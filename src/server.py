#!/usr/bin/env python3

import http.client
import http.server as SimpleHTTPServer
import os
import subprocess
import threading
import urllib.parse
import urllib.request

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
    # start the server in the directory of the image, on a separate thread
    path = os.path.dirname(args.dvd_path)
    os.chdir(path)
    thread = threading.Thread(target=start_server)
    thread.daemon = True
    thread.start()

    # preload the dvd file
    filename = urllib.parse.quote(os.path.basename(args.dvd_path))
    dvd_url = "http://" + IP + ":" + str(args.port) + "/" + filename
    conn = http.client.HTTPConnection(IP, args.port)
    conn.request("HEAD", filename)
    response = conn.getresponse()

    # start xemu and wait for it to exit
    xemu_path = os.path.dirname(args.xemu_path)
    subprocess.call([args.xemu_path, '-dvd_path', dvd_url], cwd=xemu_path)
else:
    # just start the server
    start_server()
