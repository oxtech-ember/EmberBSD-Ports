#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run focused libavutil and local RTSP redirect regressions explicitly."""
import argparse
from pathlib import Path
import socket
import subprocess
import tempfile
import threading

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--cc',type=Path,required=True)
p.add_argument('--ffprobe',type=Path,required=True)
p.add_argument('--cflag',action='append',default=[])
p.add_argument('--ldflag',action='append',default=[])
a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='ffmpeg-upstream-regression-') as tmp:
    executable=Path(tmp)/'hdr-avstring-regression'
    source=Path(__file__).with_name('hdr-avstring-regression.c')
    subprocess.run([str(a.cc.resolve(strict=True)),*a.cflag,'-UNDEBUG',str(source),*a.ldflag,'-o',str(executable)],check=True)
    for mode in ('hdr','replace'):
        subprocess.run([str(executable),mode],check=True,timeout=5)
    server=socket.socket(); server.bind(('127.0.0.1',0)); server.listen(); server.settimeout(1)
    url=f'rtsp://127.0.0.1:{server.getsockname()[1]}/sample'; count=[]; errors=[]; stop=threading.Event()
    def serve():
        try:
            while not stop.is_set() and len(count)<12:
                try: client,_=server.accept()
                except socket.timeout: continue
                with client:
                    client.settimeout(3); request=b''
                    while b'\r\n\r\n' not in request:
                        part=client.recv(4096)
                        if not part: break
                        request+=part
                    if not request: continue
                    cseq=next((line.split(b':',1)[1].strip() for line in request.split(b'\r\n')
                               if line.lower().startswith(b'cseq:')),b'1')
                    count.append(1)
                    client.sendall(b'RTSP/1.0 302 Found\r\nCSeq: '+cseq+b'\r\nLocation: '+url.encode()+b'\r\nContent-Length: 0\r\n\r\n')
        except (OSError,ValueError) as error:
            if not stop.is_set(): errors.append(error)
    thread=threading.Thread(target=serve,daemon=True); thread.start()
    try:
        result=subprocess.run([str(a.ffprobe.resolve(strict=True)),'-v','error','-rtsp_transport','tcp',url],
                              capture_output=True,text=True,timeout=15)
    finally:
        stop.set(); server.close(); thread.join(timeout=4)
    assert not errors, errors
    assert not thread.is_alive(), 'local RTSP fixture did not terminate'
    assert result.returncode != 0 and 'Too many RTSP redirects' in result.stderr, result.stderr
    assert len(count)==9, f'expected 9 RTSP requests, got {len(count)}'
print('PASS: HDR saturation, empty replacement and bounded local RTSP redirects')
