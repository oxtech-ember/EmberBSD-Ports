#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Run Boost's actual wrapper hook and archive through the selected Darwin tools."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc', 'bmake', 'environment', 'patch', 'llc', 'nm',
                 'initial-libtool', 'full-libtool', 'work'):
        cli.add_argument('--' + name, type=Path, required=True)
    cli.add_argument('--make-arg', action='append', default=[],
                     help='complete native bmake configuration tuple; repeat for each argument')
    args = cli.parse_args()
    root = Path(__file__).resolve().parents[3]
    repair = root / 'profiles/common-build-tools/patches/pkgsrc-boost-darwin-libtool.patch'
    assert all(value.is_absolute() for value in vars(args).values() if isinstance(value, Path))
    environment = json.loads(args.environment.read_text())
    environment.update(PYTHONDONTWRITEBYTECODE='1', LC_ALL='C')
    args.work.mkdir()
    tree = args.work / 'pkgsrc'
    tree.mkdir()
    packages = ('boost-headers', 'boost-jam', 'boost-libs')
    for entry in args.pkgsrc.iterdir():
        if entry.name in ('devel', 'meta-pkgs'):
            category = tree / entry.name
            category.mkdir()
            for child in entry.iterdir():
                if ((entry.name == 'devel' and child.name in packages) or
                        (entry.name == 'meta-pkgs' and child.name == 'boost')):
                    shutil.copytree(child, category / child.name)
                else:
                    (category / child.name).symlink_to(child)
        else:
            (tree / entry.name).symlink_to(entry)
    hook = args.work / 'empty-hook.mk'
    hook.write_text('post-wrapper:\n')
    makeconf = next(value.split('=', 1)[1] for value in args.make_arg if value.startswith('MAKECONF='))
    unset = args.work / 'unset-selector.mk'
    unset.write_text('.include \"' + makeconf + '\"\n.undef EMBERBSD_DARWIN_LIBTOOL\n')

    def run(label, command, *, success=True):
        result = subprocess.run(list(map(str, command)), env=environment, capture_output=True,
                                text=True, timeout=60)
        (args.work / (label + '.log')).write_text(result.stdout + result.stderr)
        assert (result.returncode == 0) == success, (label, result.returncode, result.stdout, result.stderr)
        return result

    def apply(reverse=False):
        run('reverse-patch' if reverse else 'apply-patch',
            [args.patch, '-f', '-F', '0', '-p1', '-R' if reverse else '-N',
             '-d', tree, '-i', repair])

    common = tree / 'meta-pkgs/boost/Makefile.common'
    # Accept either a baseline export or one that already carries this repair.
    if '_BOOST_DARWIN_LIBTOOL' in common.read_text():
        apply(reverse=True)

    def wrapper(package, label, selected, *, phase='initial', system='Darwin', success=True):
        directory = args.work / label
        directory.mkdir()
        link = directory / 'libtool'
        link.write_text('Original wrapper must remain untouched on refusal or non-Darwin.\n')
        command = [args.bmake, *args.make_arg, '-C', tree / 'devel' / package,
                   '-f', 'Makefile', '-f', hook, 'post-wrapper',
                   'WRAPPER_BINDIR=' + str(directory), 'WRKOBJDIR=' + str(args.work / 'objects'),
                   'PKG_DBDIR=' + str(args.work / 'pkgdb'), 'OPSYS=' + system,
                   'EMBERBSD_DARWIN_TOOL_PHASE=' + phase]
        command.append('MAKECONF=' + str(unset) if selected is None else
                       'EMBERBSD_DARWIN_LIBTOOL=' + str(selected))
        if system != 'Darwin':
            command += ['MACHINE_ARCH=aarch64', 'HOST_MACHINE_ARCH=aarch64',
                        'OS_VERSION=' + ('7.0' if system == 'Linux' else '11.0'),
                        'OPSYS_VERSION=' + ('070000' if system == 'Linux' else '110000'),
                        'LOWER_OPSYS=' + system.lower()]
        result = run(label, command, success=success)
        if not success:
            assert "EMBERBSD_DARWIN_LIBTOOL" in result.stdout + result.stderr, result
        return link

    baseline = wrapper('boost-headers', 'baseline', args.initial_libtool)
    assert baseline.is_symlink() and os.readlink(baseline) != str(args.initial_libtool), \
        'Baseline no longer reproduces the selected-tool replacement'
    apply()
    source = args.work / 'archive.ll'
    source.write_text('define i32 @ember_boost_archive() { ret i32 42 }\n')
    obj = args.work / 'archive.o'
    run('object', [args.llc, '-mtriple=arm64-apple-darwin26.0.0', '-filetype=obj', source, '-o', obj])
    for package in packages:
        for phase, selected in (('initial', args.initial_libtool), ('full', args.full_libtool)):
            label = package + '-' + phase
            link = wrapper(package, label, selected, phase=phase)
            assert link.is_symlink() and os.readlink(link) == str(selected), (label, link)
            archive = args.work / (label + '.a')
            run(label + '-archive', [link, '-static', '-o', archive, obj])
            symbols = run(label + '-symbols', [args.nm, '--defined-only', archive])
            assert '_ember_boost_archive' in symbols.stdout, symbols.stdout
    nonexec = args.work / 'nonexec'
    nonexec.write_text('Not an executable tool.\n')
    for phase in ('initial', 'full'):
        for label, selected in [('unset', None), ('empty', ''), ('relative', 'libtool'), ('absent', args.work / 'absent'),
                                ('nonexec', nonexec), ('directory', args.work)]:
            link = wrapper('boost-headers', phase + '-' + label, selected, phase=phase, success=False)
            assert not link.is_symlink() and link.read_text().startswith('Original wrapper'), link
    for system in ('Linux', 'NetBSD'):
        for package in packages:
            link = wrapper(package, package + '-' + system, 'invalid-selection', system=system)
            assert not link.is_symlink() and link.read_text().startswith('Original wrapper'), link
    print('PASS: baseline replaces the explicit Darwin selection; zero-fuzz repair preserves it')
    print('PASS: actual Boost headers/jam/libs post-wrapper hooks and six initial/full native archive/symbol checks')
    print('PASS: twelve invalid-selector refusals preserve the old wrapper; Linux/NetBSD hooks remain unchanged')
    print('SCOPE: native make hooks and tiny LLVM-generated Darwin object; no Boost compilation or prefix installation')


if __name__ == '__main__':
    main()
