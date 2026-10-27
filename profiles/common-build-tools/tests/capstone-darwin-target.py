#!/usr/bin/env python3
"""Check Capstone's compiler-target-driven library and architecture flags."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True)
parser.add_argument('--clang', required=True)
parser.add_argument('--gmake', required=True)
parser.add_argument('--host-prefix', required=True, type=Path)
parser.add_argument('--utility-path', required=True, type=Path)
args = parser.parse_args()
prefix = args.host_prefix.resolve(strict=True)
for tool in (args.clang, args.gmake):
    assert Path(tool).resolve(strict=True).is_relative_to(prefix), tool
for role in ('grep', 'awk', 'wc', 'tr', 'echo', 'sh'):
    selected = shutil.which(role, path=str(args.utility_path))
    assert selected and Path(selected).resolve(strict=True).is_relative_to(prefix), role
shell = str(Path(shutil.which('sh', path=str(args.utility_path))).resolve(strict=True))
env = {'PATH': str(args.utility_path), 'LC_ALL': 'C', 'HOME': os.devnull}


def flags(target, universal=None):
    command = [args.gmake, '-s', '-C', args.source, 'SHELL=' + shell,
               'CC=' + shlex.join([args.clang, '--target=' + target]),
               '--eval=show-ember-flags:;@echo EMBER_FLAGS $(IS_APPLE) $(EXT) $(CFLAGS) $(capstone_LDFLAGS)',
               'show-ember-flags']
    if universal is not None:
        command.append('MACOS_UNIVERSAL=' + universal)
    out = subprocess.run(command, check=True, text=True, capture_output=True, env=env).stdout
    return next(line for line in out.splitlines() if line.startswith('EMBER_FLAGS '))

for target in ('arm64-apple-darwin27', 'x86_64-apple-darwin27'):
    output = flags(target)
    assert 'EMBER_FLAGS 1 dylib ' in output, output
    assert '-dynamiclib' in output and '-arch ' not in output and ' -shared' not in output, output
    output = flags(target, 'yes')
    assert '-arch x86_64' in output and '-arch arm64' in output, output
output = flags('aarch64-unknown-netbsd')
assert 'EMBER_FLAGS 0 so ' in output and ' -shared' in output and ' -dynamiclib' not in output, output
print('Capstone target flags: 5 cases passed')
