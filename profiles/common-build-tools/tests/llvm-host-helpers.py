#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Controller fixtures; no LLVM compilation.
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import sys
import tarfile
sys.dont_write_bytecode = True
from llvm_fixture import load_sdk
sdk, args = load_sdk()
if len(args) != 1:
    sys.exit('Use NEW_WORK')
work = Path(args[0]).absolute()
work.mkdir()
cross = Path(__file__).resolve().parents[1] / 'cross'
sys.path.insert(0, str(cross))
import llvm_host


def executable(path, body):
    path.write_text('#!' + sys.executable + '\n' + body)
    path.chmod(0o755)
    return str(path)


def refused(function, *arguments):
    try:
        function(*arguments)
    except Exception:
        return
    raise AssertionError('invalid controller input accepted')


archive = work / 'llvm.tar.xz'
with tarfile.open(archive, 'w:xz', format=tarfile.USTAR_FORMAT) as output:
    for name in ('llvm', 'clang', 'cmake', 'third-party', 'libc'):
        entry = tarfile.TarInfo(llvm_host.SOURCE + '/' + name + '/fixture')
        entry.size = 7
        output.addfile(entry, io.BytesIO(b'fixture'))
cmake = executable(work / 'cmake', '''import pathlib,sys
if '--version' in sys.argv: print('cmake fixture'); sys.exit(0)
out=pathlib.Path(sys.argv[sys.argv.index('-B')+1]); out.mkdir(parents=True)
(out/'cmake-argv.json').write_text(__import__('json').dumps(sys.argv[1:]))
''')
ninja = executable(work / 'ninja', f'''import pathlib,sys
if '--version' in sys.argv: print('ninja fixture'); sys.exit(0)
root=pathlib.Path(sys.argv[sys.argv.index('-C')+1]); (root/'bin').mkdir()
for name in sys.argv[sys.argv.index('-j')+2:]:
    p=root/'bin'/name; p.write_text('#!{sys.executable}\\nprint("LLVM version 23.1.3")\\n'); p.chmod(0o755)
(root/'lib/cmake/llvm').mkdir(parents=True)
(root/'lib/cmake/llvm/LLVMConfig.cmake').write_text('fixture')
''')
os.environ['HOST_PYTHON'] = sys.executable
os.environ['HOST_CC'] = os.environ['HOST_CXX'] = '/usr/bin/true'
os.environ['JOBS'] = '1'
refused(llvm_host.native, 'llvm', [str(archive), str(work / 'wrong-pin'), cmake, ninja])
assert not (work / 'wrong-pin').exists()
# Explicitly labelled source fixture pin. No release or compiler acceptance.
llvm_host.SOURCE_SHA = hashlib.sha256(archive.read_bytes()).hexdigest()
llvm_host.native('llvm', [str(archive), str(work / 'llvm'), cmake, ninja])
flags = json.loads((work / 'llvm/native/cmake-argv.json').read_text())
assert '-DLLVM_TARGETS_TO_BUILD=Native' in flags and '-DLLVM_INCLUDE_TESTS=OFF' in flags
assert '-DPython3_EXECUTABLE=' + sys.executable in flags
assert set(json.loads((work / 'llvm/outputs.json').read_text())) == {'llvm-tblgen', 'llvm-min-tblgen', 'llvm-config'}
inputs = json.loads((work / 'llvm/inputs.json').read_text())['sha256']
assert str(cross / 'build-llvm-native.py') in inputs, 'entrypoint is missing from native provenance'
assert any(p.endswith('/emberbsd_sdk/process.py') for p in inputs), 'SDK API is missing from native provenance'
# The real config has a bare version output, unlike the other generator tools.
executable(work / 'llvm/native/bin/llvm-config', "print('23.1.3')\n")
llvm_host.native('clang', [str(archive), str(work / 'llvm/native'), str(work / 'clang'), cmake, ninja])
flags = json.loads((work / 'clang/native/cmake-argv.json').read_text())
assert '-DLLVM_TABLEGEN=' + str(work / 'llvm/native/bin/llvm-tblgen') in flags and '-DCLANG_INCLUDE_TESTS=OFF' in flags
refused(llvm_host.native, 'llvm', [str(archive), str(work / 'llvm'), cmake, ninja])
os.environ['JOBS'] = '0'
refused(llvm_host.native, 'llvm', [str(archive), str(work / 'bad-jobs'), cmake, ninja])
assert not (work / 'bad-jobs').exists()
spec = importlib.util.spec_from_file_location('dwp', cross / 'prepare-llvm-dwp-index-tests.py')
dwp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dwp)
words = [5, 1, 1, 1, 0, 0, 1, 6, 0, 8]
data = struct.pack('<10I', *words)
expected = list(words)
expected[8] = 16
assert dwp.rewrite_index(data, lambda offset, length: offset + 16) == struct.pack('<10I', *expected)
assert dwp.rewrite_index(struct.pack('<10I', *(words[:7] + [1] + words[8:])), lambda o, n: 123) == struct.pack('<10I', *(words[:7] + [1] + words[8:]))
refused(dwp.rewrite_index, data[:20], lambda o, n: 16)
print('PASS: native controller source pin, argv, generator-only targets, repeat refusal, job guard and DWP index mutation fixtures')
