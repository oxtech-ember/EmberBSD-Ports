#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check normal autoindent commands through an actual host terminal."""
import argparse
import os,pty,select,time,fcntl,termios,struct
import tempfile
from pathlib import Path
from pty_cleanup import cleanup
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--program', type=Path, required=True)
p.add_argument('--prefix', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
p.add_argument('--locale', required=True)
a=p.parse_args();exe=a.program
temporary=tempfile.TemporaryDirectory(dir=a.work_dir);root=Path(temporary.name)
cases=[('caret',b'i    one\n^\x04two\nthree\x1b:wq\n',b'    one\ntwo\n    three\n'),('zero',b'i    one\n0\x04two\nthree\x1b:wq\n',b'    one\ntwo\nthree\n'),('ctrl',b'i    one\n\x04two\nthree\x1b:wq\n',b'    one\ntwo\nthree\n')]
for name,keys,expected in cases:
 f=root/(name+'.txt');f.write_bytes(b'');pid,fd=pty.fork()
 if pid==0:
  env=dict(os.environ,TERM='xterm',LC_ALL=a.locale,PATH=str(a.prefix / 'bin')+':'+str(a.prefix / 'gnu/bin'));os.execve(str(exe),[str(exe),str(f)],env)
 fcntl.ioctl(fd,termios.TIOCSWINSZ,struct.pack('HHHH',24,80,0,0));deadline=time.monotonic()+15;output=bytearray();stage=0;ended=0;pty_open=True
 while time.monotonic()<deadline:
  ready,_,_=select.select([fd] if pty_open else [],[],[],0.05)
  if ready:
   try:data=os.read(fd,16384)
   except OSError:pty_open=False;data=b''
   if data:output.extend(data)
  elapsed=15-(deadline-time.monotonic())
  if pty_open and stage==0 and elapsed>1:os.write(fd,b':set autoindent shiftwidth=4\n');stage=1
  if pty_open and stage==1 and elapsed>2:os.write(fd,keys);stage=2
  ended,status=os.waitpid(pid,os.WNOHANG)
  if ended:break
 else:
  reaped=cleanup(pid);raise AssertionError(name+' timed out; child '+('reaped' if reaped else 'not reaped'))
 actual=f.read_bytes()
 if (os.waitstatus_to_exitcode(status) or actual != expected
     or b'runtime error:' in output or b'AddressSanitizer' in output):
  raise AssertionError(name+': '+repr(actual)+' expected '+repr(expected))
print('nvi ordinary autoindent: PASS')
