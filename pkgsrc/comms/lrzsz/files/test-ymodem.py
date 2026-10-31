#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise an ordinary binary YMODEM transfer through two owned PTYs."""
import argparse
import os
from pathlib import Path
import pty
import select
import subprocess
import tempfile
import time
import tty

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bin-dir', type=Path, required=True)
args = parser.parse_args()
bindir = args.bin_dir.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='lrzsz-ymodem-') as directory:
    root = Path(directory)
    source, destination = root / 'send', root / 'receive'
    source.mkdir()
    destination.mkdir()
    payload = bytes(range(256)) * 1288
    (source / 'payload.bin').write_bytes(payload)
    send_master, send_slave = pty.openpty()
    recv_master, recv_slave = pty.openpty()
    tty.setraw(send_slave)
    tty.setraw(recv_slave)
    processes = []
    try:
        for program, cwd, slave, params in (
            ('lrb', destination, recv_slave, ('--binary',)),
            ('lsz', source, send_slave, ('--ymodem', 'payload.bin')),
        ):
            processes.append(subprocess.Popen(
                [str(bindir / program), *params], cwd=cwd,
                stdin=slave, stdout=slave, stderr=subprocess.DEVNULL))
        os.close(send_slave)
        os.close(recv_slave)
        deadline = time.monotonic() + 45
        while any(p.poll() is None for p in processes):
            if time.monotonic() >= deadline:
                raise RuntimeError('YMODEM transfer timed out')
            for fd in select.select((send_master, recv_master), (), (), 0.1)[0]:
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    continue
                if data:
                    os.write(recv_master if fd == send_master else send_master, data)
        if any(p.returncode != 0 for p in processes):
            raise RuntimeError(f'YMODEM process statuses: {[p.returncode for p in processes]}')
        if (destination / 'payload.bin').read_bytes() != payload:
            raise RuntimeError('YMODEM payload differs')
        print(f'YMODEM binary round-trip passed: {len(payload)} bytes')
    finally:
        for p in processes:
            if p.poll() is None:
                p.kill()
            p.wait()
        os.close(send_master)
        os.close(recv_master)
