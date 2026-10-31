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
import types
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
    # As in the release archive: CMake runs this script, which has no execute bit.
    entry = tarfile.TarInfo(llvm_host.SOURCE + '/llvm/cmake/config.guess')
    entry.size = 7
    entry.mode = 0o664
    output.addfile(entry, io.BytesIO(b'fixture'))
cmake = executable(work / 'cmake', '''import pathlib,sys
if '--version' in sys.argv: print('cmake fixture'); sys.exit(0)
out=pathlib.Path(sys.argv[sys.argv.index('-B')+1]); out.mkdir(parents=True)
(out/'cmake-argv.json').write_text(__import__('json').dumps(sys.argv[1:]))
import os,shutil
(out/'cmake-env.json').write_text(__import__('json').dumps(
    {'sh': shutil.which('sh'), 'CC_FOR_BUILD': os.environ.get('CC_FOR_BUILD')}))
''')
ninja = executable(work / 'ninja', f'''import pathlib,sys
if '--version' in sys.argv: print('ninja fixture'); sys.exit(0)
root=pathlib.Path(sys.argv[sys.argv.index('-C')+1]); (root/'bin').mkdir()
for name in sys.argv[sys.argv.index('-j')+2:]:
    p=root/'bin'/name; p.write_text('#!{sys.executable}\\nprint("LLVM version 23.1.4")\\n'); p.chmod(0o755)
(root/'lib/cmake/llvm').mkdir(parents=True)
(root/'lib/cmake/llvm/LLVMConfig.cmake').write_text('fixture')
''')
os.environ['HOST_PYTHON'] = sys.executable
native_tools = {'cmake': cmake, 'ninja': ninja, 'python': sys.executable}
for role in ('cc', 'cxx', 'cpp', 'as', 'ld', 'ar', 'ranlib', 'nm', 'strip',
             'pkg-config', 'sh', 'install_name_tool'):
    native_tools[role] = executable(work / ('native-' + role), "print('SDK tool double')\n")
os.environ['HOST_CC'] = native_tools['cc']
os.environ['HOST_CXX'] = native_tools['cxx']
# This is an API double, not a descriptor, producer receipt or tool admission.
native_selection = types.SimpleNamespace(
    tool=lambda role: native_tools[role], command=lambda role: [native_tools[role]], path=str(work),
    abi_flags={key: () for key in ('cppflags', 'cflags', 'cxxflags', 'ldflags')},
    as_dict=lambda: {'format': 'emberbsd-native-toolset-selection', 'version': 1,
                     'api': 1, 'tools': dict(native_tools)})
native_api = types.ModuleType('emberbsd_sdk.native_toolset')
native_api.load_host_prefix = lambda *args, **kwargs: native_selection
sys.modules['emberbsd_sdk.native_toolset'] = native_api
os.environ['EMBERBSD_HOST_PREFIX'] = str(work)
os.environ['JOBS'] = '1'
refused(llvm_host.native, 'llvm', [str(archive), str(work / 'wrong-pin'), cmake, ninja])
assert not (work / 'wrong-pin').exists()
# Explicitly labelled source fixture pin. No release or compiler acceptance.
llvm_host.SOURCE_SHA = hashlib.sha256(archive.read_bytes()).hexdigest()
llvm_host.native('llvm', [str(archive), str(work / 'llvm'), cmake, ninja])
flags = json.loads((work / 'llvm/native/cmake-argv.json').read_text())
guess = work / 'llvm/source' / llvm_host.SOURCE / 'llvm/cmake/config.guess'
assert os.access(guess, os.X_OK), 'CMake cannot run the extracted config.guess'
# GetHostTriple runs "sh config.guess" through PATH; the SDK PATH has no sh.
seen = json.loads((work / 'llvm/native/cmake-env.json').read_text())
assert seen['sh'] and os.path.realpath(seen['sh']) == os.path.realpath(native_tools['sh']), 'CMake cannot find sh'
assert seen['CC_FOR_BUILD'] == native_tools['cc'], 'config.guess has no build compiler'
assert '-DLLVM_TARGETS_TO_BUILD=Native' in flags and '-DLLVM_INCLUDE_TESTS=OFF' in flags
assert '-DPython3_EXECUTABLE=' + sys.executable in flags
assert set(json.loads((work / 'llvm/outputs.json').read_text())) == {'llvm-tblgen', 'llvm-min-tblgen', 'llvm-config'}
assert not (work / 'llvm/inputs.json').exists(), 'Native tools must not require a provenance report'
# The real config has a bare version output, unlike the other generator tools.
executable(work / 'llvm/native/bin/llvm-config', "print('23.1.4')\n")
native_tools['llvm-config'] = str(work / 'llvm/native/bin/llvm-config')
native_tools['llvm-tblgen'] = str(work / 'llvm/native/bin/llvm-tblgen')
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

# Run the real indexed-layout preparation on a new directory. Only external
# compiler/objcopy boundaries are doubles; ELF parsing and file copying are real.
import subprocess
import stat
fixtures, accepted = work / 'dwp-fixtures', work / 'dwp-accepted'
fixtures.mkdir()
accepted.mkdir()
case = 'mode-case'
(fixtures / 'cases.tsv').write_text(case + '\t5\tplain\n')
(fixtures / case).mkdir()
(accepted / case).mkdir()
program = fixtures / case / 'program'
program.write_text('#!' + sys.executable + '\nprint("dwp executable fixture")\n')
program.chmod(0o751)
# ELF64 little-endian with one CU index and a string-offset contribution.
names = b'\0.shstrtab\0.debug_cu_index\0.debug_str_offsets.dwo\0'
chunks = [names, data, b'\0' * 8]
payload = bytearray(64)
headers = [bytes(64)]
for name, chunk in zip(('.shstrtab', '.debug_cu_index', '.debug_str_offsets.dwo'), chunks):
    position = len(payload)
    payload.extend(chunk)
    headers.append(struct.pack('<IIQQQQIIQQ', names.index(name.encode()), 3 if name == '.shstrtab' else 1,
                               0, 0, position, len(chunk), 0, 0, 1, 0))
table = len(payload)
payload.extend(b''.join(headers))
payload[:64] = struct.pack('<16sHHIQQQIHHHHHH', b'\x7fELF\x02\x01\x01' + b'\0' * 9,
                          1, 183, 1, 0, 0, table, 0, 64, 0, 0, 64, 4, 1)
(accepted / case / 'input.dwp').write_bytes(payload)
dwp.query = lambda argv: '16.2.0' if argv[1] == '-dumpfullversion' else 'aarch64--netbsd'
calls = []
def record_tool(path, argv):
    calls.append(argv)
    Path(path).write_text('Compiler/objcopy boundary fixture; no target output.\n')
dwp.log_run = record_tool
os.environ['CC'] = 'gcc16-fixture'
os.environ['OBJCOPY'] = 'objcopy-fixture'
old_umask = os.umask(0o077)
try:
    indexed = work / 'dwp-indexed'
    dwp.prepare([str(accepted), str(fixtures), str(indexed)])
finally:
    os.umask(old_umask)
copy = indexed / case / 'program'
assert copy.read_bytes() == program.read_bytes()
assert stat.S_IMODE(copy.stat().st_mode) == 0o751, 'program permissions were lost'
assert subprocess.check_output([str(copy)], text=True) == 'dwp executable fixture\n'
assert (indexed / 'cases.tsv').read_bytes() == (fixtures / 'cases.tsv').read_bytes()
assert len(calls) == 2
print('PASS: clean indexed DWP preparation preserves program mode and execution')
