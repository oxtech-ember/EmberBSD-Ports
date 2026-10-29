#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check native host selection and sealed generator ABI contracts."""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace

helper = Path(sys.argv[1]).resolve(strict=True)
spec = importlib.util.spec_from_file_location('mesa_generator_host', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def expect_error(fn, text):
    try:
        fn()
    except ValueError as error:
        assert text in str(error), str(error)
    else:
        raise AssertionError('expected ValueError containing ' + text)


linux = module.host_policy('Linux', 'x86_64', 'clang')
assert module.loader_key("/lib64/ld-linux-x86-64.so.2") == "ld-linux-x86-64.so.2"
assert module.is_system_library_path('/usr/lib')
assert module.is_system_library_path('/usr/lib/x86_64-linux-gnu')
assert not module.is_system_library_path('/usr/library')
assert linux['inspector'] == 'llvm-readelf'
assert linux['loader'] == '/usr/bin/ldd'
assert linux['compiler_family'] == 'clang'
darwin = module.host_policy('Darwin', 'arm64', 'clang')
assert darwin['inspector'] == 'otool'
assert darwin['loader'] == 'dyld'
assert module.host_policy('Darwin', 'arm64', 'gcc')['compiler_family'] == 'gcc'
expect_error(lambda: module.host_policy('Linux', 'aarch64', 'clang'), 'Unsupported native Mesa host')
expect_error(lambda: module.host_policy('Linux', 'x86_64', 'gcc'), 'Unsupported native Mesa host')
expect_error(lambda: module.host_policy('Darwin', 'x86_64', 'clang'), 'Unsupported native Mesa host')

with tempfile.TemporaryDirectory() as root:
    prefix = Path(root)
    tool = prefix / 'bin' / 'clang'
    tool.parent.mkdir()
    tool.write_bytes(b'tool')
    tool.chmod(0o755)
    assert module.require_prefix_tool(tool, prefix, 'cc') == tool.resolve()
    expect_error(lambda: module.require_prefix_tool('/usr/bin/env', prefix, 'cc'), 'escapes selected native prefix')
    escaped = prefix / 'bin' / 'external-clang'
    escaped.symlink_to('/usr/bin/env')
    expect_error(lambda: module.require_prefix_tool(escaped, prefix, 'cc'), 'escapes selected native prefix')
    readelf = prefix / 'bin' / 'llvm-readelf'
    readelf.write_bytes(b'tool')
    readelf.chmod(0o755)
    readobj = prefix / 'bin' / 'llvm-readobj'
    readelf.rename(readobj)
    readelf.symlink_to(readobj.name)
    native = SimpleNamespace(bundle_root=str(prefix))
    assert module.inspection_tool(native, linux) == readelf
    assert module.inspection_tool(native, linux).resolve() == readobj.resolve()
    external_readelf = prefix / 'bin' / 'external-readelf'
    external_readelf.symlink_to('/usr/bin/env')
    native.bundle_root = str(prefix)
    original_readelf = prefix / 'bin' / 'llvm-readelf'
    original_readelf.unlink()
    external_readelf.rename(original_readelf)
    expect_error(lambda: module.inspection_tool(native, linux), 'escapes selected native prefix')

    elf = bytearray(20)
    elf[:4] = b'\x7fELF'
    elf[4:7] = bytes((2, 1, 1))
    struct.pack_into('<H', elf, 16, 2)
    struct.pack_into('<H', elf, 18, 62)
    image = prefix / 'bin' / 'native-tool'
    image.write_bytes(elf)
    assert module.validate_binary(image, linux) == 'ELF64-x86_64'
    struct.pack_into('<H', elf, 18, 183)
    image.write_bytes(elf)
    expect_error(lambda: module.validate_binary(image, linux), 'wrong native ELF architecture')

print('PASS: native Mesa generator host matrix and prefix/ELF contracts')
