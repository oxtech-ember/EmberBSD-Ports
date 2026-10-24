#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check that GNU grep requests use the selected grep, not Ports grep.

usage: darwin-bootstrap-ggrep.py EXPORTED_PKGSRC BMAKE MAKECONF WORK

archivers/zstd requests ggrep. Ports grep needs bash, bison, flex and
help2man; help2man needs gettext-tools, python and then zstd again. The
policy must give ggrep the selected grep, as ordinary Darwin does, and an
explicit native ggrep selection must still win.
"""
import json
import subprocess
import sys
from pathlib import Path

NAMES = ['EMBERBSD_DARWIN_NATIVE_TOOLS', 'TOOLS_PLATFORM.grep', 'TOOLS_PLATFORM.ggrep',
         '_TOOLS_USE_PKGSRC.ggrep', 'TOOL_DEPENDS']


def require(value, message):
    if not value:
        raise AssertionError(message)


def show(exported, bmake, makeconf):
    out = subprocess.run([bmake, '-C', str(exported / 'archivers/zstd'), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                          f'MAKECONF={makeconf}', 'show-vars', f'VARNAMES={" ".join(NAMES)}'],
                         check=True, capture_output=True, text=True,
                         env={'PATH': '/usr/bin:/bin'}).stdout.splitlines()
    require(len(out) == len(NAMES), f'Unexpected show-vars output: {out!r}')
    return dict(zip(NAMES, out))


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    exported, bmake, makeconf, work = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    plain = show(exported, bmake, makeconf)
    require('ggrep' not in plain['EMBERBSD_DARWIN_NATIVE_TOOLS'].split(),
            'This MAKECONF already selects ggrep; give one that selects only grep')
    grep = plain['TOOLS_PLATFORM.grep']
    require(grep.startswith('/'), f'The MAKECONF selects no native grep: {grep!r}')
    require(plain['TOOLS_PLATFORM.ggrep'] == grep,
            f'ggrep does not use the selected grep: {plain["TOOLS_PLATFORM.ggrep"]!r}')
    require(plain['_TOOLS_USE_PKGSRC.ggrep'] == 'no', 'ggrep still selects Ports grep')
    require('textproc/grep' not in plain['TOOL_DEPENDS'], 'zstd still depends on Ports grep')
    work.mkdir(parents=True)
    selected = work / 'ggrep'
    selected.symlink_to(grep)
    explicit = work / 'explicit.mk.conf'
    explicit.write_text(f'.include "{makeconf}"\nEMBERBSD_DARWIN_NATIVE_TOOLS+= ggrep\n'
                        f'EMBERBSD_DARWIN_TOOL.ggrep= {selected}\n')
    chosen = show(exported, bmake, explicit)
    require(chosen['TOOLS_PLATFORM.ggrep'] == str(selected),
            f'An explicit ggrep selection was overridden: {chosen["TOOLS_PLATFORM.ggrep"]!r}')
    print(json.dumps({'ggrep': plain['TOOLS_PLATFORM.ggrep'], 'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
