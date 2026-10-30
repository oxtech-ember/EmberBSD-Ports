#!/usr/bin/env python3
"""Check selected archive tools reach BSD make packages with overrides intact."""
import argparse
import shlex
import subprocess
import tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--pkgsrc', required=True)
p.add_argument('--make', required=True)
p.add_argument('--make-arg', action='append', default=[])
for name in ('ar', 'ranlib', 'nm'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
for package in ('net/libfetch', 'net/fetch'):
    cmd = [a.make, *a.make_arg, '-C', a.pkgsrc + '/' + package,
           'AR=' + a.ar, 'RANLIB=' + a.ranlib, 'NM=' + a.nm]
    with tempfile.TemporaryDirectory() as temporary:
        fixture = Path(temporary) / 'Makefile'
        fixture.write_text('MAKE_ENV+= AR=/override/ar RANLIB=/override/ranlib NM=/override/nm\n'
                           + '.include "' + a.pkgsrc + '/' + package + '/Makefile"\n')
        for override in (False, True):
            extra = ['-f', str(fixture)] if override else []
            result = subprocess.run(cmd + extra + ['-V', '${MAKE_ENV}'],
                                    check=True, text=True, capture_output=True)
            words = shlex.split(result.stdout)
            for name, value in [('AR', a.ar), ('RANLIB', a.ranlib), ('NM', a.nm)]:
                assignments = [x for x in words if x.startswith(name + '=')]
                expected = '/override/' + name.lower() if override else value
                if not assignments or assignments[-1] != name + '=' + expected:
                    raise SystemExit(f'{package}: effective {name} is wrong: {assignments}')
print('PASS: BSD make packages select tools and honor package overrides')
