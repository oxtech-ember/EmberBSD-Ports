#!/usr/bin/env python3
"""Check package catalog paths are rooted exactly once."""
import argparse
import shlex
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--pkgsrc', required=True)
p.add_argument('--make', required=True)
p.add_argument('--make-arg', action='append', default=[])
p.add_argument('--prefix', required=True)
a = p.parse_args()
for kind in ('XML', 'SGML'):
    for value, expected in ((a.prefix + '/share/catalog', a.prefix + '/share/catalog'),
                            ('/share/catalog', '/share/catalog'),
                            ('share/catalog', a.prefix + '/share/catalog')):
        result = subprocess.run([a.make, *a.make_arg, '-C', a.pkgsrc + '/textproc/docbook-xsl',
                                 kind + '_CATALOGS=' + value, '-V', '${' + kind + '_ENTRIES}'],
                                check=True, text=True, capture_output=True)
        words = shlex.split(result.stdout)
        if expected not in words or a.prefix + a.prefix in result.stdout:
            raise SystemExit(f'{kind} catalog {value}: {result.stdout}')
print('PASS: XML and SGML catalog absolute and relative paths')
