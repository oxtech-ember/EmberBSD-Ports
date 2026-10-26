#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
"""Evaluate the opt-in NetBSD first-native profile with the selected bmake.

This is a metadata and make-policy test. It never compiles C/C++ code or
executes a package build phase. Package metadata may query compiler identity.
"""
import argparse
import hashlib
import os
import shutil
import shlex
import stat
import subprocess
import tempfile
from pathlib import Path


KINDS = ('BOOTSTRAP_DEPENDS', 'TOOL_DEPENDS', 'BUILD_DEPENDS', 'DEPENDS')
VARS = (*KINDS, 'TEST_DEPENDS', 'MAKE', '_MAKE', 'SHELL', 'SH', 'CONFIG_SHELL', 'TOOLS_SHELL',
        'PKGNAME', 'PATH', 'EMBERBSD_NETBSD_UTILITY_BIN',
        'NAWK_COMMAND_SHELL', '_EMBERBSD_NETBSD_INITIAL_SH', 'MAKE_FLAGS',
        'EMBERBSD_NETBSD_NATIVE_TOOLS', 'EMBERBSD_NETBSD_TOOL.uniq',
        'WRAPPER_BINDIR', 'BUILDLINK_DIR', 'TOOLS_DIR', '_GCC_DIR',
        'CC', 'CXX', 'CPP', 'PKG_CC', 'PKG_CXX', 'PKG_CPP',
        'CWRAPPERS_PREPEND.cc', 'CWRAPPERS_PREPEND.cxx', 'CWRAPPERS_PREPEND.cpp',
        'AS', 'LD', 'AR', 'RANLIB', 'NM', 'STRIP', '_CC', 'GCCBASE',
        'CONFIGURE_ARGS', 'CONFIGURE_ARGS.NetBSD', 'MAKE_JOBS', 'LOCALBASE', 'NATIVE_OPSYS',
        'NATIVE_OPSYS_VERSION', 'MACHINE_ARCH',
        '_EMBERBSD_NETBSD_BOOTSTRAP_POLICY', 'EMBERBSD_NETBSD_MAKE',
        'EMBERBSD_NETBSD_SH', 'EMBERBSD_NETBSD_GMAKE',
        'EMBERBSD_GCC16_SEED_CC', 'EMBERBSD_GCC16_SEED_CXX',
        'EMBERBSD_GCC16_SEED_CPP', 'EMBERBSD_GCC16_AS', 'EMBERBSD_GCC16_LD',
        'EMBERBSD_GCC16_AR', 'EMBERBSD_GCC16_RANLIB', 'EMBERBSD_GCC16_NM',
        'EMBERBSD_GCC16_STRIP', 'EMBERBSD_NETBSD_TOOL.awk', 'EMBERBSD_NETBSD_TOOL.uname',
        'EMBERBSD_NETBSD_TOOL.grep', 'EMBERBSD_NETBSD_TOOL.sed',
        'EMBERBSD_NETBSD_TOOL.pkg-config', 'EMBERBSD_NETBSD_SOURCE_TOOLS',
        'TOOLS_PLATFORM.make', 'TOOLS_PLATFORM.gmake', 'TOOLS_PLATFORM.cc',
        'TOOLS_PLATFORM.ar', 'TOOLS_PLATFORM.as', 'TOOLS_PLATFORM.ld',
        'TOOLS_PLATFORM.ranlib', 'TOOLS_PLATFORM.nm', 'TOOLS_PLATFORM.strip',
        'TOOLS_PLATFORM.cpp', 'TOOLS_PLATFORM.c++', 'TOOLS_PLATFORM.g++', 'TOOLS_PLATFORM.awk', 'TOOLS_PLATFORM.sh',
        'TOOLS_PLATFORM.pkg-config', 'TOOLS_PLATFORM.uniq',
        'TOOLS_PLATFORM.bison-yacc',
        'PLIST.builtin', 'INSTALLATION_DIRS',
        'USE_PKGSRC_GCC', 'USE_PKGSRC_GCC_RUNTIME',
        'TOOLS_PLATFORM.awk', 'TOOLS_PLATFORM.uname', 'TOOLS_PLATFORM.grep', 'TOOLS_PLATFORM.gmake',
        'TOOLS_AWK', 'TOOLS_GREP', 'TOOLS_SED', 'TOOLS_CMDLINE_AWK',
        'TOOLS_CMDLINE_GREP', 'TOOLS_CMDLINE_SED', 'AWK', 'GREP', 'SED',
        'TOOLS_PLATFORM.[', 'TOOLS_PLATFORM.echo', 'TOOLS_PLATFORM.false',
        'TOOLS_PLATFORM.test', 'TOOLS_PLATFORM.true',
        'EMBERBSD_NETBSD_BOOTSTRAP_POLICY')
FOUNDATION = {
    'devel/binutils', 'devel/bmake', 'devel/gmake', 'shells/mksh',
    'lang/python315',
}
PROFILE = 'EMBERBSD-NETBSD-BOOTSTRAP-MK.CONF'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def words(value):
    return shlex.split(value)


def run_make(bmake, bootstrap_mk, export, source_tree, makeconf, recipe, work,
             *, overrides=(), enabled=True, synthetic=False):
    recipe_dir = export / recipe
    if not (recipe_dir / 'Makefile').is_file() and source_tree is not None:
        source_dir = source_tree / recipe
        require((source_dir / 'Makefile').is_file(),
                f'pkgsrc source recipe is unavailable: {source_dir}')
        recipe_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, recipe_dir, symlinks=True)
    if synthetic:
        recipe_dir.mkdir(parents=True, exist_ok=True)
        makefile = work / f'fixture-{recipe.replace("/", "-")}.mk'
        makefile.write_text('.include "${PKGSRC}/mk/bsd.prefs.mk"\n'
                            f'PKGPATH= {recipe}\n'
                            '.include "${PKGSRC}/mk/tools/tools.NetBSD.mk"\n'
                            '.include "${PKGSRC}/mk/bsd.pkg.mk"\n')
    else:
        makefile = recipe_dir / 'Makefile'
    command = [str(bmake), '-r', '-m', str(export / 'mk'),
               '-m', str(bootstrap_mk), '-f', str(makefile),
               f'PKGSRC={export}', f'PKGSRCDIR={export}', f'MAKECONF={makeconf}',
               f'PKGPATH={recipe}', *overrides,
               *[item for name in VARS for item in ('-V', '${' + name + '}')]]
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'TZ': 'UTC', 'HOME': str(work)}
    if enabled:
        env['EMBERBSD_NETBSD_BOOTSTRAP'] = 'yes'
    return subprocess.run(command, cwd=recipe_dir, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def unpack(result):
    require(result.returncode == 0, 'make profile evaluation failed: ' + result.stderr)
    lines = result.stdout.splitlines()
    require(len(lines) == len(VARS), f'make output frame changed: {lines!r}')
    return dict(zip(VARS, lines))


def shell_probe(bmake, bootstrap_mk, export, makeconf, work):
    with tempfile.TemporaryDirectory(prefix='netbsd-shell-probe-', dir=work) as temp_name:
        makefile = Path(temp_name) / 'Makefile'
        makefile.write_text('.include "${PKGSRC}/mk/bsd.prefs.mk"\n'
                            'all:\n\t@printf "%s\\n" "$$KSH_VERSION"\n')
        proc = subprocess.run([str(bmake), '-r', '-m', str(export / 'mk'),
                               '-m', str(bootstrap_mk), '-f', str(makefile),
                               f'PKGSRC={export}', f'PKGSRCDIR={export}',
                               f'MAKECONF={makeconf}', 'all'],
                              cwd=export / 'lang/gcc16', env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C',
                                                   'TZ': 'UTC', 'HOME': temp_name,
                                                   'EMBERBSD_NETBSD_BOOTSTRAP': 'yes'},
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        require(proc.returncode == 0, 'shell probe failed: ' + proc.stderr)
        return proc.stdout.strip()


def repeated_profile_probe(bmake, bootstrap_mk, export, makeconf, work):
    with tempfile.TemporaryDirectory(prefix='netbsd-profile-rebind-', dir=work) as temp_name:
        makefile = Path(temp_name) / 'Makefile'
        makefile.write_text(
            'PKGPATH= archivers/zstd\n'
            '.include "${PKGSRC}/mk/bsd.prefs.mk"\n'
            'EMBERBSD_NETBSD_SOURCE_TOOLS= pkg-config\n'
            'EMBERBSD_NETBSD_TOOL.pkg-config= ${LOCALBASE}/bin/pkg-config\n'
            'MAKE= /outer/config/make\n'
            '_MAKE= /outer/config/make\n'
            'EMBERBSD_NETBSD_MAKE= /outer/config/make\n'
            'EMBERBSD_NETBSD_GMAKE= /outer/config/gmake\n'
            'EMBERBSD_NETBSD_SH= /outer/config/sh\n'
            'SHELL= /outer/config/sh\n'
            'SH= /outer/config/sh\n'
            'CONFIG_SHELL= /outer/config/sh\n'
            'TOOLS_SHELL= /outer/config/sh\n'
            'TOOLS_PLATFORM.make= /outer/config/make\n'
            'TOOLS_PLATFORM.gmake= /outer/config/gmake\n'
            'TOOLS_PLATFORM.cc= /outer/config/cc\n'
            'TOOLS_PLATFORM.awk= /outer/config/awk\n'
            'TOOLS_PLATFORM.pkg-config= /outer/config/pkg-config\n'
            'NAWK_COMMAND_SHELL= /outer/config/sh\n'
            '.include "${MAKECONF}"\n')
        command = [str(bmake), '-r', '-m', str(export / 'mk'),
                   '-m', str(bootstrap_mk), '-f', str(makefile),
                   f'PKGSRC={export}', f'PKGSRCDIR={export}',
                   f'MAKECONF={makeconf}', 'PKGPATH=archivers/zstd',
                   *[item for name in VARS for item in ('-V', '${' + name + '}')]]
        proc = subprocess.run(command, cwd=export / 'archivers/zstd',
                              env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C',
                                   'TZ': 'UTC', 'HOME': temp_name,
                                   'EMBERBSD_NETBSD_BOOTSTRAP': 'yes'},
                              text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        return unpack(proc)


def builtin_helper_probe(bmake, bootstrap_mk, export, makeconf, work,
                         *, enabled=True, overrides=()):
    values = unpack(run_make(bmake, bootstrap_mk, export, export, makeconf,
                             'pkgtools/bootstrap-mk-files', work,
                             enabled=enabled, overrides=overrides))
    require(values['PLIST.builtin'] == 'yes' and
            'libexec' in words(values['INSTALLATION_DIRS']),
            'NetBSD bootstrap-mk-files metadata does not install the builtin helper: '
            + repr({name: values[name] for name in ('PLIST.builtin', 'INSTALLATION_DIRS')}))

    prefix = Path(values['LOCALBASE'])
    package = export / 'pkgtools/bootstrap-mk-files'
    with tempfile.TemporaryDirectory(prefix='netbsd-builtin-install-', dir=work) as temp_name:
        root = Path(temp_name)
        wrksrc = root / 'wrksrc'
        destdir = root / 'destdir'
        wrksrc.mkdir()
        destdir.mkdir()
        (wrksrc / 'bsd.README').write_text('fixture makefile\n')
        (wrksrc / 'sys.mk').write_text('# fixture sys.mk\n')
        dest_prefix = destdir.joinpath(*prefix.parts[1:])
        for directory in words(values['INSTALLATION_DIRS']):
            (dest_prefix / directory).mkdir(parents=True, exist_ok=True)
        command = [str(bmake), '-r', '-m', str(export / 'mk'),
                   '-m', str(bootstrap_mk), '-f', str(package / 'Makefile'),
                   f'PKGSRC={export}', f'PKGSRCDIR={export}',
                   f'MAKECONF={makeconf}', 'PKGPATH=pkgtools/bootstrap-mk-files',
                   f'LOCALBASE={prefix}', f'PREFIX={prefix}',
                   f'WRKSRC={wrksrc}', f'DESTDIR={destdir}', 'do-install']
        env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'TZ': 'UTC',
               'HOME': str(root), 'EMBERBSD_NETBSD_BOOTSTRAP': 'yes'}
        installed = subprocess.run(command, cwd=package, env=env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        require(installed.returncode == 0,
                'bootstrap-mk-files do-install failed: ' + installed.stderr)
        installed_helper = dest_prefix / 'libexec/emberbsd-darwin-builtin.sh'
        source_helper = export / 'mk/tools/emberbsd-darwin-builtin.sh'
        require(installed_helper.is_file(),
                'NetBSD bootstrap-mk-files do-install omitted the builtin helper')
        require(stat.S_IMODE(installed_helper.stat().st_mode) == 0o755,
                'bootstrap-mk-files did not install the builtin helper as a script')
        require(hashlib.sha256(installed_helper.read_bytes()).digest() ==
                hashlib.sha256(source_helper.read_bytes()).digest(),
                'installed builtin helper differs from the exported source')

        shell = prefix / 'bin/mksh'

        def dispatch(name, args, expected_status, expected_stdout):
            result = subprocess.run([str(shell), str(installed_helper), name, *args],
                                    env=env, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            require(result.returncode == expected_status and
                    result.stdout == expected_stdout,
                    f'builtin {name} dispatch mismatch: status={result.returncode}, '
                    f'stdout={result.stdout!r}, stderr={result.stderr!r}')

        dispatch('echo', ['NetBSD', 'helper'], 0, 'NetBSD helper\n')
        dispatch('true', [], 0, '')
        dispatch('false', [], 1, '')
        dispatch('test', ['probe', '=', 'probe'], 0, '')
        dispatch('[', ['probe', '=', 'probe', ']'], 0, '')


def edges(values):
    result = set()
    for kind in KINDS:
        for spec in words(values[kind]):
            path = spec.rsplit(':', 1)[-1]
            if path.startswith('../../'):
                path = path.rstrip('}')
                result.add(os.path.normpath(path.removeprefix('../../')))
    return result


def edge_specs(values, *, include_tests=False):
    kinds = (*KINDS, 'TEST_DEPENDS') if include_tests else KINDS
    for kind in kinds:
        for spec in words(values[kind]):
            pattern, path = spec.rsplit(':', 1)
            if path.startswith('../../'):
                yield pattern, os.path.normpath(path.removeprefix('../../'))


def check_dependency_patterns(policy_graph, package_names, pkg_admin, pkg_admin_sha256,
                              *, include_tests=False):
    require(pkg_admin.is_absolute() and pkg_admin.is_file(),
            f'pkg_admin must be an explicit existing absolute path: {pkg_admin}')
    actual_hash = hashlib.sha256(pkg_admin.read_bytes()).hexdigest()
    require(actual_hash == pkg_admin_sha256,
            f'pkg_admin SHA256 mismatch: expected {pkg_admin_sha256}, got {actual_hash}')
    for parent, values in policy_graph.items():
        for pattern, provider in edge_specs(values, include_tests=include_tests):
            require(provider in package_names,
                    f'{parent} refers to a provider absent from the evaluated graph: {provider}')
            result = subprocess.run(
                [str(pkg_admin), 'pmatch', pattern, package_names[provider]],
                env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'TZ': 'UTC'},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            require(result.returncode == 0,
                    f'{parent} dependency pattern {pattern!r} does not match '
                    f'{provider} PKGNAME {package_names[provider]!r}: {result.stderr}')
    # Prove that the selected matcher rejects a provider name outside a pin.
    if not include_tests:
        require(any(pattern == 'gtexinfo>=7.3'
                    for values in policy_graph.values()
                    for pattern, _ in edge_specs(values)),
                'the graph lost its gtexinfo 7.3 source pin')
        negative = subprocess.run(
            [str(pkg_admin), 'pmatch', 'gtexinfo>=7.3', 'gtexinfo-7.2nb99'],
            env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'TZ': 'UTC'},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        require(negative.returncode != 0,
                'pkg_admin pmatch accepted gtexinfo below the selected 7.3 floor')


def check(export, source_tree, bmake, makeconf, bootstrap_mk, work,
          pkg_admin, pkg_admin_sha256):
    profile = export / PROFILE
    native_tools = next((line.split('=', 1)[1].strip()
                         for line in makeconf.read_text().splitlines()
                         if line.startswith('EMBERBSD_NETBSD_NATIVE_TOOLS=')), None)
    require(native_tools, 'MAKECONF has no closed native utility roster')
    extended_roster = ' '.join((*[role for role in words(native_tools) if role != 'uniq'],
                               'uniq'))
    unbound_utility = run_make(
        bmake, bootstrap_mk, export, source_tree, makeconf, 'lang/gcc16', work,
        overrides=('EMBERBSD_NETBSD_NATIVE_TOOLS=' + extended_roster,
                   'EMBERBSD_NETBSD_TOOL.uniq='))
    require(unbound_utility.returncode != 0,
            'the source profile accepted uniq without an admitted utility route')
    uniq_path = '/netbsd-profile-test/utility/bin/uniq'
    routed_utility = unpack(run_make(
        bmake, bootstrap_mk, export, source_tree, makeconf, 'lang/gcc16', work,
        overrides=('EMBERBSD_NETBSD_NATIVE_TOOLS=' + extended_roster,
                   'EMBERBSD_NETBSD_TOOL.uniq=' + uniq_path)))
    require('uniq' in words(routed_utility['EMBERBSD_NETBSD_NATIVE_TOOLS']) and
            routed_utility['EMBERBSD_NETBSD_TOOL.uniq'] == uniq_path and
            routed_utility['TOOLS_PLATFORM.uniq'] == uniq_path,
            'an admitted uniq tuple did not reach TOOLS_PLATFORM unchanged: '
            + repr({name: routed_utility[name] for name in (
                'EMBERBSD_NETBSD_NATIVE_TOOLS', 'EMBERBSD_NETBSD_TOOL.uniq',
                'TOOLS_PLATFORM.uniq')}))
    values = unpack(run_make(bmake, bootstrap_mk, export, source_tree, makeconf,
                             'lang/gcc16', work))
    actual_shell = shell_probe(bmake, bootstrap_mk, export, makeconf, work)
    require(values['_EMBERBSD_NETBSD_BOOTSTRAP_POLICY'] == '1',
            'the loaded MAKECONF did not set the NetBSD policy marker')
    # pkgsrc prepends generated wrappers from its owned recipe work tree.
    wrappers = [values['WRAPPER_BINDIR'],
                *[values[name] + '/bin' for name in ('BUILDLINK_DIR', 'TOOLS_DIR', '_GCC_DIR')]]
    require(all(Path(path).is_relative_to(work) for path in wrappers),
            'generated tool wrappers escape the isolated test work tree')
    allowed_path = {values['EMBERBSD_NETBSD_UTILITY_BIN'], values['LOCALBASE'] + '/bin', *wrappers}
    require(set(values['PATH'].split(os.pathsep)) <= allowed_path,
            'recipe PATH exposes executables outside the accepted utility directory '
            'and current source output: ' + values['PATH'])
    rebound = repeated_profile_probe(bmake, bootstrap_mk, export, makeconf, work)
    require(rebound['MAKE'] == rebound['_MAKE'] == rebound['LOCALBASE'] + '/bin/bmake' and
            rebound['SHELL'] == rebound['EMBERBSD_NETBSD_SH'] == rebound['LOCALBASE'] + '/bin/mksh' and
            rebound['TOOLS_PLATFORM.make'] == rebound['LOCALBASE'] + '/bin/bmake' and
            rebound['TOOLS_PLATFORM.gmake'].startswith(rebound['LOCALBASE'] + '/bin/gmake SHELL=') and
            rebound['TOOLS_PLATFORM.cc'] == rebound['EMBERBSD_GCC16_SEED_CC'] and
            rebound['TOOLS_PLATFORM.awk'] == rebound['EMBERBSD_NETBSD_TOOL.awk'] and
            rebound['NAWK_COMMAND_SHELL'] == rebound['LOCALBASE'] + '/bin/mksh' and
            rebound['TOOLS_PLATFORM.pkg-config'] == rebound['LOCALBASE'] + '/bin/pkg-config',
            'a repeated MAKECONF read failed to restore the source runtime/tool role bindings')
    require('MIRBSD' in actual_shell and 'KSH' in actual_shell,
            f'bmake recipe did not execute the selected mksh: {actual_shell!r}')
    require(values['MAKE'] == values['_MAKE'] == values['LOCALBASE'] + '/bin/bmake',
            f'source bmake route mismatch: {values["MAKE"]!r}, {values["_MAKE"]!r}, LOCALBASE={values["LOCALBASE"]!r}')
    seed = unpack(run_make(bmake, bootstrap_mk, export, source_tree, makeconf,
                           'devel/bmake', work))
    seed_shell = actual_shell
    require(seed['MAKE'] == seed['EMBERBSD_NETBSD_MAKE'],
            'the bmake foundation package did not retain the accepted make provider')
    require('MIRBSD' in seed_shell and 'KSH' in seed_shell,
            f'accepted mksh did not execute the seed recipe: {seed_shell!r}')
    require(values['TOOLS_PLATFORM.make'] == values['MAKE'] and
            values['TOOLS_PLATFORM.gmake'].startswith(values['EMBERBSD_NETBSD_GMAKE'] + ' ') and
            values['TOOLS_PLATFORM.cc'] == values['EMBERBSD_GCC16_SEED_CC'] and
            values['TOOLS_PLATFORM.ar'] == values['EMBERBSD_GCC16_AR'] and
            values['TOOLS_PLATFORM.awk'] == values['EMBERBSD_NETBSD_TOOL.awk'] and
            values['TOOLS_AWK'] == values['EMBERBSD_NETBSD_TOOL.awk'] and
            values['TOOLS_GREP'] == values['EMBERBSD_NETBSD_TOOL.grep'] and
            values['TOOLS_SED'] == values['LOCALBASE'] + '/bin/gsed' and
            values['TOOLS_CMDLINE_AWK'] == values['AWK'] and
            values['TOOLS_CMDLINE_GREP'] == values['GREP'] and
            values['TOOLS_CMDLINE_SED'] == values['SED'],
            'tool aliases changed: ' + repr({name: values[name] for name in (
                'TOOLS_AWK', 'TOOLS_GREP', 'TOOLS_SED', 'AWK', 'GREP', 'SED',
                'TOOLS_CMDLINE_AWK', 'TOOLS_CMDLINE_GREP', 'TOOLS_CMDLINE_SED',
                'EMBERBSD_NETBSD_TOOL.awk', 'EMBERBSD_NETBSD_TOOL.grep',
                'EMBERBSD_NETBSD_TOOL.sed')}))
    require({values[name] for name in ('SHELL', 'SH', 'CONFIG_SHELL', 'TOOLS_SHELL')} ==
            {values['LOCALBASE'] + '/bin/mksh'}, 'one or more recipe shell routes changed')
    require(values['_CC'] == words(values['EMBERBSD_GCC16_SEED_CC'])[0] and
            values['GCCBASE'] == words(values['EMBERBSD_GCC16_SEED_CC'])[0].rsplit('/bin/', 1)[0],
            'pkgsrc compiler discovery escaped the accepted GCC16 seed')
    for variable, wrapper in (('CC', 'cc'), ('CXX', 'cxx'), ('CPP', 'cpp')):
        selected = words(values['EMBERBSD_GCC16_SEED_' + variable])
        prepend = words(values['CWRAPPERS_PREPEND.' + wrapper])
        tail = selected[1:]
        occurrences = sum(prepend[index:index + len(tail)] == tail
                          for index in range(len(prepend) - len(tail) + 1)) if tail else 1
        require(values['PKG_' + variable] == selected[0] and
                selected[0] not in prepend and occurrences == 1,
                f'pkgsrc wrapper {variable}: exec={values["PKG_" + variable]!r}, '
                f'prepend={values["CWRAPPERS_PREPEND." + wrapper]!r}, expected={selected!r}')
    require(values['TOOLS_PLATFORM.as'] == values['EMBERBSD_GCC16_AS'] and
            values['TOOLS_PLATFORM.ld'] == values['EMBERBSD_GCC16_LD'] and
            values['TOOLS_PLATFORM.ar'] == values['EMBERBSD_GCC16_AR'] and
            values['TOOLS_PLATFORM.ranlib'] == values['EMBERBSD_GCC16_RANLIB'] and
            values['TOOLS_PLATFORM.nm'] == values['EMBERBSD_GCC16_NM'] and
            values['TOOLS_PLATFORM.strip'] == values['EMBERBSD_GCC16_STRIP'],
            'the selected assembler/linker/archive tool tuple changed')
    require(values['MAKE_JOBS'] == '1', 'the initial policy must be serial')
    args = words(values['CONFIGURE_ARGS'])
    require(args.count('--with-as=' + values['LOCALBASE'] + '/bin/gas') == 1 and
            args.count('--with-ld=' + values['LOCALBASE'] + '/bin/gld') == 1,
            f'GCC does not select source-built binutils: {args!r}')
    require('--disable-bootstrap' not in args,
            'the scoped GCC build disabled stage2/stage3 comparison')
    require(values['USE_PKGSRC_GCC'] != 'yes' and
            values['USE_PKGSRC_GCC_RUNTIME'] != 'yes',
            'the GCC seed would pull its own pkgsrc package or runtime back into bootstrap')

    root_edges = edges(values)
    require(FOUNDATION <= root_edges,
            f'GCC bootstrap lacks required source foundation edges: {FOUNDATION-root_edges}')
    policy_graph = {'lang/gcc16': values}
    package_names = {'lang/gcc16': values['PKGNAME']}
    pending = sorted(root_edges)
    while pending:
        recipe = pending.pop(0)
        if recipe in policy_graph:
            continue
        child = unpack(run_make(bmake, bootstrap_mk, export, source_tree, makeconf,
                                recipe, work))
        require(child['USE_PKGSRC_GCC'] != 'yes' and
                child['USE_PKGSRC_GCC_RUNTIME'] != 'yes',
                f'{recipe} unexpectedly acquires a pkgsrc GCC or scoped seed runtime')
        child_edges = edges(child)
        policy_graph[recipe] = child
        package_names[recipe] = child['PKGNAME']
        pending.extend(sorted(child_edges - policy_graph.keys()))
    nawk = policy_graph['lang/nawk']
    require(nawk['NAWK_COMMAND_SHELL'] == nawk['LOCALBASE'] + '/bin/mksh' and
            'mksh>=59b:../../shells/mksh' in words(nawk['DEPENDS']) and
            'mksh>=59b:../../shells/mksh' in words(nawk['BOOTSTRAP_DEPENDS']) and
            any('-DNAWK_COMMAND_SHELL="' + nawk['NAWK_COMMAND_SHELL'] + '"' in field
                for field in words(nawk['MAKE_FLAGS'])),
            'the nawk recipe lost its source-built runtime shell or dependency')
    visiting, visited = [], set()

    def visit(name):
        if name in visiting:
            start = visiting.index(name)
            cycle = visiting[start:] + [name]
            edges_on_cycle = ', '.join(
                f'{source} -> {target}'
                for source, target in zip(cycle, cycle[1:]))
            raise AssertionError('bootstrap policy dependency cycle: '
                                 + ' -> '.join(cycle) + ' (' + edges_on_cycle + ')')
        if name in visited:
            return
        visiting.append(name)
        for dep in edges(policy_graph.get(name, {})):
            if dep in policy_graph:
                visit(dep)
        visiting.pop()
        visited.add(name)

    visit('lang/gcc16')
    require(all('lang/gcc16-libs' not in edges(deps) for deps in policy_graph.values()),
            'the first-native source graph must not acquire gcc16-libs from its seed compiler')
    check_dependency_patterns(policy_graph, package_names, pkg_admin, pkg_admin_sha256)

    # zstd adds pkg-config to USE_TOOLS after its early bsd.prefs.mk read.
    # The source-provider edge and route must be selected from the completed
    # real package tool list, not from an earlier MAKECONF evaluation.
    zstd = unpack(run_make(bmake, bootstrap_mk, export, source_tree, makeconf,
                           'archivers/zstd', work))
    zstd_edges = edges(zstd)
    require('devel/pkgconf' in zstd_edges,
            'late pkg-config USE_TOOLS declaration lacks its shared source provider edge: '
            + repr(zstd_edges))
    require('pkg-config' in words(zstd['EMBERBSD_NETBSD_SOURCE_TOOLS']) and
            zstd['EMBERBSD_NETBSD_TOOL.pkg-config'] == zstd['LOCALBASE'] + '/bin/pkg-config' and
            zstd['TOOLS_PLATFORM.pkg-config'] == zstd['LOCALBASE'] + '/bin/pkg-config',
            'late pkg-config USE_TOOLS declaration did not select the source-built tool route')

    bash = unpack(run_make(bmake, bootstrap_mk, export, source_tree, makeconf,
                           'shells/bash', work))
    require('devel/bison' in edges(bash) and
            bash['TOOLS_PLATFORM.bison-yacc'] == bash['LOCALBASE'] + '/bin/bison -y',
            'bison-yacc must select the shared bison source provider in yacc mode')

    mksh = unpack(run_make(bmake, bootstrap_mk, export, source_tree, makeconf,
                           'shells/mksh', work))
    require('perl>=5.44.0:../../lang/perl5' in words(mksh['TEST_DEPENDS']) and
            'lang/perl5' not in edges(mksh),
            'perl:test must remain a test edge so the mksh/perl runtime graph is acyclic')
    # Match test-only provider names without adding them to the build graph.
    for _, provider in edge_specs(mksh, include_tests=True):
        if provider not in package_names:
            test_provider = unpack(run_make(
                bmake, bootstrap_mk, export, source_tree, makeconf, provider, work))
            package_names[provider] = test_provider['PKGNAME']
    check_dependency_patterns({'shells/mksh': mksh}, package_names, pkg_admin,
                              pkg_admin_sha256, include_tests=True)

    with tempfile.TemporaryDirectory(prefix='netbsd-profile-ordinary-') as temp_name:
        ordinary_conf = Path(temp_name) / 'ordinary.mk.conf'
        # -r removes sys.mk defaults. Supply the measured compiler identity
        # explicitly when this host has no base compiler. Keep policy disabled.
        ordinary_conf.write_text(
            '# no opt-in bootstrap profile\n'
            '.if ${.MAKE.LEVEL:U0} > 8\n'
            '.error "ordinary metadata compiler discovery recursed"\n'
            '.endif\n'
            + ''.join(name + '= ' + values['EMBERBSD_GCC16_SEED_' + name] + '\n'
                      for name in ('CC', 'CXX', 'CPP')))
        builtin_helper_probe(bmake, bootstrap_mk, export, makeconf, work)
        ordinary_mkfiles = unpack(run_make(
            bmake, bootstrap_mk, export, source_tree, ordinary_conf,
            'pkgtools/bootstrap-mk-files', work, enabled=False))
        require(ordinary_mkfiles['PLIST.builtin'] != 'yes' and
                'libexec' not in words(ordinary_mkfiles['INSTALLATION_DIRS']),
                'ordinary NetBSD unexpectedly installs the bootstrap builtin helper')
        ordinary = unpack(run_make(bmake, bootstrap_mk, export, source_tree, ordinary_conf,
            'devel/bmake', work, enabled=False))
        require(ordinary['SHELL'] != values['EMBERBSD_NETBSD_SH'],
                'ordinary pkgsrc unexpectedly selected the bootstrap shell')
        ordinary_nawk = unpack(run_make(bmake, bootstrap_mk, export, source_tree, ordinary_conf,
            'lang/nawk', work, enabled=False))
        require(not ordinary_nawk['NAWK_COMMAND_SHELL'],
                'ordinary nawk unexpectedly selected a bootstrap command shell')
        ordinary_gcc = unpack(run_make(bmake, bootstrap_mk, export, source_tree, ordinary_conf,
            'lang/gcc16', work, enabled=False))
    ordinary_args = words(ordinary_gcc['CONFIGURE_ARGS'])
    require('--disable-bootstrap' in ordinary_args and
            '--with-as=' + values['LOCALBASE'] + '/bin/gas' not in ordinary_args and
            '--with-ld=' + values['LOCALBASE'] + '/bin/gld' not in ordinary_args,
            'ordinary NetBSD GCC behavior changed without opt-in profile')

    for mutation, override in (
            ('wrong host', 'EMBERBSD_NETBSD_HOST_CPU=arm64'),
            ('cross mode', 'USE_CROSS_COMPILE=yes'),
            ('missing selected utility', 'EMBERBSD_NETBSD_TOOL.awk=')):
        refused = run_make(bmake, bootstrap_mk, export, source_tree, makeconf,
                           'lang/gcc16', work, overrides=(override,))
        require(refused.returncode != 0, f'profile accepted {mutation}')
    with tempfile.TemporaryDirectory(prefix='netbsd-profile-marker-', dir=work) as temp_name:
        missing_marker = Path(temp_name) / 'missing-policy.mk.conf'
        missing_marker.write_text('# deliberately omits the source profile\n')
        refused = run_make(bmake, bootstrap_mk, export, source_tree, missing_marker,
                           'lang/gcc16', work, synthetic=True)
        require(refused.returncode != 0, 'MAKECONF without the source marker was accepted')
    return {'profile': str(profile), 'recipes': len(policy_graph),
            'foundation': sorted(FOUNDATION), 'shell': values['EMBERBSD_NETBSD_SH'],
            'compiler_configure_args': args}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', required=True, type=Path)
    parser.add_argument('--source-tree', required=True, type=Path)
    parser.add_argument('--bmake', required=True, type=Path)
    parser.add_argument('--makeconf', required=True, type=Path)
    parser.add_argument('--bootstrap-mk', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--pkg-admin', required=True, type=Path)
    parser.add_argument('--pkg-admin-sha256', required=True)
    args = parser.parse_args()
    require(args.work.is_dir() and args.work.is_absolute(),
            'the caller must create the isolated absolute test work root')
    result = check(args.export, args.source_tree, args.bmake, args.makeconf,
                   args.bootstrap_mk, args.work, args.pkg_admin,
                   args.pkg_admin_sha256)
    print('PASS: NetBSD bootstrap profile metadata and source-policy checks')
    print(f"Evaluated {result['recipes']} recipes; recipe shell: {result['shell']}")


if __name__ == '__main__':
    main()
