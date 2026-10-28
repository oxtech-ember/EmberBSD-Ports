#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Compile and run normal native libc++ consumers across a DSO boundary."""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'macos-sdk', 'macos-minimum', 'work'):
    parser.add_argument('--' + name, required=True)
parser.add_argument('--stage', help='producer DESTDIR; omit to check installed default selection')
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
common = [env['CXX'], '--no-default-config', '--ld-path=' + native.tool('ld'),
          '-mmacosx-version-min=' + args.macos_minimum, '-isysroot', args.macos_sdk,
          '-std=c++23']
if args.stage:
    installed = Path(args.stage) / str(host).lstrip('/')
    common += ['-nostdinc++', '-isystem', str(installed / 'include/libc++/v1'),
               '-L' + str(installed / 'lib/libc++'), '-stdlib=libc++']
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
if str((installed / 'lib/libc++/libc++.1.dylib').resolve()) not in (work / 'run.log').read_text():
    raise SystemExit('expected selected libc++ was not loaded')
print('native filesystem, locale, thread and cross-DSO exception consumer PASS')
