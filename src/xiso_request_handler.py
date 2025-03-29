# Derived from: https://github.com/danvk/RangeHTTPServer
# See Notice.txt for licensing information

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
import os
import re
import time

from argument_parser import get_args
from image_parsers.directory_parser import DirectoryParser
from image_parsers.patches.patch_parser import PatchParser
from image_parsers.xiso_parser import XisoParser


BYTE_RANGE_RE = re.compile(r'bytes=(\d+)-(\d+)?$')
def parse_byte_range(byte_range):
    """Returns the two numbers in 'bytes=123-456' or throws ValueError.

    The last number or both numbers may be None.
    """
    if byte_range.strip() == '':
        return None, None

    m = BYTE_RANGE_RE.match(byte_range)
    if not m:
        raise ValueError('Invalid byte range %s' % byte_range)

    first, last = [x and int(x) for x in m.groups()]
    if last and last < first:
        raise ValueError('Invalid byte range %s' % byte_range)
    return first, last


args = get_args()
patch_parser = PatchParser()
xiso_cache = {}
patches = []
if args.patches is not None:
    for patch in args.patches:
        patch_obj = patch_parser.parse_patch(patch)
        if patch_obj is not None:
            patches.append(patch_obj)
        else:
            print("Unable to load patch: " + patch)


class XisoRequestHandler(SimpleHTTPRequestHandler):
    """
    Extends SimpleHTTPRequestHandler with support for:
    - Byte range requests
    - Dynamic conversion of images to XISO format
    - Patch application on the fly
    """

    def send_head(self):
        self.patches = patches
        path = self.translate_path(self.path)
        self.xiso_parser = self.get_parser_for_file(path)
        ranged = 'Range' in self.headers

        if ranged:
            try:
                self.range = parse_byte_range(self.headers['Range'])
            except ValueError:
                self.send_error(400, 'Invalid byte range')
                return None
            first, last = self.range
        else:
            self.range = None

        if self.xiso_parser is None:
            self.send_error(404, 'File not found')
            return None

        f = open(path, 'rb')
        self.xiso_parser.f = f

        file_len = self.xiso_parser.get_size()
        self.file_len = file_len
        if ranged:
            if first >= file_len:
                self.send_error(416, 'Requested Range Not Satisfiable')
                return None
            self.send_response(206)
            if last is None or last >= file_len:
                last = file_len - 1
            response_length = last - first + 1
            self.send_header('Content-Range',
                             'bytes %s-%s/%s' % (first, last, file_len))
            content_length = response_length
        else:
            self.send_response(HTTPStatus.OK)
            content_length = file_len

        self.send_header('Content-type', 'application/octet-stream')
        self.send_header('Content-Length', str(content_length))
        self.send_header('Last-Modified', self.date_time_string(time.time()))
        self.end_headers()

        return self.xiso_parser

    def get_parser_for_file(self, path):
        if not os.path.isfile(path):
            return None
        if path not in xiso_cache:
            xiso_cache[path] = self.get_new_parser_for_file(path)
        return xiso_cache[path]

    def get_new_parser_for_file(self, path):
        if XisoParser.test_file(path):
            return XisoParser(path, self.patches, args)
        elif DirectoryParser.test_file(path):
            return DirectoryParser(path, self.patches, args)
        else:
            return None

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        return SimpleHTTPRequestHandler.end_headers(self)

    def copyfile(self, source, outputfile):
        buf_size = 1024*1024
        if self.range:
            # A chunk of the file was requested
            start, stop = self.range
            buf = source.get_data_in_range(start, stop + 1)
            outputfile.write(buf)
        else:
            # The entire file was requested
            # (for testing only, not for use with xemu)
            # FIXME: the downloaded file sometimes is missing the last MiB or so
            start = 0
            stop = buf_size
            true_stop = self.file_len + 1
            while stop < true_stop:
                buf = source.get_data_in_range(start, stop)
                outputfile.write(buf)
                start += buf_size
                stop += buf_size
                stop = min(true_stop, stop)
