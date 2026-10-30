#!/usr/bin/env python3
"""Check that OpenSSL's real pkgsrc configure environment selects archive tools."""
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
cmd = [a.make, *a.make_arg, '-C', a.pkgsrc + '/security/openssl',
       'AR=' + a.ar, 'RANLIB=' + a.ranlib, '-V', '${CONFIGURE_ENV}']
result = subprocess.run(cmd, check=True, text=True, capture_output=True)
words = shlex.split(result.stdout)
for name, value in [('AR', a.ar), ('RANLIB', a.ranlib)]:
    assignments = [x for x in words if x.startswith(name + '=')]
    if assignments != [name + '=' + value]:
        raise SystemExit(f'{name} is not bound to selected archive tool: {assignments}')
print('PASS: OpenSSL configure receives the selected AR and RANLIB')
