#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Serve the selected GN Lit bundle and a CSP browser smoke fixture."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bundle', type=Path, required=True)
a = parser.parse_args()
bundle = a.bundle.resolve(strict=True)
fixture = Path(__file__).resolve().parent
files = {'/': (fixture / 'index.html', 'text/html'),
         '/consumer.js': (fixture / 'consumer.js', 'text/javascript'),
         '/lit.rollup.js': (bundle, 'text/javascript')}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        item = files.get(self.path)
        if not item:
            self.send_error(404)
            return
        data = item[0].read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', item[1])
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; require-trusted-types-for 'script'; trusted-types lit-html")
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
with HTTPServer(('127.0.0.1', 0), Handler) as server:
    print(server.server_port, flush=True)
    server.serve_forever()
