# For the XISO implementation the following tool has been used as a reference:
# https://github.com/antangelo/xdvdfs
# See Notice.txt for licensing information

from .image_parser import XBE_HEADER
from .other_formats_parser import OtherFormatsParser


class DirectoryParser(OtherFormatsParser):
    """
    Handles loose files inside a raw or compressed directory.
    The input file is expected to be (or contain) the default.xbe file
    """

    def get_file_data_in_range(self, node):
        f = self.f
        filename = node["file"].split(":")[1]
        f2 = f.open_subfile(filename)
        f2.seek(node["start"])
        data = f2.read(node["end"] - node["start"])
        f.close_subfile(f2)
        return data

    def get_file_data(self, filename, start, length):
        f = self.f
        f2 = f.open_subfile(filename)
        f2.seek(start)
        data = f2.read(length)
        f.close_subfile(f2)
        return data

    def test_file(self):
        if not self.f.valid('default.xbe'):
            return False
        self.f.open()
        res = self.f.read(4) == XBE_HEADER
        self.f.close()
        return res

    def get_files(self):
        start_path = self.f.get_root().strip('/')
        main_res = {}
        for root, dirs, files in self.f.walk():
            nodes = []
            node_size = 0
            for file in files:
                filepath = (root.replace("\\","/") + "/" + file).strip('/')
                filepath2 = filepath[(len(start_path)):].strip('/')
                filename = filepath2.split("/")[-1]
                size = self.f.get_subfile_size(filepath)

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
                dirpath = (root.replace("\\","/") + "/" + directory).strip('/')
                dirpath2 = dirpath[(len(start_path)):].strip('/')
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
            rootname = root[(len(start_path)):].replace("\\","/").strip('/')
            res = {
                "nodes": nodes,
                "size": node_size
            }
            main_res[rootname] = res
        return main_res
