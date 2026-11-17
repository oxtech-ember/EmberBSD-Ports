#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Direct platform protoc and explicit custom runtime remain separate."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
native = SimpleNamespace(host={'os':'Darwin'}, tool=lambda name: '/prefix/bin/' + name)
options = SimpleNamespace(sdk_source=Path('/sdk'), host_compiler_family='clang', host_runtime_root=None)
protoc = Path('/prefix/bin/protoc')
assert build.selected_protoc_command(options, native, protoc, None) == [str(protoc)]
assert build.selected_protoc_command(options, native, protoc, Path('/view')) == [
    '/prefix/bin/python', '/sdk/scripts/run-darwin-with-runtime.py', '--runtime-view', '/view', '--', str(protoc)]
options.host_runtime_root = Path('/custom')
try:
    build.selected_protoc_command(options, native, protoc, None)
    raise AssertionError('custom runtime without scoped view accepted')
except ValueError:
    pass
options.host_runtime_root = None
for system in ('Linux', 'NetBSD'):
    native.host['os'] = system
    assert build.selected_protoc_command(options, native, protoc, None) == [str(protoc)]
native.host['os'] = 'other'
try:
    build.selected_protoc_command(options, native, protoc, None)
    raise AssertionError('unverified platform accepted')
except ValueError:
    pass
print('PASS: platform direct protoc; custom runtime retains scoped launcher')

# A native tool is identified by its owner and the run-time dependency closure.
import tempfile
class CommandError(Exception):
    pass
with tempfile.TemporaryDirectory() as temporary:
    prefix = Path(temporary).resolve(); (prefix / 'bin').mkdir()
    real = prefix / 'bin/protoc-36'; real.write_text('binary')
    protoc = prefix / 'bin/protoc'; protoc.symlink_to('protoc-36')
    database = prefix / 'pkgdb'
    def package(name, contents):
        path = database / name; path.mkdir(parents=True)
        (path / '+CONTENTS').write_text(contents)
        for item in ('+BUILD_INFO', '+BUILD_VERSION'):
            (path / item).write_text('metadata')
        return path
    owner = package('protobuf-36.2', 'bin/protoc\nbin/protoc-36\n@pkgdep {abseil,abseil-cpp}>=2025\n')
    abseil = package('abseil-20250814', 'lib/libabsl.dylib\n@pkgdep protobuf>=36\n')
    package('zstd-1.5', 'lib/libzstd.dylib\n')
    answers = {('-E', '{abseil,abseil-cpp}>=2025'): 'abseil-20250814', ('-E', 'protobuf>=36'): 'protobuf-36.2',
               ('-Fe', str(protoc)): 'protobuf-36.2', ('-Fe', str(real)): 'protobuf-36.2'}
    def capture(command, env):
        assert command[:3] == [str(prefix / 'sbin/pkg_info'), '-K', str(database)]
        if tuple(command[3:]) not in answers:
            raise CommandError(command)
        return SimpleNamespace(stdout=(answers[tuple(command[3:])] + '\n').encode())
    sdk = {'process': SimpleNamespace(capture=capture, CommandError=CommandError)}
    options = SimpleNamespace(host_prefix=prefix)
    expected = sorted([str(protoc)] + [str(path / item) for path in (owner, abseil)
                                       for item in ('+CONTENTS', '+BUILD_INFO', '+BUILD_VERSION')])
    assert build.native_tool_inputs(options, sdk, {}, protoc) == expected
    def refused(message):
        try:
            build.native_tool_inputs(options, sdk, {}, protoc)
        except ValueError as error:
            assert message in str(error), error
        else:
            raise AssertionError(message + ' accepted')
    answers[('-Fe', str(real))] = 'zstd-1.5'
    refused('no unique package owner')
    answers[('-Fe', str(real))] = 'protobuf-36.2'
    del answers[('-E', '{abseil,abseil-cpp}>=2025')]
    refused('no unique answer: -E {abseil,abseil-cpp}>=2025')
    answers[('-E', '{abseil,abseil-cpp}>=2025')] = ''
    refused('no unique answer')
    answers[('-E', '{abseil,abseil-cpp}>=2025')] = 'abseil-20250814'
    (abseil / '+BUILD_VERSION').unlink()
    refused('incomplete package metadata')
    outside = Path(temporary).parent / 'protoc'
    try:
        build.native_tool_inputs(options, sdk, {}, outside)
        raise AssertionError('tool outside the prefix accepted')
    except (ValueError, FileNotFoundError):
        pass
print('PASS: native tool inputs are its owner and run-time dependency metadata')
