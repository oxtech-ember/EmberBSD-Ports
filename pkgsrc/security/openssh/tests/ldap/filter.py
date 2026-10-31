#!/usr/bin/env python3
"""Compile the production LDAP group/filter functions against selected libldap."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--cc', type=Path, required=True)
parser.add_argument('--ldap-prefix', type=Path, required=True)
parser.add_argument('--work', type=Path, required=True)
args = parser.parse_args()
s = (args.source / 'ldapauth.c').read_text()
tokenizer = s[s.index('static int\ntokenize('):s.index('\nvoid\nldap_close(')]
filters = s[s.index('static char *\nldap_escape_value('):s.index('\n/* Validate the URI list')]
fixture = Path(__file__).with_name('filter.c').read_text()
args.work.mkdir(parents=True, exist_ok=True)
test = args.work / 'filter.c'
test.write_text(fixture.replace('/* SOURCE FUNCTIONS */', tokenizer + filters))
subprocess.run([str(args.cc), '-Wall', '-Wextra', '-Werror',
    '-fsanitize=address,undefined', '-I' + str(args.ldap_prefix / 'include'),
    '-L' + str(args.ldap_prefix / 'lib'), str(test), '-lldap', '-llber',
    '-o', str(args.work / 'filter')], check=True)
subprocess.run([str(args.work / 'filter')], check=True)
print('LDAP filter fixture PASS')
