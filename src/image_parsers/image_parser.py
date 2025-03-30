# For the XISO implementation the following tool has been used as a reference:
# https://github.com/antangelo/xdvdfs
# See Notice.txt for licensing information

from abc import ABC, abstractmethod
import json

from .patches.patcher import Patcher
from .avl_tree import AVLTree


SECTOR_SIZE = 2048
HEADER_OFFSET = 32 * SECTOR_SIZE
HEADER_MAGIC = b"MICROSOFT*XBOX*MEDIA"
XBE_HEADER = b'XBEH'
XBE_CERT_ADDRESS_OFFSET = 280
XBE_CERT_LENGTH = 492


class ImageParser(ABC):
    """
    Base abstract class for images handling.
    Each subclass parses an image (either XISO or non-XISO) and _dynamically_
    converts its data to XISO format. (i.e. allows to read random chunks of
    the resulting XISO file without having to convert it all beforehand)
    See OtherFormatsParser for extension for non-XISO formats.
    """

    def __init__(self, file_reader, args):
        self.args = args
        self.f = file_reader
        self.verbose = self.args.verbose
        self.patcher = None
        self.filesize = 0
        self.toc = None
        self.avl_tree = None
        self.patches = None
        self.valid = self.test_file()

    def parse(self, patches):
        self.f.open()
        self.patcher = Patcher(self)
        self.filesize = self.f.get_size()
        self.get_toc()
        if self.verbose:
            print(json.dumps(self.toc, indent=4))
        self.avl_tree = AVLTree(self.toc)
        title_id, _ = self.get_xbe_info()
        if self.requires_media_patch() or self.args.apply_media_patch:
            media_patch = self.patcher.get_media_patch(title_id)
            patches.append(media_patch)
        self.patches = self.patcher.parse_patches(patches, title_id)
        self.f.close()

    def close(self):
        self.f.close()

    def get_xbe_info(self):
        xbe = "default.xbe"
        size = self.toc["FILE:" + xbe]["size"]
        xbeh = self.get_file_data(xbe, 0, len(XBE_HEADER))
        is_xbe = xbeh == XBE_HEADER
        if is_xbe:
            cert_offset = XBE_CERT_ADDRESS_OFFSET
            cert_addr = self.get_file_uint16(xbe, cert_offset)
            if cert_addr == 0 or cert_addr + XBE_CERT_LENGTH > size:
                return None, None
            else:
                title_id_data = self.get_file_data(xbe, cert_addr + 8, 4)
                title_name_data = self.get_file_data(xbe, cert_addr + 12, 40)
                title_id = title_id_data[::-1].hex()
                title_name = title_name_data.decode('utf-16').rstrip('\x00')
                return title_id.lower(), title_name
        else:
            return None, None

    def get_data_in_range(self, start, end):
        """
        Returns the data in XISO format for the specified byte range.
        """
        nodes = self.avl_tree.get_nodes_in_range(start, end)
        if self.verbose:
            print(json.dumps({"start": start, "end": end}, indent=4))
            print(json.dumps(nodes, indent=4))
        data = bytes(0)
        for node in nodes:
            data += self.get_node_data_in_range(node)
        return data

    def get_files_in_range(self, start, end):
        """
        Returns the files and TOC entries within the specified byte range.
        The byte range for each entry is included.
        """
        return self.avl_tree.get_nodes_in_range(start, end)

    def add_file_to_toc(self, file_path, data_offset, node_size):
        self.toc["FILE:" + file_path[1:]] = {
            "offset": data_offset,
            "size": node_size,
            "extra": None
        }
        if self.args.verbose:
            print("found file: " + file_path)

    def add_entry_to_toc(self, folder, file_path, toc_offset, toc_size, data):
        self.toc["TOC:" + file_path[1:]] = {
            "offset": toc_offset,
            "size": toc_size,
            "extra": {
                "folder": folder,
                "left_offset": data[0],
                "right_offset": data[1],
                "node_sector": data[2],
                "node_size": data[3],
                "attributes": data[4],
            },
        }
        if self.args.verbose:
            print("found entry: " + file_path)

    def add_header_to_toc(self, root_offset, root_size):
        self.toc["HEADER:HEADER"] = {
            "offset": HEADER_OFFSET,
            "size": SECTOR_SIZE,
            "extra": {
                "root_offset": root_offset,
                "root_size": root_size
            }
        }
        if self.args.verbose:
            print("found header")

    def get_node_data_in_range(self, node):
        """
        Returns the data in XISO format for the specified file and byte range.
        Applies patches to the file if needed.
        """
        node_type = node["file"].split(":")[0]
        filename = node["file"].split(":")[1]
        s = node["start"]
        e = node["end"]
        if node_type == "HEADER":
            data = self.get_header_data_in_range(node)
        elif node_type == "TOC":
            data = self.get_toc_data_in_range(node)
        elif node_type == "FILE":
            data = self.get_file_data_in_range(node)
            if filename in self.patches:
                patch = self.patches[filename]
                data = self.patcher.apply_patch(patch, data, s)
        else:
            data = self.get_empty_data_in_range(s, e)
        start_padding = self.get_empty_data_in_range(0, node["start_padding"])
        end_padding = self.get_empty_data_in_range(0, node["end_padding"])
        return start_padding + data + end_padding

    def get_header_data_in_range(self, node):
        start = node["start"]
        end = node["end"]
        key = node["file"]
        toc = self.toc[key]
        offset = self.f.uint32_bytes(toc["extra"]["root_offset"])
        size = self.f.uint32_bytes(toc["extra"]["root_size"])
        timestamp = bytes([0x00 for i in range(8)])
        padding = bytes([0x00 for i in range(1992)])
        h = HEADER_MAGIC
        full_data = h + offset + size + timestamp + padding + h
        return full_data[start:end]

    def get_toc_data_in_range(self, node):
        start = node["start"]
        end = node["end"]
        key = node["file"]
        toc = self.toc[key]
        name = key.split(":")[1].split("/")[-1]
        d = toc["extra"]
        l = self.f.uint16_bytes(d["left_offset"])
        r = self.f.uint16_bytes(d["right_offset"])
        sec = self.f.uint32_bytes(d["node_sector"])
        siz = self.f.uint32_bytes(d["node_size"])
        attr = bytes([d["attributes"]])
        namelen = bytes([len(name)])
        full_data = l + r + sec + siz + attr + namelen + name.encode('ascii')
        padding_size = node["size"] - len(full_data)
        full_data += self.get_empty_data_in_range(0, padding_size)
        return full_data[start:end]

    def get_empty_data_in_range(self, start, end):
        return bytes([0xFF for i in range(end - start)])

    @abstractmethod
    def get_file_data_in_range(self, node):
        """
        Returns the data of the specified file in the input byte range.
        """

    @abstractmethod
    def get_file_data(self, filename, start, length):
        pass

    def get_file_uint32(self, filename, start):
        data = self.get_file_data(filename, start, start + 4)
        return self.f.get_uint32(data, 0)

    def get_file_uint16(self, filename, start):
        data = self.get_file_data(filename, start, start + 2)
        return self.f.get_uint16(data, 0)

    @abstractmethod
    def get_toc(self):
        """
        Retrieves the table of contents of the _output_ XISO file.
        If the input is not an XISO file it has to be calculated.
        """

    @abstractmethod
    def get_size(self):
        """
        Returns the size of the _output_ XISO file
        """

    @abstractmethod
    def test_file(self):
        """
        Checks whether the specified file is in the format
        handled by this class
        """

    def requires_media_patch(self):
        return False
