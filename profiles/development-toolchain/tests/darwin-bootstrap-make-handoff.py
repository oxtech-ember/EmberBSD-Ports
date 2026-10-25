#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check the single make and shell handoff of the native Darwin host profile.

usage: darwin-bootstrap-make-handoff.py EXPORTED_PKGSRC BMAKE MAKECONF

The initial make builds exactly the dependency closure of devel/bmake.
The closure includes shells/mksh. Every other recipe depends on devel/bmake,
runs ${LOCALBASE}/bin/bmake and gives each shell consumer ${LOCALBASE}/bin/mksh.
"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

KINDS = ('BOOTSTRAP_DEPENDS', 'TOOL_DEPENDS', 'BUILD_DEPENDS', 'DEPENDS')
NAMES = ('EMBERBSD_DARWIN_SEED_MAKE_RECIPES', 'EMBERBSD_DARWIN_MAKE', 'EMBERBSD_DARWIN_GMAKE',
         'LOCALBASE', 'MAKE', '_MAKE', *KINDS)
SHELLS = ('EMBERBSD_DARWIN_SH', 'SHELL', 'SH', 'CONFIG_SHELL', 'TOOLS_SHELL',
          'EMBERBSD_DARWIN_BUILTIN_SHELL', 'TOOLS_PLATFORM.sh')
NAMES += SHELLS
ROOT = 'devel/bmake'
SHELL_PROVIDER = 'shells/mksh'
LATER = ('pkgtools/pkg_install', 'lang/gcc16', 'devel/meson', 'lang/llvm')


def require(value, message):
    if not value:
        raise AssertionError(message)


def gmake_shells(value):
    """Return the SHELL words of the gmake tuple. GNU make uses the last one."""
    return [w.split('=', 1)[1] for w in shlex.split(value['EMBERBSD_DARWIN_GMAKE'])
            if w.startswith('SHELL=')]


def evaluate(exported, bmake, makeconf, recipe):
    out = subprocess.run([bmake, '-C', str(exported / recipe), 'EMBERBSD_DARWIN_BOOTSTRAP=yes',
                          f'MAKECONF={makeconf}', 'show-vars', f'VARNAMES={" ".join(NAMES)}'],
                         check=True, capture_output=True, text=True,
                         env={'PATH': '/usr/bin:/bin'}).stdout.splitlines()
    values = dict(zip(NAMES, out))
    edges = set()
    for kind in KINDS:
        for word in shlex.split(values[kind]):
            path = word.split(':', 1)[1]
            edges.add(os.path.relpath(os.path.normpath(exported / recipe / path), exported))
    return values, edges


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    exported, bmake, makeconf = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    closure, todo, facts = set(), [ROOT], {}
    while todo:
        recipe = todo.pop()
        if recipe not in closure:
            closure.add(recipe)
            facts[recipe] = evaluate(exported, bmake, makeconf, recipe)
            todo += facts[recipe][1]
    values = facts[ROOT][0]
    seeds = set(values['EMBERBSD_DARWIN_SEED_MAKE_RECIPES'].split())
    require(seeds == closure, f'seed make recipes {sorted(seeds)} != closure {sorted(closure)}')
    require(SHELL_PROVIDER in closure, f'{SHELL_PROVIDER} is not in the {ROOT} closure')
    seed_shell = values['EMBERBSD_DARWIN_SH']
    for recipe in sorted(closure):
        value, edges = facts[recipe]
        require(value['MAKE'] == value['_MAKE'] == value['EMBERBSD_DARWIN_MAKE'],
                f'{recipe} does not use the initial make: {value["MAKE"]}')
        require(recipe == ROOT or ROOT not in edges, f'{recipe} depends on the make it seeds')
        require({value[name] for name in SHELLS} == {seed_shell},
                f'{recipe} does not use the initial shell: {[value[n] for n in SHELLS]}')
        require(set(gmake_shells(value)) <= {seed_shell},
                f'{recipe} gives gmake {gmake_shells(value)}')
    final = values['LOCALBASE'] + '/bin/bmake'
    final_shell = values['LOCALBASE'] + '/bin/mksh'
    require(final != values['EMBERBSD_DARWIN_MAKE'], 'the initial make is in the final prefix')
    require(final_shell != seed_shell, 'the initial shell is in the final prefix')
    for recipe in LATER:
        value, edges = evaluate(exported, bmake, makeconf, recipe)
        require(value['MAKE'] == value['_MAKE'] == final,
                f'{recipe} uses {value["MAKE"]} instead of {final}')
        words = [w for w in shlex.split(value['BOOTSTRAP_DEPENDS']) if w.endswith('../../' + ROOT)]
        require(len(words) == 1, f'{recipe} lacks one bootstrap edge on {ROOT}: {words}')
        require({value[name] for name in SHELLS} == {final_shell},
                f'{recipe} does not use {final_shell}: {[value[n] for n in SHELLS]}')
        require(gmake_shells(value)[-1:] == [final_shell],
                f'{recipe} gives gmake {gmake_shells(value)}')
    print(json.dumps({'seed': sorted(closure), 'later': list(LATER), 'make': final,
                      'shell': final_shell,
                      'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    main()
