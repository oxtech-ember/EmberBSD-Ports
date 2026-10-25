#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Synthetic legacy IIOD peer; the client is the actual installed ABI0/ABI1 code."""
import os
from pathlib import Path
import socketserver
import struct
import subprocess
import sys
import threading
xml = (Path(__file__).parent / 'fixture.xml').read_bytes()
class Peer(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(3)
            while line := self.rfile.readline():
                parts = line.decode('ascii').strip().split()
                if not parts: continue
                op = parts[0]; self.server.commands.append(op)
                if op in ('BINARY', 'ZPRINT'): reply = b'-22\n'
                elif op == 'PRINT': reply = str(len(xml)).encode() + b'\n' + xml + b'\n'
                elif op in ('TIMEOUT', 'OPEN', 'CLOSE'): reply = b'0\n'
                elif op == 'READ':
                    value = self.server.value
                    reply = str(len(value)).encode() + b'\n' + value + b'\n'
                elif op == 'WRITE':
                    self.server.value = self.rfile.read(int(parts[-1])).rstrip(b'\0')
                    reply = parts[-1].encode() + b'\n'
                elif op == 'READBUF':
                    if self.server.mode == 'error': reply = b'-5\n'
                    elif self.server.mode == 'cancel':
                        # Cancellation interrupts an actual blocked network read.
                        self.rfile.read(1); return
                    else:
                        data = struct.pack('<8h', -3,101,-2,102,-1,103,0,104)
                        if self.server.mode == 'partial': data = data[:8]
                        reply = str(len(data)).encode()+b'\n00000003\n'+data
                        if self.server.mode == 'partial': reply += b'0\n'
                else: raise RuntimeError('unexpected command '+repr(parts))
                self.wfile.write(reply); self.wfile.flush()
        except (ConnectionError, TimeoutError): pass
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = False
binary = sys.argv[1]
for mode in sys.argv[2:] or ['full','partial','error','cancel']:
    with Server(('127.0.0.1', 0), Peer) as server:
        server.mode=mode; server.value=b'915000000'; server.commands=[]
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        result=subprocess.run([binary, 'ip:127.0.0.1:'+str(server.server_address[1]), mode],timeout=10)
        server.shutdown();thread.join()
        print(mode,server.commands,flush=True)
        if result.returncode: raise SystemExit(result.returncode)
        if not {'BINARY','ZPRINT','PRINT','WRITE','READ','OPEN','READBUF'}.issubset(server.commands):
            raise SystemExit('Protocol fallback or operation coverage missing')
print('PASS installed official compat/core against legacy ASCII IIOD')
