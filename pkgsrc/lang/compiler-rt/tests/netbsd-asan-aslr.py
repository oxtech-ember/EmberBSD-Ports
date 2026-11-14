#!/usr/bin/env python3
"""Exercise the NetBSD ASan early-ASLR refusal and enabled-runtime controls."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('clean', 'uaf', 'ubsan', 'paxctl', 'work'):
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
for path in (args.clean, args.uaf, args.ubsan, args.paxctl):
    if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        parser.error('inputs must be absolute executables')
if not args.work.is_absolute() or args.work.exists():
    parser.error('work must be a new absolute directory')
args.work.mkdir(mode=0o700)
env = dict(os.environ, ASAN_OPTIONS='abort_on_error=1:detect_leaks=0:symbolize=0',
           UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=0')
for key in ('LD_PRELOAD', 'LD_LIBRARY_PATH'):
    env.pop(key, None)

def run(binary, *, abort=True):
    selected_env = dict(env, ASAN_OPTIONS=('abort_on_error=1' if abort else 'abort_on_error=0') + ':detect_leaks=0:symbolize=0')
    return subprocess.run([str(binary)], env=selected_env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=30)

clean, uaf, ubsan = (args.work / name for name in ('clean', 'uaf', 'ubsan'))
for source, dest in ((args.clean, clean), (args.uaf, uaf), (args.ubsan, ubsan)):
    shutil.copyfile(source, dest)
    dest.chmod(0o700)
subprocess.run([str(args.paxctl), '-a', str(clean)], check=True, timeout=30)
subprocess.run([str(args.paxctl), '+A', str(clean)], check=True, timeout=30)
refused = run(clean, abort=False)
if refused.returncode <= 0 or 'This sanitizer is not compatible with enabled ASLR.' not in refused.stdout or 'paxctl +a <executable>' not in refused.stdout:
    raise RuntimeError('default ASLR did not fail with the expected diagnostic: ' + repr((refused.returncode, refused.stdout)))
subprocess.run([str(args.paxctl), '-A', str(clean), str(uaf)], check=True, timeout=30)
subprocess.run([str(args.paxctl), '+a', str(clean), str(uaf)], check=True, timeout=30)
ok = run(clean)
if ok.returncode != 0 or ok.stdout:
    raise RuntimeError('ASan clean control failed: ' + repr((ok.returncode, ok.stdout)))
negative = run(uaf)
if negative.returncode == 0 or 'AddressSanitizer: heap-use-after-free' not in negative.stdout:
    raise RuntimeError('ASan UAF control failed: ' + repr((negative.returncode, negative.stdout)))
overflow = run(ubsan)
if overflow.returncode == 0 or 'runtime error: signed integer overflow' not in overflow.stdout:
    raise RuntimeError('UBSan overflow control failed: ' + repr((overflow.returncode, overflow.stdout)))
print('PASS: default ASLR diagnostic, per-file ASan clean/UAF, UBSan overflow')
