#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted). Evaluates the policy with an accepted MAKECONF.
"""Check the single make, shell and gzip handoff of the native Darwin host profile.

usage: darwin-bootstrap-make-handoff.py EXPORTED_PKGSRC BMAKE FULL_MAKECONF
       darwin-bootstrap-make-handoff.py --phase-fixture WORK --make-arg ARG ...
           --shell SH --tools-darwin TOOLS_DARWIN_MK

The phase fixture uses a full-format or phase-neutral MAKECONF. It imports
the actual profile and tools.Darwin.mk, with declared recipe paths only.
It queries yes, no and omitted modes without executing future providers.

The initial make builds exactly the dependency closure of devel/bmake and
the dependencies of archivers/gzip. The bmake closure includes shells/mksh and
pkgtools/bootstrap-mk-files, which installs the shell builtin helper. Every
other recipe depends on devel/bmake, runs ${LOCALBASE}/bin/bmake, gives each
shell consumer ${LOCALBASE}/bin/mksh and runs the builtins through the
installed helper. These recipes, except archivers/gzip itself, also depend on
archivers/gzip and run gzip, gunzip and gzcat from ${LOCALBASE}. The seed
recipes and archivers/gzip require no initial gzip provider. No value of a later recipe
names the exported pkgsrc tree, so no installed file can name it.
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
GZIP_PROVIDER = 'archivers/gzip'
# Tool role and the installed program of archivers/gzip. It installs no gzcat.
GZIP_TOOLS = {'gzip': 'bin/gzip', 'gunzip': 'bin/gunzip', 'gzcat': 'bin/zcat'}
GZIP_NAMES = tuple(f'{kind}.{tool}' for kind in ('EMBERBSD_DARWIN_TOOL', 'TOOLS_PLATFORM')
                   for tool in GZIP_TOOLS)
NAMES += SHELLS + BUILTINS + ('EMBERBSD_DARWIN_BUILTIN_HELPER', 'USE_TOOLS',
    'EMBERBSD_DARWIN_NATIVE_TOOLS', 'EMBERBSD_DARWIN_SOURCE_TOOLS', 'DISTFILES', 'PATCHFILES') + GZIP_NAMES
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


def gzip_edges(value):
    """Return the BOOTSTRAP_DEPENDS words on archivers/gzip."""
    return [w for w in shlex.split(value['BOOTSTRAP_DEPENDS']) if w.endswith('../../' + GZIP_PROVIDER)]


def gzip_route(value):
    """Return the program of each gzip tool role, without its arguments."""
    return {tool: (shlex.split(value['TOOLS_PLATFORM.' + tool]) or [''])[0] for tool in GZIP_TOOLS}


def initial_gzip_routes(value):
    """Require an explicit native or source role. Never invent a native path."""
    native = set(value["EMBERBSD_DARWIN_NATIVE_TOOLS"].split())
    source = set(value["EMBERBSD_DARWIN_SOURCE_TOOLS"].split())
    routes = gzip_route(value)
    for tool in GZIP_TOOLS:
        require((tool in native) != (tool in source), f"{tool}: choose exactly one provider kind")
        selected = value["EMBERBSD_DARWIN_TOOL." + tool]
        if tool in native:
            require(selected.startswith("/") and routes[tool] == selected, f"{tool}: native route differs")
        else:
            require(selected == routes[tool] == "", f"{tool}: future tool appeared before handoff")
    return routes


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
    initial_gzip = initial_gzip_routes(first)
    require(GZIP_PROVIDER not in seeds, f'{GZIP_PROVIDER} is built with the initial make')
    for recipe in sorted(set(seeds) | set(LATER) | {GZIP_PROVIDER}):
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
            later = recipe not in seeds and recipe != GZIP_PROVIDER
            require(len(gzip_edges(value)) == (1 if later else 0), f'{recipe}/{mode}: gzip edge changed')
            route = {tool: str(prefix / path) for tool, path in GZIP_TOOLS.items()} if later and handoff else initial_gzip
            require(gzip_route(value) == route, f'{recipe}/{mode}: gzip route {gzip_route(value)}')
            require(not later or set(GZIP_TOOLS) <= set(value['USE_TOOLS'].split()), f'{recipe}/{mode}: bare gzip tools are not shadowed')
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
    gzip_closure, todo = set(), [GZIP_PROVIDER]
    while todo:
        recipe = todo.pop()
        if recipe not in gzip_closure:
            gzip_closure.add(recipe)
            if recipe not in facts:
                facts[recipe] = evaluate(exported, bmake, makeconf, recipe)
            todo += facts[recipe][1] - closure
    gzip_deps = gzip_closure - {GZIP_PROVIDER} - closure
    seeds = set(values['EMBERBSD_DARWIN_SEED_MAKE_RECIPES'].split())
    require(seeds == closure | gzip_deps,
            f'seed make recipes {sorted(seeds)} != closure {sorted(closure | gzip_deps)}')
    closure |= gzip_deps
    plist = (exported / GZIP_PROVIDER / 'PLIST').read_text().splitlines()
    require(set(GZIP_TOOLS.values()) <= set(plist), f'{GZIP_PROVIDER} does not install {sorted(GZIP_TOOLS.values())}')
    initial_gzip = initial_gzip_routes(values)
    require(SHELL_PROVIDER in closure, f'{SHELL_PROVIDER} is not in the {ROOT} closure')
    require(HELPER_PROVIDER in closure, f'{HELPER_PROVIDER} is not in the {ROOT} closure')
    plist = (exported / HELPER_PROVIDER / 'PLIST').read_text().splitlines()
    require('${PLIST.builtin}' + HELPER in plist, f'{HELPER_PROVIDER} does not install {HELPER}')
    seed_shell = values['EMBERBSD_DARWIN_SH']
    seed_helper = exported / 'mk/tools/emberbsd-darwin-builtin.sh'
    for recipe in sorted(closure):
        value, edges = facts[recipe]
        compressed = [name for name in shlex.split(value['DISTFILES'] + ' ' + value['PATCHFILES'])
                      if name.endswith(('.gz', '.tgz', '.taz'))]
        require(not compressed or initial_gzip['gzcat'],
                f'{recipe}: compressed input precedes its gzip provider: {compressed}')
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
        require(GZIP_PROVIDER not in edges and gzip_route(value) == initial_gzip,
                f'{recipe} uses gzip {gzip_route(value)} with edges {sorted(edges)}')
    final = values['LOCALBASE'] + '/bin/bmake'
    final_shell = values['LOCALBASE'] + '/bin/mksh'
    final_helper = values['LOCALBASE'] + '/' + HELPER
    require(final != values['EMBERBSD_DARWIN_MAKE'], 'the initial make is in the final prefix')
    require(final_shell != seed_shell, 'the initial shell is in the final prefix')
    final_gzip = {tool: values['LOCALBASE'] + '/' + path for tool, path in GZIP_TOOLS.items()}
    require(not set(final_gzip.values()) & set(initial_gzip.values()), 'the native gzip is in the final prefix')
    value = facts[GZIP_PROVIDER][0]
    compressed = [name for name in shlex.split(value['DISTFILES'] + ' ' + value['PATCHFILES'])
                  if name.endswith(('.gz', '.tgz', '.taz'))]
    require(not compressed or initial_gzip['gzcat'], 'gzip cannot decompress its own source')
    require(value['MAKE'] == value['_MAKE'] == final and {value[name] for name in SHELLS} == {final_shell},
            f'{GZIP_PROVIDER} is not built with {final} and {final_shell}: {value["MAKE"]} {value["SHELL"]}')
    require(not gzip_edges(value) and gzip_route(value) == initial_gzip,
            f'{GZIP_PROVIDER} uses gzip {gzip_route(value)} with {gzip_edges(value)}')
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
        require(len(gzip_edges(value)) == 1, f'{recipe} lacks one bootstrap edge on {GZIP_PROVIDER}: {gzip_edges(value)}')
        require(gzip_route(value) == final_gzip, f'{recipe} uses gzip {gzip_route(value)} instead of {final_gzip}')
        require(set(GZIP_TOOLS) <= set(value['USE_TOOLS'].split()),
                f'{recipe} does not shadow bare {sorted(GZIP_TOOLS)} commands')
        leaked = sorted(name for name in NAMES if str(exported) in value[name])
        require(not leaked, f'{recipe} names the exported tree in {leaked}')
    print(json.dumps({'seed': sorted(closure), 'later': list(LATER), 'make': final,
                      'shell': final_shell, 'builtin_helper': final_helper, 'gzip': final_gzip,
                      'result': 'PASS'}, sort_keys=True))


if __name__ == '__main__':
    if '--phase-fixture' in sys.argv:
        phase_fixture(sys.argv[1:])
    else:
        main()
