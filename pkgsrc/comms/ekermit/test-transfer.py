#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise normal binary and text transfers through two Unix PTYs."""
import argparse
import errno
import os
from pathlib import Path
import pty
import select
import subprocess
import tempfile
import time
import tty

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--program', type=Path, required=True)
p.add_argument('--prefix', type=Path, required=True)
a = p.parse_args()
program = a.program.resolve(strict=True)
env = dict(os.environ, PATH=str(a.prefix / 'bin') + ':' + str(a.prefix / 'gnu/bin'), LC_ALL='C')
for mode, contents in (('B', b'Binary\x00\xff\r\nsecond\n'), ('T', b'first line\nsecond line\n')):
    with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temp:
        root = Path(temp)
        sender, receiver = root / 'sender', root / 'receiver'
        sender.mkdir(); receiver.mkdir()
        (sender / 'sample.dat').write_bytes(contents)
        master1, slave1 = pty.openpty()
        master2, slave2 = pty.openpty()
        tty.setraw(slave1); tty.setraw(slave2)
        children = []
        try:
            children.append(subprocess.Popen([str(program), '-' + mode, '-r'], cwd=receiver,
                                            stdin=slave2, stdout=slave2, stderr=subprocess.PIPE, env=env))
            children.append(subprocess.Popen([str(program), '-' + mode, '-s', 'sample.dat'], cwd=sender,
                                            stdin=slave1, stdout=slave1, stderr=subprocess.PIPE, env=env))
            os.close(slave1); os.close(slave2)
            pairs = {master1: master2, master2: master1}
            deadline = time.monotonic() + 30
            while any(child.poll() is None for child in children):
                if time.monotonic() >= deadline:
                    raise RuntimeError(mode + ' transfer timed out')
                readable, _, _ = select.select(list(pairs), [], [], 0.1)
                for fd in readable:
                    try:
                        data = os.read(fd, 65536)
                        if data:
                            os.write(pairs[fd], data)
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
            for child in children:
                if child.returncode:
                    raise RuntimeError(mode + ' transfer failed: ' + child.stderr.read().decode(errors='replace'))
            if (receiver / 'sample.dat').read_bytes() != contents:
                raise RuntimeError(mode + ' received bytes differ')
        finally:
            for child in children:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=5)
            os.close(master1); os.close(master2)
print('E-Kermit binary and text PTY transfers: PASS')
