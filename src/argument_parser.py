import argparse
import sys


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dvd_path", help="the file to open with xemu")
    parser.add_argument("--xemu_path", help="path of the xemu executable",
                        required='--dvd_path' in sys.argv)
    parser.add_argument("--patches", help="patches to load", nargs='+')
    parser.add_argument("--apply_media_patch", help="apply media patch on default.xbe",
                        action="store_true")
    parser.add_argument("--port", help="server port (default 8000)", type=int, default=8000)
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    return parser.parse_args()
