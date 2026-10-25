#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check that the native Darwin host profile builds Ruby without YJIT.

usage: darwin-bootstrap-ruby-yjit.py EXPORTED_PKGSRC BMAKE MAKECONF

YJIT needs lang/rust, which needs a foreign stage-0 binary and an LLVM
libunwind that the common profile does not prepare. The native Darwin host
profile disables it. Builds outside that profile keep the upstream default.
On aarch64 and x86_64 upstream makes YJIT a required option group;
pkgsrc-ruby40-optional-jit.patch makes it optional so it can be disabled.
"""
import json
import shlex
import subprocess
import sys
from pathlib import Path


def require(value, message):
    if not value:
        raise AssertionError(message)


def evaluate(exported, bmake, makeconf, bootstrap):
    names = ['PKG_OPTIONS', 'CONFIGURE_ARGS', 'BUILD_DEPENDS', 'TOOL_DEPENDS', 'PKG_FAIL_REASON']
    # Outside the host profile EMBERBSD_DARWIN_BOOTSTRAP stays undefined.
    # Without a package database, answer installed-option queries as empty
    # instead of recursing through the Rust and LLVM recipes.
    policy = ['EMBERBSD_DARWIN_BOOTSTRAP=yes'] if bootstrap else ['PKG_INFO=/usr/bin/true']
    out = subprocess.run([bmake, '-C', str(exported / 'lang/ruby40'), *policy,
                          f'MAKECONF={makeconf}', 'show-vars', f'VARNAMES={" ".join(names)}'],
                         check=True, capture_output=True, text=True,
                         env={'PATH': '/usr/bin:/bin'}).stdout.splitlines()
    return {name: shlex.split(value) for name, value in zip(names, out)}


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    exported, bmake, makeconf = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    host = evaluate(exported, bmake, makeconf, True)
    # show-vars succeeds even when the options make the recipe unbuildable.
    require(not host['PKG_FAIL_REASON'], f'host profile cannot build Ruby: {host["PKG_FAIL_REASON"]}')
    require('ruby-yjit' not in host['PKG_OPTIONS'], f'host profile selects YJIT: {host["PKG_OPTIONS"]}')
    require('--disable-yjit' in host['CONFIGURE_ARGS'], 'host profile does not pass --disable-yjit')
    rust = [d for d in host['BUILD_DEPENDS'] + host['TOOL_DEPENDS'] if 'lang/rust' in d]
    require(not rust, f'host profile still depends on Rust: {rust}')
    other = evaluate(exported, bmake, '/dev/null', False)
    require('ruby-yjit' in other['PKG_OPTIONS'], 'the upstream default changed outside the host profile')
    print(json.dumps({'host': host['PKG_OPTIONS'], 'other': other['PKG_OPTIONS'],
                      'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
