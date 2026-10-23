#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Query current pkgsrc inputs at the shared root.
import importlib.util
import os
from pathlib import Path
import shlex
import sys
sys.dont_write_bytecode = True
from sdk_source import load_sdk

_spec = importlib.util.spec_from_file_location('llvm_reuse', Path(__file__).with_name('reuse-package-stage.py'))
reuse = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reuse)
FLAGS = '''CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CMAKE_CONFIGURE_ARGS CONFIGURE_ENV
CC CXX CPP AR AS LD RANLIB STRIP CWRAPPERS_APPEND.cc CWRAPPERS_APPEND.cxx
PKG_OPTIONS _CMAKE_BUILD_SYSTEM INSTALL_TARGET CMAKE_INSTALL_ARGS
LLVM_TARGETS_TO_BUILD LLVM_EXPERIMENTAL_TARGETS_TO_BUILD
CROSS_DESTDIR TOOLDIR MACHINE_GNU_PLATFORM TOOL_PYTHONBIN EMBERBSD_LLVM_NATIVE_TOOLS
MAKE_ENV CMAKE_BUILD_ARGS _CMAKE_BUILD_TOOL BUILD_TARGET BUILD_DIRS CONFIGURE_DIR
SETENV RUN INSTALL_ENV INSTALL_DIRS PREFIX'''.split()
FIELDS = FLAGS + '''PKGNAME PKGPATH USE_CROSS_COMPILE OPSYS OS_VERSION MACHINE_ARCH
LLVM_VERSION WRKDIR WRKSRC CMAKE_BUILD_DIR EMBERBSD_LLVM_PKGDIR
CMAKE .MAKE.MAKEFILES PKG_FAIL_REASON'''.split()


def prepare(template, output, bmake, package, receipt, sdk_source):
    from emberbsd_sdk.jsonio import read_json, write_json
    from emberbsd_sdk.paths import canonical_existing, canonical_new, reject_overlap
    from emberbsd_sdk.process import capture
    value = read_json(template)
    work = value['runtime_work']
    reuse.check(os.path.isabs(work) and os.path.isdir(work), 'Existing runtime_work required')
    package = canonical_existing(package)
    # Keep inherited MAKEFLAGS. Query current metadata at the actual reused
    # build root, without rewriting any compiler or environment value.
    command = [bmake, '-C', package, '_PKGSRC_BARRIER=yes', '_MAKEVARS_MK=defined',
               'EMBERBSD_LLVM_REUSE_QUERY=yes', 'WRKDIR=' + work]
    for key in FIELDS:
        command.extend(['-v', key])
    lines = capture(command).stdout.decode().splitlines()
    reuse.check(len(lines) == len(FIELDS), 'Invalid current pkgsrc query')
    row = dict(zip(FIELDS, lines))
    reuse.check(not row['PKG_FAIL_REASON'], 'Current pkgsrc inputs failed: ' + row['PKG_FAIL_REASON'])
    reuse.check(row['USE_CROSS_COMPILE'] == 'yes' and row['PKGPATH'] in ('lang/llvm', 'lang/llvm-devel'), 'Cross LLVM package required')
    target = value['target']
    for field, key in dict(OPSYS='opsys', OS_VERSION='version', MACHINE_ARCH='arch', MACHINE_GNU_PLATFORM='triple').items():
        reuse.check(row[field] == target[key], f'Current target differs: {field}')
    reuse.check(row['LLVM_VERSION'] == value['version'], 'Current LLVM version differs')
    reuse.check(row['WRKDIR'] == work and row['WRKSRC'] == value['source'] and row['WRKSRC'] + '/' + row['CMAKE_BUILD_DIR'] == value['build'], 'Current LLVM source/build root differs')
    reuse.check(row['INSTALL_TARGET'] in ('install', 'install/strip'), 'Unsupported CMake install target')
    recipe = canonical_existing(row['EMBERBSD_LLVM_PKGDIR'])
    sdk_recipe = canonical_existing(recipe + '/../llvm-devel')
    reuse.check(recipe == canonical_existing(value['recipe']) and sdk_recipe == canonical_existing(value['sdk_recipe']), 'Current recipe roots differ')
    value['schema'] = 2
    value['flags'] = {key: row[key] for key in FLAGS}
    value['install_strip'] = row['INSTALL_TARGET'] == 'install/strip'
    value['cmake'] = canonical_existing(row['CMAKE'])
    value['python'] = canonical_existing(sys.executable)
    value['sdk_source'] = canonical_existing(sdk_source)
    value.pop('perl', None)
    files = value['files']
    for kind in ('compiler', 'native_tools', 'patches', 'target_abi'):
        reuse.check(isinstance(files[kind], list) and files[kind], f'Missing {kind} inventory')
    compiler_roots = [canonical_existing(path) for path in files['compiler']]
    for name in ('gcc', 'g++', 'strip'):
        driver = row['TOOLDIR'] + '/bin/' + target['triple'] + '-' + name
        reuse.check(canonical_existing(driver) in compiler_roots, f'Current compiler tool missing from inventory: {name}')
    native = [bmake, value['python'], value['cmake'], row['TOOL_PYTHONBIN']]
    native.extend(row['EMBERBSD_LLVM_NATIVE_TOOLS'] + '/' + name for name in ('llvm-tblgen', 'llvm-min-tblgen', 'llvm-config'))
    # The build tool command is recorded verbatim above. Its actual executable
    # must also be an explicit hashed input. Reject ambiguous command wrappers.
    tool = shlex.split(row['_CMAKE_BUILD_TOOL'])
    reuse.check(tool and os.path.isabs(tool[0]), 'Absolute current CMake build tool required')
    native.append(tool[0])
    files['native_tools'] = sorted(set(files['native_tools'] + [canonical_existing(path) for path in native]))
    files['sdk_api'] = sorted(str(p) for p in Path(sdk_source, 'src', 'emberbsd_sdk').rglob('*.py'))
    makefiles = [canonical_existing(os.path.join(package, path)) for path in shlex.split(row['.MAKE.MAKEFILES'])]
    files['pkgsrc'] = sorted({path for path in makefiles if not any(path.startswith(root + '/') for root in (recipe, sdk_recipe))})
    reuse.check(os.path.isabs(output) and os.path.isdir(os.path.dirname(output)) and not os.path.islink(output), 'Regular context output path required')
    output = canonical_new(output)
    reuse.reject_overlaps(output, reuse.input_roots(value), 'Context output overlaps LLVM inputs')
    protected = [p for group in files.values() for p in group] + list(value['manifests'].values()) + [template, value['runtime']['archive']]
    if receipt != '-':
        protected.append(receipt)
    # Check path and inode identity before opening the output. A hardlink to
    # the accepted receipt is equally protected. Exclusive atomic JSON writes
    # also keep a shared alias from being truncated after this check.
    for path in protected:
        try:
            reject_overlap(output, path)
        except Exception as error:
            raise ValueError('Context output replaces an input') from error
    write_json(output, value, exclusive=False)
    reuse.context(output)
    print('PASS: current pkgsrc compile and build commands were queried without string normalization.')


if __name__ == '__main__':
    from sdk_source import exit_error, install_signal_handlers
    install_signal_handlers()
    try:
        sdk, args = load_sdk()
        if len(args) != 5:
            raise ValueError('Usage: prepare-reuse-inputs.py [--sdk-source SOURCE] TEMPLATE OUTPUT BMAKE PACKAGE_DIRECTORY RECEIPT_OR_DASH')
        prepare(*args, sdk_source=sdk)
    except Exception as error:
        exit_error(error)
