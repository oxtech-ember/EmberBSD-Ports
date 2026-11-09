#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Evaluate the prepared Ruby JIT rules with and without a Rust library."""

import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', type=Path, required=True)
    parser.add_argument('--jit-mk', type=Path, required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix='ruby-jit-link-') as tmp:
        makefile = Path(tmp) / 'Makefile'
        makefile.write_text(
            'JIT_CARGO_SUPPORT = no\n'
            'LIBRUBY_SO = libruby.dylib\n'
            'OBJS = vm.o\nDLDOBJS = dmyext.o\n'
            f'include {args.jit_mk.resolve()}\n'
            '.PHONY: check\ncheck:\n'
            '\t$(info FORCE=$(RUST_LIB_FORCE_LOAD_FLAGS))\n'
            '\t$(info LINK=$(RUST_LIB_LINK_FLAGS))\n'
            '\t$(info MERGE=$(RUST_LIB_MERGE))\n'
            '\t@:\n'
        )
        for os_name, jit in [('darwin27', False), ('darwin27', True),
                             ('netbsd11', False), ('netbsd11', True)]:
            result = subprocess.run(
                [str(args.make.resolve()), '-rR', '--no-print-directory',
                 '-f', str(makefile), 'check', f'target_os={os_name}',
                 f'RUST_LIB={"libjit.a" if jit else ""}',
                 f'RUST_LIBOBJ={"jit.o" if jit else ""}'],
                cwd=tmp, capture_output=True, text=True, check=True,
            )
            values = dict(line.split('=', 1) for line in result.stdout.splitlines())
            force, link, merge = (values[key] for key in ('FORCE', 'LINK', 'MERGE'))
            if os_name.startswith('darwin') and jit:
                assert force == '-Wl,-force_load,libjit.a', force
                assert link == (force + ' -Wl,-exported_symbols_list,libjit.exports'), link
                assert '"libjit.a"' in merge and 'addlib' in merge, merge
            else:
                assert (force, link, merge) == ('', '', ':'), (os_name, jit, result.stdout)

    print('PASS: Darwin JIT final links retain the Rust archive; no-JIT and ELF flags stay empty')


if __name__ == '__main__':
    main()
