#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), explicit Darwin SDK and libffi selection.
"""Check actual configure selection and recipe metadata without a package build."""
import argparse
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'recipe', 'pkgsrc', 'makeconf', 'bmake', 'shell',
                 'pkg-config', 'pkg-admin', 'ffi-prefix', 'sandbox-profile', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--sdk-only', action='store_true', help='Run only native Darwin SDK metadata controls')
    args = cli.parse_args()
    args.work.mkdir()
    for name in ('home', 'tmp'):
        (args.work / name).mkdir()
    env = dict(os.environ, HOME=str(args.work / 'home'), TMPDIR=str(args.work / 'tmp'),
               LC_ALL='C', PKG_CONFIG=str(args.pkg_config))
    results = {}
    returncodes = {}
    failures = []

    def run(name, command, extra=None, codes=(0,)):
        process = subprocess.run(['/usr/bin/sandbox-exec', '-f', str(args.sandbox_profile),
                                  *map(str, command)], env=dict(env, **(extra or {})),
                                 cwd=args.work, capture_output=True, timeout=60)
        (args.work / (name + '.out')).write_bytes(process.stdout)
        (args.work / (name + '.err')).write_bytes(process.stderr)
        returncodes[name] = process.returncode
        require(process.returncode in codes, 'command failed: ' + name)
        return process.stdout.decode()

    # Evaluate the exact Darwin owner block with BSD make. This isolates an
    # absent selector from pkgsrc's earlier platform auto-discovery.
    recipe_text = (args.recipe / 'Makefile').read_text()
    lines = recipe_text.splitlines(True)
    start = lines.index('.if ${OPSYS} == "Darwin"\n',
                        next(i for i, line in enumerate(lines) if 'retain the selected Darwin ABI' in line))
    depth = 0
    selected = []
    for line in lines[start:]:
        selected.append(line)
        if re.match(r'\.\s*if\b', line):
            depth += 1
        elif re.match(r'\.\s*endif\b', line):
            depth -= 1
        if depth == 0:
            break
    owner = args.work / 'darwin-owner.mk'
    owner.write_text(''.join(selected))
    regular_file = args.work / 'not-a-directory'
    regular_file.touch()
    # Query the supplied configuration for the valid SDK, rather than choose
    # a host default. This is metadata only and has no package target.
    actual = run('selected-sdk', [args.bmake, '-C', args.pkgsrc / 'lang/python315',
        'MAKECONF=' + str(args.makeconf), '-V', '${OSX_SDK_PATH}']).strip()
    require(actual.startswith('/') and Path(actual).is_dir(), 'The positive control needs a selected SDK')
    for label, system, cross, sdk, rejected in (
        ('sdk-valid', 'Darwin', 'no', actual, False),
        ('sdk-missing', 'Darwin', 'no', None, True),
        ('sdk-empty', 'Darwin', 'no', '', True),
        ('sdk-relative', 'Darwin', 'no', 'relative-sdk', True),
        ('sdk-absent', 'Darwin', 'no', str(args.work / 'absent-sdk'), True),
        ('sdk-file', 'Darwin', 'no', str(regular_file), True),
        ('sdk-cross', 'Darwin', 'yes', None, False),
        ('sdk-linux', 'Linux', 'no', None, False),
        ('sdk-netbsd', 'NetBSD', 'no', None, False)):
        fixture = args.work / (label + '.mk')
        fixture.write_text('OPSYS=' + system + '\nUSE_CROSS_COMPILE=' + cross + '\n'
            + (('OSX_SDK_PATH=' + sdk + '\n') if sdk is not None else '')
            + '.include "' + str(owner) + '"\n')
        output = run(label, [args.bmake, '-r', '-f', fixture, '-V', '${PKG_FAIL_REASON}'])
        failed = 'Python315 native Darwin requires OSX_SDK_PATH' in output
        valid = failed == rejected
        results[label] = dict(rejected=failed, expected=rejected, valid=valid)
        if not valid:
            failures.append(label + ': native Darwin SDK failure scope changed')
    if args.sdk_only:
        (args.work / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        for failure in failures:
            print('FAIL: ' + failure)
        require(not failures, 'native Darwin SDK selector regression')
        print('PASS: selected SDK; missing, empty, relative, absent and file rejection; cross/Linux/NetBSD unchanged')
        return

    # Use the real generated configure block. Cached header/link answers make
    # both providers available; no compiler result or runtime is accepted here.
    source = (args.source / 'configure').read_text()
    maintained = (args.source / 'configure.ac').read_text()
    ac_guard = re.search(r'have_libffi=missing\nAS_IF\(\[(.*?)\], \[', maintained)
    sh_guard = re.search(r'have_libffi=missing\nif (.*?)\n', source)
    paired = ac_guard is not None and sh_guard is not None and ac_guard[1] == sh_guard[1]
    results['paired-guard'] = paired
    if not paired:
        failures.append('maintained/generated explicit-selector guards differ or are absent')
    start = source.index('have_libffi=missing\n')
    end = source.index('if test "x$have_libffi" = xyes', start)
    fragment = source[start:end]
    probe = args.work / 'ffi-selection.sh'
    probe.write_text('exec 5>configure-selection.log 6>/dev/null\n'
        'ac_fn_c_check_header_compile() { ac_cv_header_ffi_h=yes; }\n'
        'ac_cv_lib_ffi_ffi_call=yes\nCFLAGS=\nCPPFLAGS=\nLDFLAGS=\nLIBS=\n'
        + fragment + '\nprintf "%s\\n" "$have_libffi" "$LIBFFI_CFLAGS" "$LIBFFI_LIBS"\n')
    selected_cflags = '-I/selected/ports/include'
    selected_libs = '-L/selected/ports/lib -Wl,-rpath,/selected/ports/lib -lffi'
    for system, explicit in (('Darwin', True), ('Darwin', False), ('Linux', True)):
        label = system.lower() + ('-explicit' if explicit else '-default')
        output = run(label, [args.shell, probe], dict(ac_sys_system=system,
            SDKROOT='/selected/host-abi', LIBFFI_CFLAGS=selected_cflags if explicit else '',
            LIBFFI_LIBS=selected_libs if explicit else ''))
        rows = output.splitlines()
        require(len(rows) == 3, 'invalid configure selection output')
        if explicit:
            valid = rows == ['yes', selected_cflags, selected_libs]
        else:
            valid = rows == ['yes', '-I/selected/host-abi/usr/include/ffi -DUSING_APPLE_OS_LIBFFI=1', '-lffi']
        results[label] = dict(have_libffi=rows[0], cflags=rows[1], libs=rows[2], valid=valid)
        if not valid:
            failures.append(label + ': configure replaced explicit libffi selection')

    for flag in ('cflags', 'libs'):
        discovered = run('pkg-config-' + flag, [args.pkg_config, '--' + flag, 'libffi']).strip()
        cflags = selected_cflags if flag == 'libs' else ''
        libs = selected_libs if flag == 'cflags' else ''
        label = 'darwin-explicit-' + ('libs' if libs else 'cflags')
        rows = run(label, [args.shell, probe], dict(ac_sys_system='Darwin',
            SDKROOT='/selected/host-abi', LIBFFI_CFLAGS=cflags, LIBFFI_LIBS=libs)).splitlines()
        expected = ['yes', cflags or discovered, libs or discovered]
        valid = rows == expected
        results[label] = dict(output=rows, expected=expected, valid=valid)
        if not valid:
            failures.append(label + ': configure replaced a partial selector')

    # SDKROOT is the supported upstream selector. Its exact generated block
    # must skip xcrun when set and retain discovery when unset.
    start = source.index('  if test -z "$SDKROOT"; then')
    end = source.index('  { printf', start)
    sdk_probe = args.work / 'sdk-selection.sh'
    sdk_probe.write_text('HAS_XCRUN=yes\n'
        'xcrun() { printf called >xcrun-called; echo /automatic/apple-abi; }\n'
        + source[start:end] + '\nprintf "%s\\n" "$SDKROOT"\n')
    for sdk in ('/selected/host-abi', ''):
        called = args.work / 'xcrun-called'
        if called.exists():
            called.unlink()
        label = 'sdk-explicit' if sdk else 'sdk-default'
        output = run(label, [args.shell, sdk_probe], dict(SDKROOT=sdk)).strip()
        valid = output == (sdk or '/automatic/apple-abi') and called.exists() == (not bool(sdk))
        results[label] = dict(output=output, xcrun=called.exists(), valid=valid)
        if not valid:
            failures.append(label + ': SDKROOT selection changed')

    # Read full pkgsrc metadata through its normal include chain. All objects
    # point to this new check tree. The installed package prefix stays read-only.
    tree = args.work / 'pkgsrc'
    tree.mkdir()
    for entry in args.pkgsrc.iterdir():
        if entry.name != 'lang':
            (tree / entry.name).symlink_to(entry)
            continue
        (tree / 'lang').mkdir()
        for package in entry.iterdir():
            if package.name == 'python315':
                shutil.copytree(args.recipe, tree / 'lang/python315')
            else:
                (tree / 'lang' / package.name).symlink_to(package)
    output = run('recipe', [args.bmake, '-C', tree / 'lang/python315',
        'MAKECONF=' + str(args.makeconf), 'WRKOBJDIR=' + str(args.work / 'objects'),
        'BUILDLINK_PREFIX.libffi=' + str(args.ffi_prefix),
        '-V', '${CONFIGURE_ENV}', '-V', '${OSX_SDK_PATH}',
        '-V', '${BUILDLINK_PREFIX.libffi}', '-V', '${_CROSS_DESTDIR:U}'])
    rows = output.splitlines()
    require(len(rows) == 4, 'invalid recipe metadata output')
    values = dict(item.split('=', 1) for item in shlex.split(rows[0]) if '=' in item)
    expected_prefix = rows[3] + rows[2]
    checks = dict(sdk=values.get('SDKROOT') == rows[1],
        cflags=values.get('LIBFFI_CFLAGS') == '-I' + expected_prefix + '/include',
        libs=values.get('LIBFFI_LIBS') == '-L' + expected_prefix + '/lib -lffi')
    results['recipe'] = dict(sdk=rows[1], prefix=expected_prefix,
        selected={k: values.get(k) for k in ('SDKROOT', 'LIBFFI_CFLAGS', 'LIBFFI_LIBS')}, checks=checks)
    failures.extend('recipe: missing selected ' + key for key, ok in checks.items() if not ok)
    # Tool-only Python dependencies use pyversion.mk rather than buildlink3.
    # Evaluate that actual owner and use pkgsrc's matcher, without a pkgdb query.
    for custom in (False, True):
        label = 'floor-custom' if custom else 'floor-default'
        fixture = args.work / (label + '.mk')
        fixture.write_text('PKGNAME= ffi-selector-regression-1.0\nPYTHON_VERSION_REQD=315\n'
            + ('BUILDLINK_API_DEPENDS.python315=python315>=99\n' if custom else '')
            + '.include "' + str(tree / 'lang/python/pyversion.mk') + '"\n')
        output = run(label, [args.bmake, '-C', tree / 'lang/python315', '-r', '-f', fixture,
            'MAKECONF=' + str(args.makeconf), '-V', '${PYDEPENDENCY}'])
        patterns = [item.split(':', 1)[0] for item in output.split()]
        accepted = {}
        for version in ('3.15.1', '3.15.1nb1', '99'):
            matches = []
            for index, pattern in enumerate(patterns):
                name = label + '-' + version + '-' + str(index)
                run(name,
                    [args.pkg_admin, 'pmatch', pattern, 'python315-' + version], codes=(0, 1))
                matches.append(returncodes[name] == 0)
            accepted[version] = bool(patterns) and all(matches)
        expected = {'3.15.1': False, '3.15.1nb1': not custom, '99': True}
        valid = accepted == expected
        results[label] = dict(patterns=patterns, accepted=accepted, valid=valid)
        if not valid:
            failures.append(label + ': old provider or stronger caller constraint changed')

    (args.work / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    for failure in failures:
        print('FAIL: ' + failure)
    require(not failures, 'Darwin SDK/libffi source or metadata regression')
    print('PASS: explicit Darwin and Linux libffi selectors; default Darwin SDK behavior')
    print('PASS: paired configure guard, actual pkgsrc SDKROOT/libffi flags and additive nb1 floor')
    print('No compilation, prefix mutation or runtime acceptance')


if __name__ == '__main__':
    main()
