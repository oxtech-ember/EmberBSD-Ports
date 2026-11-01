#!/usr/bin/env python3
"""Exercise the actual native Kerberos handler with an ordinary mock."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ('cc', 'source', 'work-dir'):
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--sanitize', action='store_true')
args = parser.parse_args()
args.work_dir.mkdir(parents=True, exist_ok=True)
text = (args.source / 'auth2-krb5.c').read_text()
start = text.index('static int\nuserauth_kerberos(')
end = text.index('\nAuthmethod method_kerberos', start)
template = Path(__file__).with_suffix('.c.in').read_text()
source = args.work_dir / 'kerberos-auth-handler.c'
source.write_text(template.replace('@@USERAUTH_KRB5@@', text[start:end]))
exe = args.work_dir / 'kerberos-auth-handler'
command = [str(args.cc), '-Wall', '-Wextra', '-Werror']
if args.sanitize:
    command += ['-fsanitize=address,undefined']
subprocess.run([*command, str(source), '-o', str(exe)], check=True)
subprocess.run([str(exe)], check=True)
