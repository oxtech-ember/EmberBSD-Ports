#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check the single make and shell handoff of the native Darwin host profile.

usage: darwin-bootstrap-make-handoff.py EXPORTED_PKGSRC BMAKE FULL_MAKECONF
       darwin-bootstrap-make-handoff.py --phase-fixture WORK --make-arg ARG ...
           --shell SH --tools-darwin TOOLS_DARWIN_MK

The phase fixture uses a full-format or phase-neutral MAKECONF. It imports
the actual profile and tools.Darwin.mk, with declared recipe paths only.
It queries yes, no and omitted modes without executing future providers.

The initial make builds exactly the dependency closure of devel/bmake.
The closure includes shells/mksh and pkgtools/bootstrap-mk-files, which
installs the shell builtin helper. Every other recipe depends on devel/bmake,
runs ${LOCALBASE}/bin/bmake, gives each shell consumer ${LOCALBASE}/bin/mksh
and runs the builtins through the installed helper. No value of a later
recipe names the exported pkgsrc tree, so no installed file can name it.
"""
import argparse
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
BUILTINS = tuple(f'TOOLS_PLATFORM.{name}' for name in ('[', 'echo', 'false', 'test', 'true'))
NAMES += SHELLS + BUILTINS + ('EMBERBSD_DARWIN_BUILTIN_HELPER',)
ROOT = 'devel/bmake'
SHELL_PROVIDER = 'shells/mksh'
HELPER_PROVIDER = 'pkgtools/bootstrap-mk-files'
HELPER = 'libexec/emberbsd-darwin-builtin.sh'
LATER = ('pkgtools/pkg_install', 'lang/gcc16', 'devel/meson', 'lang/llvm')


def require(value, message):
    if not value:
        raise AssertionError(message)


def gmake_shells(value):
    """Return the SHELL words of the gmake tuple. GNU make uses the last one."""
    return [w.split('=', 1)[1] for w in shlex.split(value['EMBERBSD_DARWIN_GMAKE'])
            if w.startswith('SHELL=')]


def builtins(value, shell, helper):
    """Return the builtin commands that differ from SHELL HELPER NAME."""
    return {name: value[name] for name in BUILTINS
            if value[name] != f'{shell} {helper} {name.split(".", 1)[1]}'}


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


def phase_fixture(argv):
    """Evaluate the real profile without recipes or future shell execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase-fixture', type=Path, required=True)
    parser.add_argument('--make-arg', action='append', required=True)
    parser.add_argument('--shell', required=True)
    parser.add_argument('--tools-darwin', type=Path, required=True)
    args = parser.parse_args(argv)
    work, command = args.phase_fixture, args.make_arg
    require(work.is_absolute() and not work.exists() and not work.is_symlink(), 'Use a fresh absolute fixture work root')
    require(len(command) == 5 and command[1] == '-m' and command[3] == 'SHELL=' + args.shell and
            command[4].startswith('MAKECONF=') and all(os.path.isabs(path) for path in
                (command[0], command[2], args.shell, command[4].removeprefix('MAKECONF='))),
            'Supply the complete selected initial make tuple and shell')
    require(args.tools_darwin.is_absolute(), 'Supply the real source tools.Darwin.mk')
    config = Path(command[4].removeprefix('MAKECONF='))
    config_text = config.read_text()
    require(not any(line.startswith(('_MAKE=', 'MAKE=', 'EMBERBSD_DARWIN_METADATA='))
                    for line in config_text.splitlines()), 'Use full-format or phase-neutral MAKECONF, without metadata post-bindings')
    require(not any(c.isspace() for c in args.shell), 'The fixture .SHELL path must be one word')
    work.mkdir()
    empty = work / 'empty-bin'; empty.mkdir()
    prefix = work / 'unbuilt-prefix'
    env = dict(PATH=str(empty), LC_ALL='C', TZ='UTC', TMPDIR=str(work), SHELL=args.shell)
    observations = {}

    def query(recipe, mode):
        path = work / (recipe.replace('/', '-') + '-' + mode + '.mk')
        path.write_text(f'.SHELL: name=sh path={args.shell} hasErrCtl=no check="set -e" ignore="set +e" echoFlag=v errFlag=e\n'
                        'BSD_PKG_MK=1\n.include "${MAKECONF}"\n'
                        f'PKGPATH= {recipe}\n.include "${{MAKECONF}}"\n.include "${{MAKECONF}}"\n'
                        f'.include "{args.tools_darwin}"\n')
        # .SHELL selects the actual parser child shell. Observe policy SHELL
        # as data, without a command-line SHELL overriding that observation.
        invocation = [word for word in command if not word.startswith('SHELL=')]
        invocation += ['-r', '-f', str(path), 'EMBERBSD_DARWIN_BOOTSTRAP=yes', 'LOCALBASE=' + str(prefix)]
        if mode != 'default':
            invocation += ['EMBERBSD_DARWIN_METADATA=' + mode]
        invocation += [word for name in NAMES for word in ('-V', name + '=${' + name + '}')]
        result = subprocess.run(invocation, cwd=work, env=env, capture_output=True, text=True)
        path.with_suffix('.stdout').write_text(result.stdout)
        path.with_suffix('.stderr').write_text(result.stderr)
        require(result.returncode == 0 and not result.stderr, f'{recipe}/{mode} query failed; inspect {path.with_suffix(".stderr")}')
        lines = result.stdout.splitlines()
        require(len(lines) == len(NAMES), 'The named query roster is incomplete')
        value = dict(zip(NAMES, (line.removeprefix(name + '=') for name, line in zip(NAMES, lines))))
        require(all(line.startswith(name + '=') for name, line in zip(NAMES, lines)), 'The named query framing changed')
        observations[recipe + ':' + mode] = dict(argv=invocation, values=value, exit=result.returncode)
        return value

    first = query(ROOT, 'yes')
    seeds = first['EMBERBSD_DARWIN_SEED_MAKE_RECIPES'].split()
    initial_shell = first['EMBERBSD_DARWIN_SH']
    initial_gmake = shlex.split(first['EMBERBSD_DARWIN_GMAKE'])
    initial_helper = str(args.tools_darwin.with_name('emberbsd-darwin-builtin.sh'))
    for recipe in sorted(set(seeds) | set(LATER)):
        modes = {mode: query(recipe, mode) for mode in ('yes', 'no', 'default')}
        require(modes['no'] == modes['default'], f'{recipe}: omitted flag differs from no')
        require(all(modes['yes'][kind] == modes['no'][kind] for kind in KINDS), f'{recipe}: metadata changes dependency edges')
        for mode, value in modes.items():
            handoff = mode != 'yes' and recipe not in seeds
            shell = str(prefix / 'bin/mksh') if handoff else initial_shell
            helper = str(prefix / HELPER) if handoff else initial_helper
            make = str(prefix / 'bin/bmake') if handoff else value['EMBERBSD_DARWIN_MAKE']
            require(value['MAKE'] == value['_MAKE'] == make, f'{recipe}/{mode}: incomplete make selection')
            require({value[name] for name in SHELLS} == {shell}, f'{recipe}/{mode}: shell selection differs')
            expected_gmake = initial_gmake + (['SHELL=' + shell] if handoff else [])
            require(shlex.split(value['EMBERBSD_DARWIN_GMAKE']) == expected_gmake, f'{recipe}/{mode}: gmake tuple reset or accumulated')
            require(os.path.normpath(value['EMBERBSD_DARWIN_BUILTIN_HELPER']) == helper and not builtins(value, shell, value['EMBERBSD_DARWIN_BUILTIN_HELPER']), f'{recipe}/{mode}: builtin route differs')
            words = [word for word in shlex.split(value['BOOTSTRAP_DEPENDS']) if word.endswith('../../' + ROOT)]
            require(len(words) == (0 if recipe in seeds else 1), f'{recipe}/{mode}: bmake edge changed')
    require(not os.path.lexists(prefix), 'The data fixture created or executed a future provider')
    report = dict(status='PASS', scope='Source profile evaluation only; no native provider qualification', observations=observations)
    (work / 'phase-result.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(status='PASS', result=str(work / 'phase-result.json'))))


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
    require(HELPER_PROVIDER in closure, f'{HELPER_PROVIDER} is not in the {ROOT} closure')
    plist = (exported / HELPER_PROVIDER / 'PLIST').read_text().splitlines()
    require('${PLIST.builtin}' + HELPER in plist, f'{HELPER_PROVIDER} does not install {HELPER}')
    seed_shell = values['EMBERBSD_DARWIN_SH']
    seed_helper = exported / 'mk/tools/emberbsd-darwin-builtin.sh'
    for recipe in sorted(closure):
        value, edges = facts[recipe]
        require(value['MAKE'] == value['_MAKE'] == value['EMBERBSD_DARWIN_MAKE'],
                f'{recipe} does not use the initial make: {value["MAKE"]}')
        require(recipe == ROOT or ROOT not in edges, f'{recipe} depends on the make it seeds')
        require({value[name] for name in SHELLS} == {seed_shell},
                f'{recipe} does not use the initial shell: {[value[n] for n in SHELLS]}')
        require(set(gmake_shells(value)) <= {seed_shell},
                f'{recipe} gives gmake {gmake_shells(value)}')
        helper = value['EMBERBSD_DARWIN_BUILTIN_HELPER']
        require(Path(os.path.normpath(helper)) == seed_helper,
                f'{recipe} uses the builtin helper {helper}')
        require(not builtins(value, seed_shell, helper),
                f'{recipe} runs builtins {builtins(value, seed_shell, helper)}')
    final = values['LOCALBASE'] + '/bin/bmake'
    final_shell = values['LOCALBASE'] + '/bin/mksh'
    final_helper = values['LOCALBASE'] + '/' + HELPER
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
        require(not builtins(value, final_shell, final_helper),
                f'{recipe} runs builtins {builtins(value, final_shell, final_helper)}')
        leaked = sorted(name for name in NAMES if str(exported) in value[name])
        require(not leaked, f'{recipe} names the exported tree in {leaked}')
    print(json.dumps({'seed': sorted(closure), 'later': list(LATER), 'make': final,
                      'shell': final_shell, 'builtin_helper': final_helper,
                      'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    if '--phase-fixture' in sys.argv:
        phase_fixture(sys.argv[1:])
    else:
        main()
