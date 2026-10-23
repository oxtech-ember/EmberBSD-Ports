#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Ported from librsvg-targets.rb.
"""Check real bmake selection and Rust metadata import without a VM or GI query."""

import argparse
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True

TARGETS = {
    'amd64': ('x86_64', 'x86_64--netbsd', 'x86_64-unknown-netbsd', 'rust-std-x86_64-netbsd'),
    'aarch64': ('aarch64', 'aarch64--netbsd', 'aarch64-unknown-netbsd', 'rust-std-aarch64-netbsd'),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_sdk(source):
    require(source and os.path.isabs(source),
            'set --sdk-source or EMBERBSD_SDK_SOURCE to an absolute SDK source')
    root = Path(source).resolve(strict=True)
    package = root / 'src/emberbsd_sdk'
    require((package / '__init__.py').is_file(), 'SDK source has no emberbsd_sdk API')
    sys.path.insert(0, str(root / 'src'))
    import emberbsd_sdk
    require(type(emberbsd_sdk.API_VERSION) is int and emberbsd_sdk.API_VERSION == 1
            and Path(emberbsd_sdk.__file__).resolve().parent == package.resolve(),
            'the selected SDK must provide API version 1')
    from emberbsd_sdk.errors import CommandError
    from emberbsd_sdk.jsonio import write_json
    from emberbsd_sdk.paths import canonical_existing, canonical_new
    from emberbsd_sdk.process import capture
    return SimpleNamespace(root=str(root), CommandError=CommandError,
                           write_json=write_json, canonical_existing=canonical_existing,
                           canonical_new=canonical_new, capture=capture)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', default=os.environ.get('EMBERBSD_SDK_SOURCE'))
    parser.add_argument('--profile', default=str(Path(__file__).resolve().parent.parent),
                        help='common-graphics profile with the production cross fragments')
    parser.add_argument('host_prefix', metavar='HOST_PREFIX')
    parser.add_argument('cross_tools', metavar='CROSS_TOOLS')
    parser.add_argument('new_work', metavar='NEW_WORK')
    options = parser.parse_args()
    require(sys.version_info[:2] == (3, 15), 'use the selected build-host Python 3.15')
    sdk = load_sdk(options.sdk_source)
    python = sdk.canonical_existing(sys.executable)
    host, tools, profile = (Path(sdk.canonical_existing(value)) for value in
                           (options.host_prefix, options.cross_tools, options.profile))
    require(os.path.isabs(options.new_work), 'new absolute work required')
    work = Path(sdk.canonical_new(options.new_work))
    require(not os.path.lexists(work), 'new absolute work required')
    work.mkdir(parents=True)
    recipe = work / 'pkgsrc/graphics/librsvg'
    gi = work / 'pkgsrc/devel/gobject-introspection'
    for directory in (recipe, gi, work / 'pkgsrc/mk', work / 'sysroot', work / 'wrappers'):
        directory.mkdir(parents=True)
    (work / 'pkgsrc/mk/bsd.prefs.mk').write_text('', encoding='utf-8')
    (recipe / 'Makefile').write_text('.include "cross.mk"\n', encoding='utf-8')
    shutil.copyfile(profile / '../../pkgsrc/graphics/librsvg/cross.mk', recipe / 'cross.mk')
    shutil.copyfile(profile / '../../pkgsrc/devel/gobject-introspection/cross.mk', gi / 'cross.mk')
    # Existence only. This regression never invokes the GI target launcher.
    sdk.write_json(str(work / 'query.json'), {})
    for name, driver in (('cc', 'gcc'), ('c++', 'g++')):
        (work / 'wrappers' / name).symlink_to(tools / ('bin/x86_64--netbsd-' + driver))
    base = [os.environ.get('BMAKE', 'bmake'), '-C', str(recipe), 'USE_CROSS_COMPILE=yes',
            'OPSYS=NetBSD', 'CROSS_OPSYS=NetBSD', 'CROSS_OS_VERSION=11.0',
            'TOOLBASE=' + str(host), 'TOOLDIR=' + str(tools),
            'CROSS_DESTDIR=' + str(work / 'sysroot'),
            'WRAPPER_BINDIR=' + str(work / 'wrappers'), 'PREFIX=/usr/pkg',
            'BUILDLINK_DIR=' + str(work / 'buildlink'),
            'EMBERBSD_CROSS_BUILD_PYTHON=' + python, 'EMBERBSD_SDK_SOURCE=' + sdk.root,
            'EMBERBSD_GI_QUERY_CONFIG=' + str(work / 'query.json'),
            'EMBERBSD_CROSS_BUILD_CC=/usr/bin/cc', 'EMBERBSD_CROSS_BUILD_CXX=/usr/bin/c++',
            'GREP=/usr/bin/grep', 'TEST=/bin/test', 'FIND=/usr/bin/find', 'PRINTF=printf']

    def capture(command):
        command = list(map(os.fspath, command))
        try:
            return sdk.capture(command)
        except sdk.CommandError as error:
            return subprocess.CompletedProcess(command, error.returncode,
                                               error.stdout, error.stderr)

    def record(name, result):
        output = result.stdout + result.stderr
        (work / (name + '.log')).write_bytes(output)
        return output.decode('utf-8', 'replace')

    def run(name, *args):
        result = capture(base + list(args))
        output = record(name, result)
        require(result.returncode == 0, name + ': ' + output)
        return output

    result = capture([host / 'bin/rustc', '-vV'])
    native = record('native-rust', result)
    require(result.returncode == 0, 'real Rust version query failed')
    found = re.search(r'^host: (\S+)$', native, re.M)
    require(found is not None, 'real Rust host missing')
    native_host = found[1]
    for target, (arch, triplet, rust, std) in TARGETS.items():
        args = ['MACHINE_ARCH=' + arch, 'CROSS_MACHINE_ARCH=' + arch,
                'MACHINE_GNU_PLATFORM=' + triplet, 'EMBERBSD_CROSS_TARGET=' + target,
                'WRKDIR=' + str(work)]
        reason = run(target + '-reason', *args, '-V', '${PKG_FAIL_REASON}')
        require(not reason.strip(), 'supported target rejected: ' + reason)
        settings = run(target + '-settings', *args, '-V', '${TOOL_DEPENDS}',
                       '-V', '${MESON_ARGS}', '-V', '${MESON_BINARY.nm}',
                       '-V', '${MESON_BINARY.strip}', '-V', '${MAKE_ENV}')
        key, cc_key = rust.upper().replace('-', '_'), rust.replace('-', '_')
        for expected in (std + '-1.99.1', '-Dtriplet=' + rust, triplet + '-nm',
                         triplet + '-strip', triplet + '-ar',
                         'CARGO_TARGET_' + key + '_LINKER=', 'CC_' + cc_key + '=',
                         'CXX_' + cc_key + '=', 'AR_' + cc_key + '=',
                         'CARGO_TARGET_' + native_host.upper().replace('-', '_') + '_LINKER=/usr/bin/cc',
                         'EMBERBSD_SDK_SOURCE=' + sdk.root, python):
            require(expected in settings, 'wrong target/native provider setting: ' + expected)
        other_std = 'rust-std-aarch64-netbsd' if target == 'amd64' else 'rust-std-x86_64-netbsd'
        other_gnu = 'aarch64--netbsd' if target == 'amd64' else 'x86_64--netbsd'
        require(other_std not in settings and other_gnu not in settings,
                'unselected std or GNU provider leaked into target settings')
        for key_name, foreign in (
                ('CROSS_MACHINE_ARCH', 'aarch64' if arch == 'x86_64' else 'x86_64'),
                ('MACHINE_GNU_PLATFORM', 'foreign--netbsd'),
                ('RUST_TARGET', 'aarch64-unknown-netbsd' if rust == 'x86_64-unknown-netbsd'
                 else 'x86_64-unknown-netbsd')):
            rejected = run(target + '-mixed-' + key_name, *args, key_name + '=' + foreign,
                           '-V', '${PKG_FAIL_REASON}')
            require(bool(rejected.strip()), 'mixed provider accepted: ' + key_name)
    unknown = run('unknown', 'MACHINE_ARCH=riscv64', 'CROSS_MACHINE_ARCH=riscv64',
                  'MACHINE_GNU_PLATFORM=riscv64--netbsd', '-V', '${PKG_FAIL_REASON}')
    require(bool(unknown.strip()), 'unknown target accepted')
    common = ['MACHINE_ARCH=x86_64', 'CROSS_MACHINE_ARCH=x86_64',
              'MACHINE_GNU_PLATFORM=x86_64--netbsd', 'EMBERBSD_CROSS_TARGET=amd64']
    (work / 'positive').mkdir()
    run('actual-std-positive', *common, 'WRKDIR=' + str(work / 'positive'), 'emberbsd-librsvg-rust')
    require((work / 'positive/target-std-check.rmeta').is_file() and
            (work / 'positive/target-std-check.rmeta').stat().st_size > 0,
            'actual compiler did not emit target std metadata')
    for directory in ('native-wrappers', 'foreign-compiler'):
        (work / directory).mkdir()
    for name in ('cc', 'c++'):
        (work / 'native-wrappers' / name).symlink_to('/usr/bin/' + name)
    result = capture(base + common + ['WRAPPER_BINDIR=' + str(work / 'native-wrappers'),
                     'WRKDIR=' + str(work / 'foreign-compiler'), 'emberbsd-librsvg-rust'])
    record('actual-foreign-compiler-negative', result)
    require(result.returncode != 0 and
            not os.path.lexists(work / 'foreign-compiler/target-std-check.rmeta'),
            'native compiler accepted as selected target wrapper')
    # Change only this fixture's rustc sysroot. Use genuine native std/core data.
    foreign_host = work / 'foreign-host'
    foreign_lib = foreign_host / 'lib/rustlib/x86_64-unknown-netbsd/lib'
    for directory in (foreign_host / 'bin', foreign_lib, work / 'negative'):
        directory.mkdir(parents=True)
    (foreign_host / 'bin/cargo').symlink_to(host / 'bin/cargo')
    rustc = foreign_host / 'bin/rustc'
    rustc.write_text('#!/bin/sh\nexec ' + shlex.quote(str(host / 'bin/rustc')) +
                     ' --sysroot ' + shlex.quote(str(foreign_host)) + ' "$@"\n', encoding='utf-8')
    rustc.chmod(0o755)
    for library in ('std', 'core'):
        files = list((host / 'lib/rustlib' / native_host / 'lib').glob('lib' + library + '-*.rlib'))
        require(len(files) == 1, 'one genuine foreign std/core input required')
        shutil.copyfile(files[0], foreign_lib / files[0].name)
    result = capture(base + common + ['TOOLBASE=' + str(foreign_host),
                     'WRKDIR=' + str(work / 'negative'), 'emberbsd-librsvg-rust'])
    output = record('actual-foreign-std-negative', result)
    require(result.returncode != 0 and re.search(
            r'E0461|E0514|incompatible|couldn.t find crate.*(?:std|core).*expected target',
            output, re.I) is not None, 'foreign std metadata was accepted or not read by rustc')
    require(not os.path.lexists(work / 'negative/target-std-check.rmeta'),
            'foreign metadata published a success output')
    (work / 'ambiguous').mkdir()
    standard = next(foreign_lib.glob('libstd-*.rlib'))
    shutil.copyfile(standard, foreign_lib / 'libstd-duplicate.rlib')
    result = capture(base + common + ['TOOLBASE=' + str(foreign_host),
                     'WRKDIR=' + str(work / 'ambiguous'), 'emberbsd-librsvg-rust'])
    output = record('actual-ambiguous-std-negative', result)
    require(result.returncode != 0 and 'Missing, ambiguous or linked target std rlib.' in output,
            'ambiguous std was not rejected before metadata import')
    require(not os.path.lexists(work / 'ambiguous/target-std-check.rmeta'),
            'ambiguous std published a success output')
    print('PASS: real bmake selects both canonical target providers and native Rust host linker; mixed/unknown inputs fail')
    print('PASS: actual official Rust 1.99 imports matching amd64 std metadata; genuine native foreign std is rejected')
    print('PASS: duplicate genuine std archives fail the early uniqueness guard')
    print('SCOPE: no Cargo build, target linking, GI execution, target package or VM acceptance')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'error: {error}', file=sys.stderr)
        raise SystemExit(1)
