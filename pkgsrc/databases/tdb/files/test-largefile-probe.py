#!/usr/bin/env python3
"""Exercise Waf's large-file check with selected compiler and two ABI widths."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

source, cc = Path(sys.argv[1]).resolve(), sys.argv[2]
assert Path(cc).is_absolute()
sys.path[:0] = [str(source / 'third_party/waf'), str(source / 'buildtools'),
                str(source / 'buildtools/wafsamba')]
spec = importlib.util.spec_from_file_location(
    'samba_conftests_test', source / 'buildtools/wafsamba/samba_conftests.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Probe:
    def __init__(self, width):
        self.width = width
        self.calls = []
        self.defines = {}

    def CHECK_COMMAND(self, argv):
        return False

    def CHECK_CODE(self, code, define, execute, cflags='', msg=''):
        assert not execute
        self.calls.append((code, cflags))
        width = 64 if cflags == '-D_FILE_OFFSET_BITS=64' else self.width
        ctype = 'long long' if width == 64 else 'int'
        program = f'typedef {ctype} off_t; int main(void) {{ {code}; return 0; }}\n'
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / 'probe.c').write_text(program)
            result = subprocess.run([cc, '-Werror', '-c', str(p / 'probe.c'),
                                     '-o', str(p / 'probe.o')],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0

    def DEFINE(self, name, value):
        self.defines[name] = value

native = Probe(64)
assert module.CHECK_LARGEFILE(native)
assert len(native.calls) == 1 and native.defines == {}
small = Probe(32)
assert module.CHECK_LARGEFILE(small)
assert len(small.calls) == 2 and small.defines == {'_FILE_OFFSET_BITS': 64}
print('large-file compile-only probes: PASS')
