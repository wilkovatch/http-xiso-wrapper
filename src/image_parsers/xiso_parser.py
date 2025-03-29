# For the XISO implementation the following tool has been used as a reference:
# https://github.com/antangelo/xdvdfs
# See Notice.txt for licensing information

from .image_parser import ImageParser, HEADER_OFFSET, HEADER_MAGIC, SECTOR_SIZE


FULL_DUMP_DATA_OFFSET = 387 * 1024 * 1024


class XisoParser(ImageParser):
    """
    Handles Standard XISO and Redump-style XISO files
    """
    def get_file_data_in_range(self, node, start, end):
        f = self.f
        f.seek(self.image_start + node["offset"] + node["start"])
        return f.read(node["end"] - node["start"])

    def get_file_data(self, filename, start, length):
        f = self.f
        file = self.toc["FILE:" + filename]
        f.seek(self.image_start + file["offset"] + start)
        return f.read(length)

    def get_size(self):
        return self.filesize - self.image_start

    def requires_media_patch(self):
        return self.image_start > 0

    @staticmethod
    def test_file(path):
        with open(path, 'rb') as f:
            root_sector, _, _ = XisoParser.read_header(f)
            return root_sector is not None

    def get_toc(self):
        f = self.f
        self.toc = None

        root_sector, root_size, image_start = XisoParser.read_header(f)
        self.image_start = image_start
        if root_sector is not None:
            self.toc = {}
            self.add_header_to_toc(root_sector, root_size)
            root_offset = root_sector * SECTOR_SIZE
            self.traverse_file_tree("", root_offset, root_size, 0)

    @staticmethod
    def read_header(f, full = False):
        image_start = FULL_DUMP_DATA_OFFSET if full else 0

        f.seek(image_start + HEADER_OFFSET)
        header_magic = f.read(len(HEADER_MAGIC))
        if header_magic != HEADER_MAGIC:
            if full:
                return None, None, None
            else:
                return XisoParser.read_header(f, True)

        root_sector = XisoParser.read_uint32(f)
        root_size = XisoParser.read_uint32(f)

        return root_sector, root_size, image_start

    def traverse_file_tree(self, parent_path, parent_offset, parent_size,
                           node_offset):
        f = self.f

        if node_offset >= parent_size:
            return

        entry_offset = parent_offset + node_offset

        f.seek(self.image_start + entry_offset)

        (data, left_offset, right_offset, node_size, file_path, data_offset,
         is_directory, entry_size) = self.read_node(parent_path)

        if file_path is None:
            return

        if is_directory:
            self.add_entry_to_toc(True, file_path, entry_offset, entry_size,
                                  data)
            if node_size != 0:
                self.traverse_file_tree(file_path, data_offset, node_size, 0)
        else:
            self.add_entry_to_toc(False, file_path, entry_offset, entry_size,
                                  data)
            self.add_file_to_toc(file_path, data_offset, node_size)

        if left_offset != 0 and left_offset != 0xFFFF:
            self.traverse_file_tree(parent_path, parent_offset, parent_size,
                                    left_offset * 4)

        if right_offset != 0 and right_offset != 0xFFFF:
            self.traverse_file_tree(parent_path, parent_offset, parent_size,
                                    right_offset * 4)

    def read_node(self, parent_path):
        f = self.f

        b = f.read(14)
        left_offset = XisoParser.get_uint16(b, 0)
        right_offset = XisoParser.get_uint16(b, 2)
        node_sector = XisoParser.get_uint32(b, 4)
        node_size = XisoParser.get_uint32(b, 8)
        attributes = b[12]
        filename_length = b[13]
        data = (left_offset, right_offset, node_sector, node_size, attributes)
        file_path = None
        data_offset = None
        is_directory = None
        entry_size = 14

        ff_filled = b == [0xFF for i in range(14)]
        zero_filled = b == [0x00 for i in range(14)]
        empty = ff_filled or zero_filled

        if not empty:
            filename = f.read(filename_length).decode('ascii')
            file_path = parent_path + "/" + filename
            data_offset = node_sector * SECTOR_SIZE
            is_directory = attributes & 0x10 > 0
            padding = (4 - ((14 + filename_length) % 4)) % 4
            entry_size += filename_length + padding

        return (data, left_offset, right_offset, node_size, file_path,
                data_offset, is_directory, entry_size)
