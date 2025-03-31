# Relies on: https://github.com/chyyran/chd-rs-py
# See Notice.txt for licensing information

import fnmatch
import os

try:
    # optional import
    from chd import chd_open
    CHD_ENABLED = True
except ImportError:
    def chd_open(file):
        raise ImportError()
    CHD_ENABLED = False

from .file_reader import FileReader


class ChdReader(FileReader):
    """
    Handles CHD file reading.
    Only handles archives containing a single file.
    """
    def __init__(self, filepath):
        self.filepath = filepath
        self.hunk_size = 0
        self.hunk = 0
        self.pos = 0
        self.buffer = None
        self.f = None

    def open(self):
        if self.f is not None:
            return
        self.f = chd_open(self.filepath)
        self.hunk_size = (self.f.header().hunk_size() // 2448) * 2048

    def close(self):
        # keep it open for better performance
        pass

    def seek(self, n):
        hunk = n // self.hunk_size
        if hunk != self.hunk:
            self.hunk = hunk
            self.buffer = self.f.hunk(self.hunk)
        self.pos = n % self.hunk_size

    def read(self, n):
        data = bytearray(n)
        left = n
        i0 = 0
        while left > 0:
            if self.pos >= self.hunk_size:
                self.hunk += 1
                self.buffer = self.f.hunk(self.hunk)
                self.pos = 0
            subhunk = (self.pos // 2048)
            subhunk_end = (subhunk + 1) * 2048
            next_pos = min(self.hunk_size, self.pos + left, subhunk_end)
            offset = 400 * subhunk
            j0 = offset + self.pos
            j1 = offset + next_pos
            delta = j1 - j0
            i1 = i0 + delta
            data[i0:i1] = self.buffer[j0:j1]
            self.pos = next_pos
            left -= delta
            i0 = i1
        return bytes(data)

    def get_size(self):
        return len(self.f) * 16 * 1024

    def walk(self):
        raise FileNotFoundError("not available")

    def get_root(self):
        raise FileNotFoundError("not available")

    def get_subfile_size(self, file):
        raise FileNotFoundError("not available")

    def open_subfile(self, file):
        raise FileNotFoundError("not available")

    def close_subfile(self, file):
        raise FileNotFoundError("not available")

    def valid(self, pattern):
        pattern = "*.chd"
        fn = os.path.basename(self.filepath)
        return len(fnmatch.filter([fn], pattern)) > 0
