#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check actual native Clang23/GCC16 dependencies.
import os
from pathlib import Path
import shlex
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_sdk as sdk
import llvm_native as native


def test(args):
    if len(args) != 2:
        raise ValueError('usage: HOST_CXX=/absolute/c++ llvm-native-headers.py --sdk-source SDK TARGET_SYSROOT NEW_WORK')
    sysroot = sdk.existing_directory(args[0])
    work = Path(sdk.new_destination(args[1], [sysroot]))
    cxx = os.environ['HOST_CXX']
    triple = native.capture(cxx, '-dumpmachine')
    compiler = native.compiler(cxx, triple, [])
    roots = [str(work), *compiler['header_roots']]
    foreign = sysroot + '/usr/include/stdbool.h'
    if not Path(foreign).is_file():
        raise ValueError('Actual target stdbool.h is required')
    (work / 'include').mkdir(parents=True)
    extra_checks = 0

    def rejects(name, path, allowed, forbidden, expected):
        nonlocal extra_checks
        try:
            native.validate_header(path, allowed, forbidden=forbidden)
        except ValueError as error:
            if expected not in str(error):
                raise ValueError('FAIL: ' + name + ': ' + str(error)) from error
        else:
            raise ValueError('FAIL: ' + name + ': accepted ' + repr(path))
        extra_checks += 1
        print('PASS: ' + name, flush=True)

    if compiler['family'] == 'clang':
        clang_source = work / 'clang-standard.cpp'
        clang_source.write_text('#include <type_traits>\n')
        depfile = native.capture(cxx, '-M', '-MT', 'clang-standard', str(clang_source))
        dependencies = shlex.split(depfile.replace('\\\n', ' ').removeprefix('clang-standard:'))
        emitted = next((path for path in dependencies if '..' in path.split('/')), None)
        if emitted is None:
            raise ValueError('Clang depfile did not emit a noncanonical absolute header path')
        canonical = str(Path(emitted).resolve(strict=True))
        if not any(canonical == root or canonical.startswith(root + '/') for root in compiler['header_roots']):
            raise ValueError('Clang header dependency did not resolve into a measured native include root')
        if native.validate_header(emitted, roots, forbidden=[sysroot]) != canonical:
            raise ValueError('Clang header validation did not return the canonical dependency path')
        extra_checks += 1
        print('PASS: real Clang depfile accepts an allowed normalized header path', flush=True)

    allowed = work / 'allowed-root'
    allowed.mkdir()
    header = allowed / 'valid.h'
    header.write_text('/* measured native test header */\n')
    alias = work / 'allowed-root-alias'
    alias.symlink_to(allowed, target_is_directory=True)
    if native.validate_header(str(header), [str(alias)], forbidden=[]) != str(header.resolve(strict=True)):
        raise ValueError('FAIL: canonicalized allowed include root')
    extra_checks += 1
    print('PASS: allowed include roots are compared canonically', flush=True)
    rejects('relative dependency is refused', 'allowed-root/valid.h', [str(allowed)], [], 'unsafe native header dependency')

    control_dir = allowed / '\nsegment'
    control_dir.mkdir()
    control_path = str(control_dir) + '/../../allowed-root/valid.h'
    rejects('raw control characters are refused before normalization', control_path, [str(allowed)], [], 'unsafe native header dependency')
    rejects('missing dependency is refused', str(allowed / 'missing.h'), [str(allowed)], [], 'does not exist')
    rejects('directory dependency is refused', str(allowed), [str(work)], [], 'not a regular file')

    narrow_root = work / 'narrow-allowed-root'
    narrow_root.mkdir()
    escaped = work / 'outside-allowed-root.h'
    escaped.write_text('/* outside the allowed root */\n')
    escaped_raw = str(narrow_root) + '/../outside-allowed-root.h'
    rejects('normalized path escaping a raw allowed prefix is refused', escaped_raw, [str(narrow_root)], [], 'unexpected native header dependency')

    (work / 'native.cpp').write_text('#include <linux/types.h>\n')
    dep_flags = ['-fno-canonical-system-headers'] if compiler['family'] == 'gcc' else []
    before = native.capture(cxx, '-M', '-MT', 'native', str(work / 'native.cpp'))
    after = native.capture(cxx, *dep_flags, '-M', '-MT', 'native', str(work / 'native.cpp'))
    (work / 'before.d').write_text(before + '\n')
    (work / 'after.d').write_text(after + '\n')
    dependencies = shlex.split(after.replace('\\\n', ' ').removeprefix('native:'))
    for path in dependencies:
        native.validate_header(path, roots, forbidden=[sysroot])
    print('PASS: real compiler dependencies belong to measured native include roots')
    if compiler['family'] == 'gcc':
        tokens = [native.capture(cxx, *flags, '-E', '-P', str(work / 'native.cpp')) for flags in ([], dep_flags)]
        if tokens[0] != tokens[1]:
            raise ValueError('Dependency-name option changed actual preprocessed tokens')
        print('PASS: dependency-name option preserves actual preprocessed tokens')
    link = work / 'include/target-bool.h'
    link.symlink_to(foreign)
    (work / 'foreign.cpp').write_text('#include <target-bool.h>\n')
    foreign_dependencies = native.capture(cxx, *dep_flags, '-M', '-MT', 'foreign', '-isystem', str(work / 'include'), str(work / 'foreign.cpp'))
    (work / 'foreign.d').write_text(foreign_dependencies + '\n')
    paths = shlex.split(foreign_dependencies.replace('\\\n', ' ').removeprefix('foreign:'))
    if compiler['family'] == 'gcc' and str(link) not in paths:
        raise ValueError('GCC did not retain the actual work header link')
    target_alias = work / 'target-sysroot-alias'
    target_alias.symlink_to(sysroot, target_is_directory=True)
    try:
        native.validate_header(str(link), roots, forbidden=[str(target_alias)])
    except ValueError as error:
        if 'resolves inside a target tree' not in str(error):
            raise
    else:
        raise ValueError('Accepted a work header link into the real target sysroot')
    print('PASS: work header link into actual target sysroot is refused before local classification')
    sdk.write_json(work / 'receipt.json', dict(scope='Actual native Clang23/GCC16 header scan and target-header refusal only', compiler=cxx, target_header=foreign, target_header_sha256=sdk.digest(foreign), dependencies=dependencies, refused_work_link=str(link), checks=2 + extra_checks + (compiler['family'] == 'gcc')))
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(test))
