#!/usr/bin/env python3
"""Check effective pkgsrc configure archive tools for native and cross bindings."""
import argparse
import shlex
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--pkgsrc', required=True)
p.add_argument('--make', required=True)
p.add_argument('--make-arg', action='append', default=[])
p.add_argument('--ar', required=True)
p.add_argument('--ranlib', required=True)
a = p.parse_args()
for package in ('security/openssl', 'archivers/bsdtar'):
    cmd = [a.make, *a.make_arg, '-C', a.pkgsrc + '/' + package,
           'AR=' + a.ar, 'RANLIB=' + a.ranlib]
    for override in (False, True):
        extra = ['CONFIGURE_ENV=AR=/override/ar RANLIB=/override/ranlib'] if override else []
        result = subprocess.run(cmd + extra + ['-V', '${_CONFIGURE_SCRIPT_ENV}'],
                                check=True, text=True, capture_output=True)
        words = shlex.split(result.stdout)
        for name, value in [('AR', a.ar), ('RANLIB', a.ranlib)]:
            assignments = [x for x in words if x.startswith(name + '=')]
            expected = '/override/' + name.lower() if override else value
            if not assignments or assignments[-1] != name + '=' + expected:
                raise SystemExit(f'{package}: effective {name} is wrong: {assignments}')
print('PASS: OpenSSL and bsdtar select archive tools and honor recipe overrides')
