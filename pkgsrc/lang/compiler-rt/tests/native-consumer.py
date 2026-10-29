#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile and run normal native libc++ consumers across a DSO boundary."""
import argparse
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'macos-sdk', 'macos-minimum', 'work'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--stage', help='producer DESTDIR; omit to check installed default selection')
parser.add_argument('--native-cxx', help='selected SDK native C++ binding for the installed runtime')
args = parser.parse_args()
sys.path.insert(0, str(Path(args.sdk_source) / 'src'))
from emberbsd_sdk import host_prefix, native_checks, process
host = Path(args.host_prefix).resolve(strict=True)
work = Path(args.work)
if not work.is_absolute() or work.exists():
    parser.error('--work must be a new absolute directory')
work.mkdir(parents=True)
native = host_prefix.load_host_prefix(str(host), compiler_family='clang',
    required_roles=('cc', 'cxx', 'ld', 'ar', 'ranlib', 'python', 'sh'))
env = native_checks.check_environment(native, bindings=str(work / 'commands'),
    environment=process.sanitized_environment())
env.update(SDKROOT=args.macos_sdk, MACOSX_DEPLOYMENT_TARGET=args.macos_minimum)
if args.native_cxx:
    selected = Path(args.native_cxx)
    if not selected.is_absolute() or not selected.is_file() or not os.access(selected, os.X_OK):
        parser.error('--native-cxx must select an absolute executable binding')
else:
    selected = Path(env['CXX'])
common = [str(selected), '--no-default-config', '--ld-path=' + native.tool('ld'),
          '-mmacosx-version-min=' + args.macos_minimum, '-isysroot', args.macos_sdk,
          '-std=c++23']
if args.stage:
    installed = Path(args.stage) / str(host).lstrip('/')
    common += ['-nostdinc++', '-isystem', str(installed / 'include/libc++/v1'),
               '-L' + str(installed / 'lib/libc++'), '-stdlib=libc++']
    # The Darwin ABI view contains only the selected SDK's two ABI headers;
    # it must not expose a second full standard-library header tree.
    abi_view = work / 'darwin-cxxabi'
    abi_view.mkdir()
    for name in ('cxxabi.h', '__cxxabi_config.h'):
        (abi_view / name).symlink_to(Path(args.macos_sdk) / 'usr/include/c++/v1' / name)
    common += ['-idirafter', str(abi_view)]
    env['DYLD_LIBRARY_PATH'] = str(installed / 'lib/libc++')
else:
    installed = host
files = Path(__file__).resolve().parent
bridge = work / 'libbridge.dylib'
main = work / 'main'
process.run_logged(common + ['-dynamiclib', str(files / 'native-consumer-bridge.cc'),
    '-Wl,-install_name,@rpath/libbridge.dylib', '-o', str(bridge)], str(work / 'bridge.log'), env=env)
process.run_logged(common + [str(files / 'native-consumer.cc'), '-L' + str(work), '-lbridge',
    '-Wl,-rpath,' + str(work), '-o', str(main)], str(work / 'main.log'), env=env)
env['DYLD_PRINT_LIBRARIES'] = '1'
process.run_logged([str(main)], str(work / 'run.log'), env=env)
if str((installed / 'lib/libc++/libc++_ember1.1.dylib').resolve()) not in (work / 'run.log').read_text():
    raise SystemExit('expected selected libc++ was not loaded')
objc = work / 'objc-consumer'
process.run_logged(common + ['-fobjc-arc', str(files / 'native-consumer-objc.mm'),
    '-framework', 'Foundation', '-o', str(objc)], str(work / 'objc-build.log'), env=env)
process.run_logged([str(objc)], str(work / 'objc-run.log'), env=env)
if str((installed / 'lib/libc++/libc++_ember1.1.dylib').resolve()) not in (work / 'objc-run.log').read_text():
    raise SystemExit('Objective-C consumer did not load selected libc++')
print('native filesystem, streams, locale, threads, demangle, Objective-C and cross-DSO exceptions PASS')
