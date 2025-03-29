# For the XISO implementation the following tool has been used as a reference:
# https://github.com/antangelo/xdvdfs
# See Notice.txt for licensing information

from abc import abstractmethod

from .avl_tree import AVLTree
from .image_parser import ImageParser, SECTOR_SIZE


class OtherFormatsParser(ImageParser):
    """
    Base abstract class for non-XISO images handling.
    The base class handles generation of the XISO table of contents.
    Subclasses have to implement the following methods:
    - get_files
    - get_file_data_in_range
    - get_file_data
    - test_file
    """

    def __init__(self, filepath, patches, args):
        self.root_size = 0
        self.dirsize = 0
        super().__init__(filepath, patches, args)

    def ceil_to_sector(self, size):
        s = SECTOR_SIZE
        return (size + s - 1) // s * s

    def get_size(self):
        return self.dirsize

    def get_toc(self):
        files = self.get_toc_data()
        self.toc = {}
        self.add_header_to_toc(33, self.root_size)
        for dirfiles in files:
            # TOC entries
            for file in dirfiles:
                filename = "/" + file["filename"]
                is_directory = file["folder"]
                data = [
                    file['left_offset'],                # left_offset
                    file['right_offset'],               # right_offset
                    file["data_offset"] // SECTOR_SIZE, # node_sector
                    file["size"],                       # node_size
                    16 if is_directory else 32          # attributes
                ]
                self.add_entry_to_toc(is_directory, filename,
                                      file["entry_offset"], file["entry_size"],
                                      data)

            # File data
            for file in dirfiles:
                filename = "/" + file["filename"]
                is_directory = file["folder"]
                if not is_directory:
                    self.add_file_to_toc(filename, file["data_offset"], file["size"])

    def get_root(self):
        """
        Returns the file path.
        Separate method to allow subclassing for directories.
        """
        return self.filepath

    @abstractmethod
    def get_files(self, start_path, main_res):
        """
        Returns the file tree as a dictionary, with:
        - key: the directory path (relative to the root)
        - value: the list of files and directories inside the key directory
        Each entry in the value list should be a dictionary with:
        - "filename": the file or directory path (relative to the root)
        - "size":
          - for files: the size in bytes
          - for directories: the combined size of the XISO entries
            directly inside the directory (plus padding if across sectors)
        - "entry_size": the XISO entry size
        - "folder": True if it's a directory, False otherwise
        """

    def adjusted_entry_offset(self, cur_offset, entry_size):
        """
        Adds padding to the specified offset so that the entry starts at the
        beginning of the next sector if it would otherwise be across sectors
        """
        sec_sz = SECTOR_SIZE
        next_offset = cur_offset + entry_size
        if (next_offset % sec_sz) < (cur_offset % sec_sz):
            cur_offset += (next_offset % sec_sz)
        return cur_offset

    def get_toc_data(self):
        """
        Returns the data required to construct the XISO table of contents,
        which is a list of lists (one for each directory, root included),
        with each directory list entry containing:
        - "filename", "size" and "folder" from the get_files method
        - "left_offset": offset of the left node
        - "right_offset": offset of the right node
        - "data_offset": the offset of the file data or of the first entry in
           the directory
        """
        sec_sz = SECTOR_SIZE

        # get the files
        files = {}
        self.get_files(self.get_root(), files)

        # calculate folder sizes
        for key, value in files.items():
            for node in value["nodes"]:
                if node["folder"]:
                    folder_size = files[node["filename"]]["size"]
                    node["size"] = self.ceil_to_sector(folder_size)

        # Calculate AVL trees for each folder
        for key, value in files.items():
            entries = {
                f["filename"]: {
                    "offset": (f["filename"].split("/")[-1]).lower(),
                    "size": f["size"],
                    "data": f
                }
                for f in value['nodes']
            }
            tree = AVLTree(entries).to_list()
            new_nodes = []
            for f in tree:
                f2 = f.data
                ln = None if f.left is None else f.left.data["filename"]
                rn = None if f.right is None else f.right.data["filename"]
                f2["left_name"] = ln
                f2["right_name"] = rn
                new_nodes.append(f2)
            files[key]['nodes'] = new_nodes

        # Offsets
        cur_offset = 33 * sec_sz
        for key, value in files.items():
            start_offset = cur_offset
            # TOC
            for node in value["nodes"]:
                # multi sector TOC
                entry_size = node["entry_size"]
                cur_offset = self.adjusted_entry_offset(cur_offset, entry_size)

                node["entry_offset"] = cur_offset
                cur_offset += entry_size

            cur_offset = self.ceil_to_sector(cur_offset)

            # Files
            for node in value["nodes"]:
                if not node["folder"]:
                    node["data_offset"] = cur_offset
                    cur_offset = self.ceil_to_sector(cur_offset + node["size"])
                else:
                    node["data_offset"] = None
            files[key]["offset"] = start_offset

            cur_offset += sec_sz

        # Left-right offsets
        for key, value in files.items():
            start_offset = value['nodes'][0]['entry_offset']
            offset_dict = {}
            for node in value["nodes"]:
                node_offset = node["entry_offset"] - start_offset
                offset_dict[node["filename"]] = node_offset
            for node in value["nodes"]:
                ln = node['left_name']
                rn = node['right_name']
                l_offset = 0 if ln is None else offset_dict[ln] // 4
                r_offset = 0 if rn is None else offset_dict[rn] // 4
                node['left_offset'] = l_offset
                node['right_offset'] = r_offset

        # Directory offsets
        for key, value in files.items():
            # Files
            for node in value["nodes"]:
                if node["folder"]:
                    node["data_offset"] = files[node["filename"]]["offset"]

        # cleanup
        res = [value["nodes"] for _, value in files.items()]
        self.root_size = files[""]["size"]
        self.dirsize = cur_offset

        return res
