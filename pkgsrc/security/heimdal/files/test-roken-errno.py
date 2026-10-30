#!/usr/bin/env python3
"""Check generated errno guards with the selected target compiler and Perl."""
import argparse
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('perl', 'cc', 'sysroot', 'source', 'config'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
names = ('EAFNOSUPPORT', 'EINPROGRESS', 'ELOOP', 'ENOTSOCK', 'ENOTSUP',
         'EOVERFLOW', 'ETIMEDOUT', 'EWOULDBLOCK')
with tempfile.TemporaryDirectory() as temp:
    out = Path(temp)
    source = Path(a.source)
    subprocess.run([a.perl, str(source / 'cf/roken-h-process.pl'), '-c', a.config,
                    '-p', str(source / 'lib/roken/roken.h.in'), '-o', str(out / 'roken.h')], check=True)
    text = (out / 'roken.h').read_text()
    start = text.index('/* Microsoft VC 2010 POSIX definitions */')
    guards = text[start:text.index('\n\n', start)]
    for name in names:
        if '#ifndef ' + name + '\n' not in guards:
            raise SystemExit('missing runtime guard: ' + name)
    cases = {
        'target': '#include <errno.h>\nenum { prior = ETIMEDOUT };\n' + guards +
                  '\n_Static_assert(ETIMEDOUT == prior && ETIMEDOUT == 60, "errno changed");\n',
        'fallback': ''.join('#undef ' + n + '\n' for n in names) + '#define ELOOP 777\n' + guards +
                    '\n_Static_assert(ELOOP == 777 && ETIMEDOUT == 138 && EAFNOSUPPORT == 102, "fallback");\n',
    }
    for name, body in cases.items():
        path = out / (name + '.c')
        path.write_text(body)
        subprocess.run([a.cc, '-target', 'x86_64-unknown-netbsd', '--sysroot=' + a.sysroot,
                        '-Werror=macro-redefined', '-fsyntax-only', str(path)], check=True)
print('generated errno guards PASS')
