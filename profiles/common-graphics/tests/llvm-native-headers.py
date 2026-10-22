#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check actual native GCC16 dependencies.
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
        raise ValueError('usage: HOST_CXX=/absolute/g++ llvm-native-headers.py --sdk-source SDK TARGET_SYSROOT NEW_WORK')
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
    (work / 'native.cpp').write_text('#include <linux/types.h>\n')
    before = native.capture(cxx, '-M', '-MT', 'native', str(work / 'native.cpp'))
    after = native.capture(cxx, '-fno-canonical-system-headers', '-M', '-MT', 'native', str(work / 'native.cpp'))
    (work / 'before.d').write_text(before + '\n')
    (work / 'after.d').write_text(after + '\n')
    dependencies = shlex.split(after.replace('\\\n', ' ').removeprefix('native:'))
    for path in dependencies:
        native.validate_header(path, roots, forbidden=[sysroot])
    print('PASS: real GCC16 UAPI dependencies belong to measured native include roots')
    tokens = [native.capture(cxx, *flags, '-E', '-P', str(work / 'native.cpp')) for flags in ([], ['-fno-canonical-system-headers'])]
    if tokens[0] != tokens[1]:
        raise ValueError('Dependency-name option changed actual preprocessed tokens')
    print('PASS: dependency-name option preserves actual preprocessed tokens')
    link = work / 'include/target-bool.h'
    link.symlink_to(foreign)
    (work / 'foreign.cpp').write_text('#include <target-bool.h>\n')
    foreign_dependencies = native.capture(cxx, '-fno-canonical-system-headers', '-M', '-MT', 'foreign', '-isystem', str(work / 'include'), str(work / 'foreign.cpp'))
    (work / 'foreign.d').write_text(foreign_dependencies + '\n')
    paths = shlex.split(foreign_dependencies.replace('\\\n', ' ').removeprefix('foreign:'))
    if str(link) not in paths:
        raise ValueError('GCC did not retain the actual work header link')
    try:
        native.validate_header(str(link), roots, forbidden=[sysroot])
    except ValueError as error:
        if 'resolves inside a target tree' not in str(error):
            raise
    else:
        raise ValueError('Accepted a work header link into the real target sysroot')
    print('PASS: work header link into actual target sysroot is refused before local classification')
    sdk.write_json(work / 'receipt.json', dict(scope='Actual native Linux GCC16 header scan and target-header refusal only', compiler=cxx, target_header=foreign, target_header_sha256=sdk.digest(foreign), dependencies=dependencies, refused_work_link=str(link), checks=3))
    return 0


if __name__ == '__main__':
    sys.exit(sdk.main(test))
