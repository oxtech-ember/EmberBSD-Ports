#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Check that the Darwin build shell and package tools stay off GCC16.

"pkg_add -U" removes the old GCC16 package before it installs the new one,
and the package scripts run with the build shell. If mksh, bmake or a
pkg_install tool loads a library from the GCC16 prefix, a GCC16 update
breaks the tools that perform it. The check follows every dylib and rpath
of those tools, also through their non-system libraries:

  python3 -B darwin-build-tools-isolation.py --prefix PREFIX \\
      [--pkg-sbin PKG_INSTALL_SBIN]

PREFIX/gcc16 is the GCC16 prefix. The pkg_install tools default to
PREFIX/sbin.
"""

import argparse
import importlib.util
from pathlib import Path
import sys

sys.dont_write_bytecode = True
TESTS = Path(__file__).resolve().parent
SHELL_TOOLS = ('bin/mksh', 'bin/bmake')
PKG_TOOLS = ('pkg_add', 'pkg_admin', 'pkg_create', 'pkg_delete', 'pkg_info')
SYSTEM = (Path('/usr/lib'), Path('/System'))


def load_macho():
    spec = importlib.util.spec_from_file_location('darwin_libc_ssp', TESTS / 'darwin-libc-ssp.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.mach_o_load_commands


def expand(name, image, executable, rpaths):
    """Return the paths dyld may load for one install name."""
    if name.startswith('@rpath/'):
        return [Path(expand(r, image, executable, [])[0]) / name[7:] for r in rpaths]
    if name.startswith('@loader_path/'):
        return [image.parent / name[13:]]
    if name.startswith('@executable_path/'):
        return [executable.parent / name[17:]]
    return [Path(name)]


def violations(tool, gcc_prefix, load):
    """Return (image, reference) pairs that point into the GCC16 prefix."""
    found, seen, queue = [], set(), [tool]
    while queue:
        image = queue.pop()
        if image in seen:
            continue
        seen.add(image)
        info = load(image)
        rpaths = [p for r in info['rpaths'] for p in expand(r, image, tool, [])]
        for path in rpaths:
            if path.resolve().is_relative_to(gcc_prefix):
                found.append((image, 'LC_RPATH %s' % path))
        for name in info['dylibs']:
            for path in expand(name, image, tool, rpaths):
                if path.resolve().is_relative_to(gcc_prefix):
                    found.append((image, name))
                elif path.exists() and not any(path.is_relative_to(s) for s in SYSTEM):
                    queue.append(path.resolve())
    return found


def audit(tools, gcc_prefix, load):
    bad = []
    for tool in tools:
        assert tool.is_file(), 'missing build tool: %s' % tool
        bad += violations(tool, gcc_prefix, load)
    for image, reference in bad:
        print('FAIL: %s loads %s' % (image, reference))
    assert not bad, 'build tools depend on the GCC16 prefix %s' % gcc_prefix
    print('PASS: %d build tools load nothing from %s' % (len(tools), gcc_prefix))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--pkg-sbin', type=Path)
    args = parser.parse_args(argv)
    prefix = args.prefix.resolve()
    sbin = (args.pkg_sbin or prefix / 'sbin').resolve()
    tools = [prefix / t for t in SHELL_TOOLS] + [sbin / t for t in PKG_TOOLS]
    audit(tools, prefix / 'gcc16', load_macho())


if __name__ == '__main__':
    main()
