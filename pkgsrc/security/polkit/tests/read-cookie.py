#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile and exercise the actual polkit helper input function, without setuid."""
import argparse
import errno
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--cc', type=Path, required=True)
p.add_argument('--cflag', action='append', default=[])
p.add_argument('--ldflag', action='append', default=[])
a = p.parse_args()
source = (a.source / 'src/polkitagent/polkitagenthelperprivate.c').read_text()
start = source.index('char *\nread_cookie (')
end = source.index('\ngboolean\nsend_dbus_message', start)
function = source[start:end]
with tempfile.TemporaryDirectory() as d:
    work = Path(d)
    unit = work / 'test.c'
    unit.write_text('#include <glib.h>\n#include <stdio.h>\n#include <string.h>\n'
                    '#include <stdlib.h>\n#include <errno.h>\n' + function +
                    '\nint main(int argc,char **argv){char *s=read_cookie(argc,argv);'
                    'if(!s){printf("ERR:%d",errno);return 0;}'
                    'printf("OK:%zu:",strlen(s));fwrite(s,1,strlen(s),stdout);free(s);return 0;}\n')
    binary = work / 'test'
    subprocess.run([str(a.cc), *a.cflag, str(unit), '-o', str(binary), *a.ldflag], check=True)
    def run(data, *args):
        return subprocess.run([str(binary), *args], input=data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=True).stdout
    assert run(b'abc\n') == b'OK:3:abc'
    assert run(b'\n') == b'OK:0:'
    assert run(b'', 'unused', 'argv-cookie') == b'OK:11:argv-cookie'
    assert run(b'x' * 4096 + b'\n') == b'OK:4096:' + b'x' * 4096
    assert run(b'x' * 4097 + b'\n') == f'ERR:{errno.EOVERFLOW}'.encode()
    assert run(b'no-newline') == f'ERR:{errno.EOVERFLOW}'.encode()
    assert run(b'').startswith(b'ERR:')
    assert run(b'\0\n') == f'ERR:{errno.EINVAL}'.encode()
    assert run(b'a\0b\n') == f'ERR:{errno.EOVERFLOW}'.encode()
print('PASS: actual read_cookie argv, valid/max, overlong, EOF and leading NUL')
