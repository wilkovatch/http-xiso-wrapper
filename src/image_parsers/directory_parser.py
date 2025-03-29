# For the XISO implementation the following tool has been used as a reference:
# https://github.com/antangelo/xdvdfs
# See Notice.txt for licensing information

import os

from .image_parser import XBE_HEADER
from .other_formats_parser import OtherFormatsParser


class DirectoryParser(OtherFormatsParser):
    """
    Handles unpacked files inside a directory.
    The input file is expected to be the default.xbe file
    """

    def get_file_data_in_range(self, node, start, end):
        filename = node["file"].split(":")[1]
        filepath = self.get_root() + "/" + filename
        with open(filepath, 'rb') as f:
            f.seek(node["start"])
            return f.read(node["end"] - node["start"])

    def get_file_data(self, filename, start, length):
        filepath = self.get_root() + "/" + filename
        with open(filepath, 'rb') as f:
            f.seek(start)
            return f.read(length)

    def get_root(self):
        """
        Returns the directory containing the input file
        """
        return os.path.dirname(self.filepath)

    @staticmethod
    def test_file(path):
        with open(path, 'rb') as f:
            return f.read(4) == XBE_HEADER

    def get_files(self, start_path, main_res):
        for root, dirs, files in os.walk(start_path):
            nodes = []
            node_size = 0
            for file in files:
                filepath = os.path.join(root, file)
                filepath2 = filepath[(len(start_path) + 1):].replace("\\","/")
                filename = filepath2.split("/")[-1]
                size = os.path.getsize(filepath)

                padding = (4 - ((14 + len(filename)) % 4)) % 4
                entry_size = 14 + len(filename) + padding
                node_size = self.adjusted_entry_offset(node_size, entry_size)
                node_size += entry_size

                nodes.append({
                    "filename": filepath2,
                    "size": size,
                    "entry_size": entry_size,
                    "folder": False
                })
            for directory in dirs:
                dirpath = os.path.join(root, directory)
                dirpath2 = dirpath[(len(start_path) + 1):].replace("\\","/")
                dirname = dirpath2.split("/")[-1]

                padding = (4 - ((14 + len(dirname)) % 4)) % 4
                entry_size = 14 + len(dirname) + padding
                node_size = self.adjusted_entry_offset(node_size, entry_size)
                node_size += entry_size

                nodes.append({
                    "filename": dirpath2,
                    "size": None,
                    "entry_size": entry_size,
                    "folder": True
                })
            rootname = root[(len(start_path) + 1):].replace("\\","/")
            res = {
                "nodes": nodes,
                "size": node_size
            }
            main_res[rootname] = res
