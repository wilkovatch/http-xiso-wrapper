import fnmatch
import os
from zipfile import ZipFile, BadZipFile

from .file_reader import FileReader


class ZipReader(FileReader):
    """
    Handles zip file reading. Experimental.
    Zip files are expected to contain the raw files.
    (e.g. with the default.xbe and all the other files)
    Could work with zipped XISOs if the seek wasn't slow.
    Warning: seek is slow with large files.
    """
    def __init__(self, filepath):
        self.is_xbe = False
        self.pattern = None
        self.f2 = None
        self.validated = False
        self.cur_subfile = None
        self.cur_subfile_handle = None
        self.closed = True
        super().__init__(filepath)

    def open(self):
        if not self.closed:
            return
        self.f = ZipFile(self.filepath, 'r')
        if self.validated and self.pattern is not None:
            file = fnmatch.filter(self.f.namelist(), self.pattern)[0]
            self.f2 = self.f.open(file)
        self.closed = False

    def check_f2(self):
        if self.f2 is None:
            msg = "no files found matching pattern: " + self.pattern
            raise FileNotFoundError(msg)

    def close(self):
        # keep it open for better performance
        pass

    def close_forced(self):
        if self.f2 is not None:
            self.f2.close()
        if self.cur_subfile is not None:
            self.cur_subfile = None
            self.cur_subfile_handle.close()
        self.f.close()
        self.closed = True

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
        if self.cur_subfile != file:
            if self.cur_subfile_handle is not None:
                self.cur_subfile_handle.close()
            self.cur_subfile = file
            self.cur_subfile_handle = self.f.open(self.get_root() + file)
            return self.cur_subfile_handle
        else:
            return self.cur_subfile_handle

    def close_subfile(self, file):
        # keep it open for better performance
        pass

    def valid(self, pattern):
        if self.filepath.split(".")[-1] != "zip":
            return False
        self.is_xbe = pattern == "default.xbe"
        self.pattern = pattern
        try:
            self.open()
            res = len(fnmatch.filter(self.f.namelist(), pattern)) > 0
            self.close_forced()
            self.validated = True
            return res
        except BadZipFile:
            return False
