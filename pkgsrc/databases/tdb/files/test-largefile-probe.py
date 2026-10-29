#!/usr/bin/env python3
"""Exercise Waf's large-file check with selected compiler and two ABI widths."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

source, cc = Path(sys.argv[1]).resolve(), sys.argv[2]
assert Path(cc).is_absolute()
sys.path[:0] = [str(source / 'third_party/waf'), str(source / 'buildtools'),
                str(source / 'buildtools/wafsamba')]
spec = importlib.util.spec_from_file_location(
    'samba_conftests_test', source / 'buildtools/wafsamba/samba_conftests.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Probe:
    def __init__(self, width, cross=False, allow_flags=True):
        self.width = width
        self.env = SimpleNamespace(CROSS_COMPILE=cross)
        self.allow_flags = allow_flags
        self.commands = []
        self.command_result = False
        self.added_flags = []
        self.calls = []
        self.defines = {}

    def CHECK_COMMAND(self, argv):
        self.commands.append(argv)
        return self.command_result

    def CHECK_CODE(self, code, define, execute, cflags='', msg=''):
        assert not execute
        self.calls.append((code, cflags))
        width = 64 if self.allow_flags and cflags == '-D_FILE_OFFSET_BITS=64' else self.width
        ctype = 'long long' if width == 64 else 'int'
        program = f'typedef {ctype} off_t; int main(void) {{ {code}; return 0; }}\n'
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'probe.c').write_text(program)
            result = subprocess.run([cc, '-Werror', '-c', str(p / 'probe.c'),
                                     '-o', str(p / 'probe.o')],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0

    def ADD_CFLAGS(self, flags):
        self.added_flags.append(flags)

    def DEFINE(self, name, value):
        self.defines[name] = value

native = Probe(64)
assert module.CHECK_LARGEFILE(native)
assert len(native.calls) == 1 and native.defines == {}
small = Probe(32)
assert module.CHECK_LARGEFILE(small)
assert len(small.calls) == 2 and small.defines == {'_FILE_OFFSET_BITS': 64}
cross = Probe(64, cross=True)
assert module.CHECK_LARGEFILE(cross)
assert not cross.commands and len(cross.calls) == 1
cross32 = Probe(32, cross=True)
assert module.CHECK_LARGEFILE(cross32)
assert not cross32.commands and cross32.defines == {'_FILE_OFFSET_BITS': 64}
unknown = Probe(32, cross=True, allow_flags=False)
assert not module.CHECK_LARGEFILE(unknown)
assert unknown.commands == [['getconf', 'LFS_CFLAGS']]
fallback = Probe(32, cross=True, allow_flags=False)
fallback.command_result = '-D_FILE_OFFSET_BITS=64'
# The external flags are tested and retained when the standard probes failed.
fallback.CHECK_CODE = lambda code, define, execute, cflags='', msg='': (
    cflags == fallback.command_result and define == 'WORKING_GETCONF_LFS_CFLAGS'
    or define == 'HAVE_LARGEFILE' and bool(fallback.added_flags))
assert module.CHECK_LARGEFILE(fallback)
assert fallback.commands == [['getconf', 'LFS_CFLAGS']]
assert fallback.added_flags == ['-D_FILE_OFFSET_BITS=64']
assert fallback.defines == {'_FILE_OFFSET_BITS': '64'}
assert native.commands == [['getconf', 'LFS_CFLAGS']]
print('large-file compile-only probes and cross fallback: PASS')
