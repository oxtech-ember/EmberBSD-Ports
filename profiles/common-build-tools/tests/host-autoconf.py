#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc native Autoconf selection.
"""Check real native/cross Autoconf tools, Libtoolize roles and refusal controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'native_makeconf', 'cross_makeconf', 'host_autoconf', 'new_work'):
        cli.add_argument(name, type=Path)
    cli.add_argument('--unpatched-autoconf', type=Path,
                     help='Original mk/tools/autoconf.mk when the input export already carries our patch.')
    args = cli.parse_args()
    require(sys.version_info >= (3, 15), 'Use the selected native Python 3.15 or newer.')
    pkgsrc, native, cross, autoconf = (p.resolve(strict=True) for p in
        (args.pkgsrc, args.native_makeconf, args.cross_makeconf, args.host_autoconf))
    work = args.new_work
    require(all(re.fullmatch(r'/[A-Za-z0-9_./-]+', str(p)) for p in
                (pkgsrc, native, cross, autoconf, work)), 'Use absolute portable paths.')
    require(work.resolve() == work and not work.exists() and not work.is_symlink(),
            'Use a new absolute canonical work directory.')
    require(not any(work.is_relative_to(p) for p in (pkgsrc, autoconf.parent)),
            'Keep work outside selected source and tool inputs.')
    original = args.unpatched_autoconf.resolve(strict=True) if args.unpatched_autoconf else None
    work.mkdir(mode=0o700)
    (work / 'tmp').mkdir()
    tools = ['autoconf', 'autoheader', 'autom4te', 'autoreconf', 'autoscan', 'autoupdate', 'ifnames']
    patch = Path(__file__).resolve().parents[1] / 'patches/pkgsrc-host-autoconf.patch'
    bmake = os.environ.get('BMAKE', 'bmake')
    commands, results = [], {}
    environment = dict(os.environ, LC_ALL='C', TMPDIR=str(work / 'tmp'),
                       TMP=str(work / 'tmp'), TEMP=str(work / 'tmp'))

    def run(label, argv, cwd=None, env=environment, expected=0):
        command = list(map(str, argv))
        process = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=120)
        (work / (label + '.out')).write_bytes(process.stdout)
        (work / (label + '.err')).write_bytes(process.stderr)
        commands.append(dict(name=label, argv=command, cwd=str(cwd) if cwd else None,
                             status=process.returncode, expected=expected))
        (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        require(process.returncode == expected, f'{label}: expected {expected}, got {process.returncode}')
        return process.stdout

    for variant in ('old', 'new', 'weak-guard'):
        tree = work / variant
        (tree / 'devel').mkdir(parents=True)
        for source in pkgsrc.iterdir():
            if source.name not in ('mk', 'devel'):
                (tree / source.name).symlink_to(source)
        shutil.copytree(pkgsrc / 'mk', tree / 'mk', symlinks=True)
        if original:
            shutil.copyfile(original, tree / 'mk/tools/autoconf.mk')
            helper = tree / 'mk/tools/ember-autoconf.mk'
            if helper.exists():
                helper.unlink()
        for source in (pkgsrc / 'devel').iterdir():
            if source.name == 'm4':
                shutil.copytree(source, tree / 'devel/m4', symlinks=True)
                recipe = tree / 'devel/m4/Makefile'
                recipe.write_text('USE_TOOLS+= ${EMBER_TEST_TOOLS}\n'
                    '.if ${EMBER_TEST_LIBTOOL:Uno} == "yes"\nUSE_LIBTOOL=yes\n.endif\n'
                    'TOOL_DEPENDS+= ${EMBER_TEST_NATIVE_LIBTOOL}\n' + recipe.read_text())
            else:
                (tree / 'devel' / source.name).symlink_to(source)
        if variant != 'old':
            run('patch-' + variant, ['patch', '-f', '-N', '-F', '0', '-p1', '-d', tree, '-i', patch])
            if variant == 'weak-guard':
                # A prefix-only guard dropped the required floor when any native provider existed.
                rules = tree / 'mk/tools/autoconf.mk'
                correct = 'empty(TOOL_DEPENDS:M${_TOOLS_AUTORECONF_LIBTOOL_DEPEND})'
                contents = rules.read_text()
                require(contents.count(correct) == 1, 'Missing exact predicate guard for fault control.')
                rules.write_text(contents.replace(correct, 'empty(TOOL_DEPENDS:Mlibtool-base*)'))

    configs = {}
    for mode, source in [('native', native), ('cross', cross)]:
        config = work / (mode + '.mk.conf')
        config.write_text(f'.include "{source}"\n.undef EMBERBSD_BUILD_AUTOCONF\n'
            '.undef TOOLS_DEPENDS.autoconf\n' + ''.join(
            f'.undef TOOLS_PATH.{tool}\n.undef TOOLS_PLATFORM.{tool}\n' for tool in tools))
        configs[mode] = config
    variables = ['PKG_FAIL_REASON', 'TOOL_DEPENDS', 'DEPENDS', 'TEST_DEPENDS'] + [f'TOOLS_PATH.{t}' for t in tools]

    def metadata(label, variant, mode, use, options=()):
        argv = [bmake, '-C', work / variant / 'devel/m4', f'MAKECONF={configs[mode]}',
                f'WRKDIR={work}/objects-{mode}', f'WRKOBJDIR={work}/objects-{mode}',
                f'PACKAGES={work}/packages', 'EMBER_TEST_TOOLS=' + use, *options]
        output = run(label, argv + [v for key in variables for v in ['-v', key]])
        values = output.decode().splitlines()
        require(len(values) == len(variables), 'Unexpected metadata shape: ' + label)
        results[label] = dict(zip(variables, values))
        return results[label], argv

    role_names = ['TOOLS_CMD.' + t for t in [*tools, 'automake', 'aclocal', 'gm4', 'libtoolize']]
    role_names += ['TOOLS_PATH.libtoolize', 'PKG_LIBTOOL', 'PKG_SHLIBTOOL', 'LIBTOOL_REQD',
                   'CC', 'CFLAGS', 'CXX', 'CXXFLAGS']
    roles = {}

    def role_metadata(label, variant, mode, use, enabled, options=()):
        output = work / ('libtool-' + variant + '-' + mode + '-' + label)
        value, make = metadata(label + '-' + variant + '-' + mode, variant, mode, use,
            ['EMBER_TEST_LIBTOOL=' + ('yes' if enabled else 'no'),
             'WRKDIR=' + str(output), 'WRKOBJDIR=' + str(output), *options])
        extra = run(label + '-paths-' + variant + '-' + mode,
                    make + [v for key in role_names for v in ['-v', key]]).decode().splitlines()
        require(len(extra) == len(role_names), 'Unexpected role metadata shape.')
        return dict(value, **dict(zip(role_names, extra))), make, output

    def fixture(path):
        path.mkdir()
        (path / 'm4').mkdir()
        (path / 'configure.ac').write_text('AC_INIT([ember-libtool-role], [1.0])\n'
            'AC_CONFIG_AUX_DIR([build-aux])\nAC_CONFIG_MACRO_DIRS([m4])\n'
            'AM_INIT_AUTOMAKE([foreign])\nAC_PROG_CC\nLT_INIT\n'
            'AC_CONFIG_FILES([Makefile])\nAC_OUTPUT\n')
        (path / 'Makefile.am').write_text('lib_LTLIBRARIES = libember.la\nlibember_la_SOURCES = library.c\n')
        (path / 'library.c').write_text('int ember_value(void) { return 42; }\n')

    for mode in ('native', 'cross'):
        selected = {}
        for variant in ('old', 'new'):
            row, make, output = role_metadata('regenerate', variant, mode, 'autoreconf automake', True)
            selected[variant] = row
            paths = [row['TOOLS_CMD.' + tool] for tool in [*tools, 'automake', 'aclocal', 'gm4']]
            if variant == 'new':
                helper = Path(row['TOOLS_CMD.libtoolize'])
                prefix = Path(row['TOOLS_PATH.libtoolize']).parents[1]
                require(helper == output / '.tools/bin/libtoolize', 'Wrong private Libtoolize output.')
                require(row['TOOLS_PATH.libtoolize'] == str(prefix / 'bin/libtoolize'), 'Wrong native Libtoolize path.')
                require(any(dep.startswith('libtool-base>=') and dep.endswith(':../../devel/libtool-base')
                            for dep in row['TOOL_DEPENDS'].split()), 'Missing native Libtoolize provider.')
                paths.append(str(helper))
            else:
                require(not row['TOOLS_PATH.libtoolize'], 'Baseline already selects Libtoolize.')
            paths = list(dict.fromkeys(path for path in paths if path))
            require(all(Path(path).is_relative_to(output) for path in paths), 'Non-private role tool output.')
            run('role-wrappers-' + variant + '-' + mode, make + ['_PKGSRC_BARRIER=yes', *paths])
            env = dict(environment, PATH=str(output / '.tools/bin') + ':/usr/bin:/bin:/usr/sbin:/sbin')
            for name in ['LIBTOOLIZE', 'AUTOCONF', 'AUTOHEADER', 'AUTOMAKE', 'ACLOCAL', 'M4', 'ACLOCAL_PATH']:
                env.pop(name, None)
            source = work / ('libtool-source-' + variant + '-' + mode)
            fixture(source)
            expected = 1 if variant == 'old' else 0
            run('bare-autoreconf-' + variant + '-' + mode, ['autoreconf', '-fi'], source, env, expected)
            if variant == 'old':
                diagnostic = (work / ('bare-autoreconf-old-' + mode + '.err')).read_text()
                require('libtoolize' in diagnostic and 'failed to run' in diagnostic,
                        'Baseline failed before the missing Libtoolize cause.')
            else:
                require(all((source / name).is_file() for name in
                    ['configure', 'Makefile.in', 'build-aux/ltmain.sh', 'm4/libtool.m4']),
                    'Actual source regeneration is incomplete.')
                require((source / 'm4/libtool.m4').read_bytes() ==
                        (prefix / 'share/aclocal/libtool.m4').read_bytes(), 'Wrong native Libtool macros.')
                fault = work / ('missing-wrapper-' + mode)
                shutil.copytree(output / '.tools/bin', fault, symlinks=True)
                (fault / 'libtoolize').unlink()
                source = work / ('libtool-source-fault-' + mode)
                fixture(source)
                env['PATH'] = str(fault) + ':/usr/bin:/bin:/usr/sbin:/sbin'
                run('bare-autoreconf-missing-wrapper-' + mode, ['autoreconf', '-fi'], source, env, 1)
                require('libtoolize' in (work / ('bare-autoreconf-missing-wrapper-' + mode + '.err')).read_text(),
                        'Missing-wrapper control does not detect Libtoolize.')
        for key in ['DEPENDS', 'TEST_DEPENDS', 'PKG_LIBTOOL', 'PKG_SHLIBTOOL', 'LIBTOOL_REQD',
                    'CC', 'CFLAGS', 'CXX', 'CXXFLAGS']:
            normalize = lambda value, variant: value.replace(str(work / variant), '%TREE%').replace(
                str(work / ('libtool-' + variant + '-' + mode + '-regenerate')), '%WORK%')
            require(normalize(selected['old'][key], 'old') == normalize(selected['new'][key], 'new'),
                    'Target compiler/Libtool or runtime roles changed: ' + mode + '/' + key)
        if mode == 'native':
            require(selected['old']['TOOL_DEPENDS'] == selected['new']['TOOL_DEPENDS'],
                    'A native Libtool provider was added twice.')
        else:
            require('cross-libtool-base-' in selected['new']['TOOL_DEPENDS'], 'Target Libtool provider disappeared.')
        roles[mode] = selected
        for label, use, enabled in [('no-autoreconf', 'autoconf automake', True),
                ('no-libtool', 'autoreconf automake', False),
                ('legacy213', 'autoreconf autoconf213 automake', True),
                ('legacy269', 'autoreconf autoconf269 automake', True),
                ('runtime', 'autoreconf:run automake', True),
                ('test', 'autoreconf:test automake', True)]:
            before, _, output_old = role_metadata(label, 'old', mode, use, enabled)
            after, _, output_new = role_metadata(label, 'new', mode, use, enabled)
            normalize = lambda row, variant, output: {k: v.replace(str(work / variant), '%TREE%').replace(
                str(output), '%WORK%') for k, v in row.items()}
            require(normalize(before, 'old', output_old) == normalize(after, 'new', output_new),
                    'Changed excluded Libtoolize role: ' + mode + '/' + label)

    predicate_controls = {}
    for floor in ('2.4.2nb9', '99.0'):
        required = 'libtool-base>=' + floor + ':../../devel/libtool-base'
        for label, version in [('weak', '1.0'), ('strong', '100.0'), ('exact', floor)]:
            supplied = 'libtool-base>=' + version + ':../../devel/libtool-base'
            control = floor + '-' + label
            options = ['EMBER_TEST_NATIVE_LIBTOOL=' + supplied, 'LIBTOOL_REQD=' + floor]
            rows = {}
            for variant in ('weak-guard', 'new'):
                row, _, _ = role_metadata('predicate-' + control, variant, 'cross',
                                          'autoreconf automake', True, options)
                dependencies = row['TOOL_DEPENDS'].split()
                require(dependencies.count(supplied) == 1, 'Existing native predicate changed: ' + control)
                require('cross-libtool-base-' in row['TOOL_DEPENDS'], 'Cross Libtool provider was removed.')
                if variant == 'new':
                    require(dependencies.count(required) == 1, 'Required native Libtool floor was dropped: ' + control)
                    require(row['LIBTOOL_REQD'] == floor, 'Custom Libtool floor changed: ' + control)
                else:
                    require((required in dependencies) == (supplied == required),
                            'Faulty prefix guard no longer reproduces lost native floor: ' + control)
                rows[variant] = row
            predicate_controls[control] = rows

    external = ['EMBERBSD_BUILD_AUTOCONF=' + str(autoconf)]
    for mode in ('native', 'cross'):
        old, _ = metadata(mode + '-ignored-before', 'old', mode, 'autoconf', external)
        fixed, make = metadata(mode + '-selected', 'new', mode, 'autoconf', external)
        require(':../../devel/autoconf' in old['TOOL_DEPENDS'], 'Baseline did not expose the redundant dependency.')
        require(not fixed['PKG_FAIL_REASON'], 'Selected provider has an error.')
        require(not any(':../../devel/autoconf' in fixed[key] for key in ['TOOL_DEPENDS', 'DEPENDS', 'TEST_DEPENDS']),
                'Selected provider still requests an Autoconf package.')
        for tool in tools:
            expected = autoconf if tool == 'autoconf' else autoconf.parent / tool
            require(fixed['TOOLS_PATH.' + tool] == str(expected), 'Wrong tool selection: ' + tool)
        for use in ['autoconf', 'autoconf:run', 'autoconf:test', 'autoconf213', 'autoconf269']:
            options = [] if use == 'autoconf' else external
            before, _ = metadata(mode + '-' + use.replace(':', '-') + '-before', 'old', mode, use, options)
            after, _ = metadata(mode + '-' + use.replace(':', '-') + '-after', 'new', mode, use, options)
            normalize = lambda row, variant: {k: v.replace(str(work / variant) + '/', '%PKGSRC%/') for k, v in row.items()}
            require(normalize(before, 'old') == normalize(after, 'new'), 'Changed default/legacy/runtime/test routing: ' + mode + '/' + use)
        names = ['WRKDIR', 'TOOLS_DIR', 'WRKLOG'] + ['TOOLS_CMD.' + t for t in tools]
        values = run(mode + '-paths', make + [v for key in names for v in ['-v', key]]).decode().splitlines()
        require(len(values) == len(names), 'Unexpected path metadata.')
        for value in values:
            path = Path(value)
            require(path.is_relative_to(work / ('objects-' + mode)), 'Non-private tool output: ' + value)
            require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink output ancestor: ' + value)
        wrappers = values[3:]
        run(mode + '-wrappers', make + ['_PKGSRC_BARRIER=yes', 'TOOLS_ALWAYS_WRAP=yes', *wrappers])
        for path in wrappers:
            run(mode + '-' + Path(path).name + '-version', [path, '--version'])
        source = work / ('source-' + mode)
        source.mkdir()
        (source / 'configure.ac').write_text('AC_INIT([ember-host-autoconf], [1.0])\nAC_CONFIG_HEADERS([config.h])\n'
            'AC_DEFINE([EMBER_GENERATOR_VALUE], [42], [Generator contract value.])\nAC_OUTPUT\n')
        run(mode + '-autoconf', [wrappers[0]], source)
        run(mode + '-autoheader', [wrappers[1]], source)
        run(mode + '-configure', ['sh', './configure'], source)
        require('#define EMBER_GENERATOR_VALUE 42' in (source / 'config.h').read_text(), 'Generated header is incorrect.')

    controls = {'relative': 'autoconf', 'missing': str(work / 'missing-autoconf')}
    for kind in ['old', 'broken', 'nonexecutable', 'wrong-banner']:
        path = work / (kind + '-autoconf')
        version = '2.72' if kind == 'old' else '2.73'
        banner = ('automake (GNU automake) ' if kind == 'wrong-banner' else 'autoconf (GNU Autoconf) ') + version
        path.write_text("#!/bin/sh\nprintf '%s\\n' '" + banner + "'\n" + ('exit 1\n' if kind == 'broken' else ''))
        if kind != 'nonexecutable':
            path.chmod(0o755)
        controls[kind] = str(path)
    for name, path in controls.items():
        value, _ = metadata('invalid-' + name, 'new', 'native', 'autoconf', ['EMBERBSD_BUILD_AUTOCONF=' + path])
        require('EMBERBSD_BUILD_AUTOCONF' in value['PKG_FAIL_REASON'], 'Accepted invalid provider: ' + name)
    value, _ = metadata('required-version', 'new', 'native', 'autoconf', external + ['AUTOCONF_REQD=2.50 99.0'])
    require('Autoconf >=99.0' in value['PKG_FAIL_REASON'], 'Ignored AUTOCONF_REQD.')
    for kind in ['missing', 'mismatch', 'failure']:
        directory = work / ('companion-' + kind)
        directory.mkdir()
        for tool in tools:
            if tool != 'autoheader':
                (directory / tool).symlink_to(autoconf.parent / tool)
        if kind != 'missing':
            header = directory / 'autoheader'
            header.write_text("#!/bin/sh\nprintf '%s\\n' 'autoheader (GNU Autoconf) " +
                ('2.72' if kind == 'mismatch' else '2.73') + "'\n" + ('exit 1\n' if kind == 'failure' else ''))
            header.chmod(0o755)
        value, _ = metadata('invalid-companion-' + kind, 'new', 'native', 'autoconf',
            ['EMBERBSD_BUILD_AUTOCONF=' + str(directory / 'autoconf')])
        require('matching executable autoheader' in value['PKG_FAIL_REASON'], 'Accepted invalid companion: ' + kind)

    inputs = [native, cross, autoconf, patch] + ([original] if original else [])
    (work / 'result.json').write_text(json.dumps(dict(
        scope='Real native/cross pkgsrc metadata and host tool wrappers; no package installation or target execution.',
        inputs={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}, results=results, libtool_roles=roles, libtool_predicates=predicate_controls), indent=2) + '\n')
    print('PASS: explicit native Autoconf, seven real tool wrappers, source regeneration, routing and refusal controls.')


if __name__ == '__main__':
    main()
