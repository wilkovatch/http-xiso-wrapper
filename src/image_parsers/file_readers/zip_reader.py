import fnmatch
import os
from zipfile import ZipFile, BadZipFile

from .file_reader import FileReader


class ZipReader(FileReader):
    """
    Handles zip file reading. Experimental.
    Zip files are expected to contain the raw files.
    (e.g. with the default.xbe and all the other files)
    Could work with zipped XISOs if the week wasn't slow.
    Warning: seek is slow with large files.
    """
    def __init__(self, filepath):
        self.is_xbe = False
        self.pattern = None
        self.f2 = None
        self.validated = False
        super().__init__(filepath)

    def open(self):
        self.f = ZipFile(self.filepath, 'r')
        if self.validated and self.pattern is not None:
            file = fnmatch.filter(self.f.namelist(), self.pattern)[0]
            self.f2 = self.f.open(file)

    def check_f2(self):
        if self.f2 is None:
            msg = "no files found matching pattern: " + self.pattern
            raise FileNotFoundError(msg)

    def close(self):
        if self.f2 is not None:
            self.f2.close()
        self.f.close()

    def seek(self, n):
        self.check_f2()
        self.f2.seek(n)

    def read(self, n):
        self.check_f2()
        return self.f2.read(n)

    def get_size(self):
        if self.f2 is not None:
            return self.f.getinfo(self.f2.name).file_size
        return super().get_size()

    def walk(self):
        res = {}

        for info in self.f.infolist():
            if info.is_dir():
                key = "dirs"
                entry = os.path.dirname(info.filename).rstrip('/')
            else:
                key = "files"
                entry = info.filename
            path = os.path.dirname(entry)
            basename = os.path.basename(entry)
            if path not in res:
                res[path] = { "dirs": [], "files": [] }
            res[path][key].append(basename)

        for key, item in res.items():
            yield (key, item["dirs"], item["files"])


    def get_root(self):
        if not self.is_xbe:
            msg = "the default.xbe file is not in this archive"
            raise FileNotFoundError(msg)
        return ''

    def get_subfile_size(self, file):
        return self.f.getinfo(file).file_size

    def open_subfile(self, file):
        return self.f.open(self.get_root() + file)

    def valid(self, pattern):
        if self.filepath.split(".")[-1] != "zip":
            return False
        self.is_xbe = pattern == "default.xbe"
        self.pattern = pattern
        try:
            self.open()
            res = len(fnmatch.filter(self.f.namelist(), pattern)) > 0
            self.close()
            self.validated = True
            return res
        except BadZipFile:
            return False
