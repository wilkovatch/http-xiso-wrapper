#!/usr/bin/env python3

import http.server as SimpleHTTPServer
import os
import subprocess
import threading
import urllib.parse

from argument_parser import get_args
from xiso_request_handler import XisoRequestHandler


args = get_args()

# Note about the IP: use 127.0.0.1 instead of localhost on Windows, otherwise
# there would be a 2-3 seconds delay for each request
IP = "127.0.0.1"

def start_server():
    SimpleHTTPServer.test(HandlerClass=XisoRequestHandler, port=args.port,
                          bind=IP)

if args.dvd_path:
    # start the server on a separate thread
    thread = threading.Thread(target=start_server)
    thread.daemon = True
    thread.start()

    # start xemu and wait for it to exit
    path = os.path.dirname(args.dvd_path)
    filename = urllib.parse.quote_plus(os.path.basename(args.dvd_path))
    os.chdir(path)
    dvd_url = "http://" + IP + ":" + str(args.port) + "/" + filename
    subprocess.call([args.xemu_path, '-dvd_path', dvd_url])
else:
    # just start the server
    start_server()
