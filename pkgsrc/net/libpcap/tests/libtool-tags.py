#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise the configured pkgsrc Makefile's C compile and link rules."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--make', type=Path, required=True)
parser.add_argument('--shell', type=Path, required=True)
parser.add_argument('--worksrc', type=Path, required=True)
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='libpcap-libtool-tags-') as temporary:
    work = Path(temporary)
    (work / 'Makefile').write_bytes((args.worksrc / 'Makefile').read_bytes())
    (work / 'probe.c').write_text('int probe(void) { return 0; }\n')
    mock = work / 'libtool'
    mock.write_text('#!' + str(args.shell) + '''\nset -eu
[ "$1" = --tag=CC ] || exit 1
case "$2" in
  --mode=compile) printf '%s\\n' compile >> "$LIBTOOL_TEST_LOG"; : > probe.lo ;;
  --mode=link) printf '%s\\n' link >> "$LIBTOOL_TEST_LOG"; : > libpcap.la ;;
  *) exit 1 ;;
esac
''')
    mock.chmod(0o755)
    bindir = args.make.resolve().parent
    env = dict(os.environ, LIBTOOL_TEST_LOG=str(work / 'calls'),
               PATH=str(bindir) + os.pathsep + str(bindir.parent / 'gnu/bin'))
    command = [str(args.make), '-f', str(work / 'Makefile'),
               'LIBTOOL=' + str(mock), 'srcdir=' + str(work), 'OBJ=probe.lo',
               'SHELL=' + str(args.shell), 'libpcap.la']
    result = subprocess.run(command, cwd=work, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    assert (work / 'calls').read_text().splitlines() == ['compile', 'link']
print('PASS: configured libpcap C compile and link select the libtool tag')
