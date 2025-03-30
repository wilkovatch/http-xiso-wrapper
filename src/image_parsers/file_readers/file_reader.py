import fnmatch
import os
import struct


class FileReader():
    """
    Handles file reading, with convenience methods for integers.
    Allows to switch to other files.
    """
    def __init__(self, filepath):
        self.filepath = filepath
        self.f = None

    def open(self):
        self.f = open(self.filepath, 'rb')

    def close(self):
        self.f.close()

    def seek(self, n):
        self.f.seek(n)

    def read(self, n):
        return self.f.read(n)

    def get_size(self):
        return os.path.getsize(self.filepath)

    def walk(self):
        return os.walk(self.get_root())

    def get_root(self):
        return os.path.dirname(self.filepath) + '/'

    def get_subfile_size(self, file):
        return os.path.getsize(file)

    def open_subfile(self, file):
        return open(file, 'rb')

    def close_subfile(self, file):
        file.close()

    def valid(self, pattern):
        fn = os.path.basename(self.filepath)
        return len(fnmatch.filter([fn], pattern)) > 0

    def uint32_bytes(self, n):
        return n.to_bytes(4, byteorder='little')

    def uint16_bytes(self, n):
        return n.to_bytes(2, byteorder='little')

    def read_uint32(self):
        return struct.unpack('<I', self.read(4))[0]

    def read_uint16(self):
        return struct.unpack('<H', self.read(2))[0]

    def get_uint16(self, b, i):
        return int.from_bytes(b[i:i+2], byteorder='little')

    def get_uint32(self, b, i):
        return int.from_bytes(b[i:i+4], byteorder='little')
