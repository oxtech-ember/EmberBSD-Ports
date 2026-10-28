#!/usr/bin/env python3
"""Check the compiler bindings in a generated cross-libtool script."""
import argparse
import re
import shlex
from pathlib import Path


def check(script, cc, cxx):
    blocks = re.split(r'^# ### BEGIN LIBTOOL TAG CONFIG: (\S+)\s*$', script,
                      flags=re.MULTILINE)
    configs = {'C': blocks[0]}
    configs.update(zip(blocks[1::2], blocks[2::2]))
    for tag, expected in [('C', cc), ('CXX', cxx), ('OBJC', cc), ('OBJCXX', cxx)]:
        match = re.search(r'^CC="([^"]*)"$', configs.get(tag, ''), re.MULTILINE)
        if not match or not shlex.split(match.group(1)) or shlex.split(match.group(1))[0] != expected:
            raise ValueError(f'{tag} does not use {expected}')
    for tag in ('ML64', 'F77', 'FC', 'GO', 'GCJ', 'RC'):
        match = re.search(r'^CC="([^"]*)"$', configs.get(tag, ''), re.MULTILINE)
        if not match or match.group(1):
            raise ValueError(f'{tag} unexpectedly selects a compiler')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('script', type=Path)
    p.add_argument('--cc', required=True)
    p.add_argument('--cxx', required=True)
    args = p.parse_args()
    check(args.script.read_text(), args.cc, args.cxx)
    print('cross-libtool tag bindings: PASS')


if __name__ == '__main__':
    main()
