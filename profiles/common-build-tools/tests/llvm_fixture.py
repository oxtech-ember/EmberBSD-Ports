# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). CMake fixture only, never LLVM acceptance.
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
FILES = Path(__file__).resolve().parents[1] / '../../pkgsrc/lang/llvm/files'
sys.path.insert(0, str(FILES))
from sdk_source import load_sdk


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), FILES / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def fixture(work, sdk_source, cmake, source=None, build=None, recipe=None, sdk_recipe=None, wrapper=True, include_empty=True):
    work = Path(work)
    source = Path(source or work / 'source')
    build = Path(build or source / 'build')
    recipe = Path(recipe or work / 'recipe')
    sdk_recipe = Path(sdk_recipe or work / 'sdk-recipe')
    for p in (source, build, recipe / 'files', sdk_recipe, work / 'bin', work / 'lists'):
        p.mkdir(parents=True, exist_ok=True)
    for name in ('select-package-stage.py', 'sdk_source.py'):
        shutil.copyfile(FILES / name, recipe / 'files' / name)
    (recipe / 'patch').write_text('prepared patch')
    (sdk_recipe / 'PLIST.fixture').write_text('declared SDK')
    (work / 'target-abi.h').write_text('target ABI fixture')
    for name, text in [('gcc', 'GCC16 fixture'), ('tblgen', 'LLVM23 fixture')]:
        (work / 'bin' / name).write_text(text)
    for name, text in [('empty.dat', ''), ('runtime.dat', 'runtime fixture\n'), ('license', 'license fixture\n')]:
        (source / name).write_text(text)
    (build / 'object.dat').write_text('SDK object fixture\n')
    (source / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.20)
project(LLVMReuseFixture NONE)
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/runtime.dat" DESTINATION lib RENAME libLLVM.so.23.1)
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/empty.dat" DESTINATION include/llvm/IR RENAME Empty.h)
install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/license" DESTINATION include/llvm/Support RENAME LICENSE.TXT)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/object.dat" DESTINATION include/llvm/IR RENAME Module.h)
''')
    if not include_empty:
        cmake_file = source / 'CMakeLists.txt'
        cmake_file.write_text(''.join(line for line in cmake_file.read_text().splitlines(keepends=True) if 'empty.dat' not in line))
    subprocess.run([cmake, '-S', str(source), '-B', str(build)], check=True, stdout=subprocess.DEVNULL)
    selected_cmake = cmake
    if wrapper:
        selected_cmake = str(work / 'bin/cmake')
        Path(selected_cmake).write_text(f'''#!{sys.executable}
import json, os, pathlib, subprocess, sys
pathlib.Path({str(work / 'last-install-args.json')!r}).write_text(json.dumps(sys.argv[1:]))
with open({str(work / 'install-invocations.log')!r}, 'a') as log: log.write(os.environ['DESTDIR'] + '\\n')
obj = pathlib.Path({str(build / 'object.dat')!r})
original = obj.read_bytes()
mode = os.environ.get('LLVM_REUSE_TEST_MUTATE')
try:
    if mode == 'exit97': sys.exit(97)
    if mode == 'aba': obj.write_bytes(b'temporary wrong SDK bytes')
    result = subprocess.run([{cmake!r}, *sys.argv[1:]])
    dest = pathlib.Path(os.environ['DESTDIR'])
    if mode == 'missing': (dest / 'usr/pkg/include/llvm/IR/Module.h').unlink()
    if mode == 'outside': (dest / 'outside-prefix').write_text('unexpected output')
    if mode == 'after': obj.write_bytes(b'changed after installation')
    sys.exit(result.returncode)
finally:
    if mode == 'aba': obj.write_bytes(original)
''')
        os.chmod(selected_cmake, 0o755)
    runtime = ['lib/libLLVM.so.23.1', 'include/llvm/Support/LICENSE.TXT']
    devel = ['include/llvm/IR/Module.h'] + (['include/llvm/IR/Empty.h'] if include_empty else [])
    lists = {}
    for kind, entries in dict(full=runtime + devel, runtime=runtime, devel=devel).items():
        path = work / 'lists' / kind
        path.write_text('\n'.join(entries) + '\n')
        lists[kind] = str(path)
    package = work / 'archive-input'
    package.mkdir()
    contents = '@cwd /usr/pkg\n@name llvm-23.1.3nb1\n'
    for name, path in zip(runtime, [source / 'runtime.dat', source / 'license']):
        contents += name + '\n@comment MD5:' + hashlib.md5(path.read_bytes()).hexdigest() + '\n'
    (package / '+CONTENTS').write_text(contents)
    (package / '+BUILD_INFO').write_text('OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=aarch64\nOBJECT_FMT=ELF\n')
    archive = work / 'llvm-23.1.3nb1.tgz'
    subprocess.run(['/usr/bin/tar', '-czf', str(archive), '-C', str(package), '+CONTENTS', '+BUILD_INFO'], check=True)
    value = dict(schema=2, version='23.1.3', target=dict(opsys='NetBSD', version='11.0', arch='aarch64', triple='aarch64--netbsd'),
        source=str(source), build=str(build), recipe=str(recipe), sdk_recipe=str(sdk_recipe), install_strip=True,
        flags={'CXXFLAGS': '-O2', 'CMAKE_CONFIGURE_ARGS': '-DCMAKE_SYSTEM_NAME=NetBSD'}, cmake=selected_cmake,
        python=os.path.realpath(sys.executable), sdk_source=sdk_source, tar='/usr/bin/tar', manifests=lists,
        files=dict(compiler=[str(work / 'bin/gcc')], native_tools=list(dict.fromkeys([selected_cmake, cmake, os.path.realpath(sys.executable), '/usr/bin/tar', str(work / 'bin/tblgen')])), patches=[str(recipe / 'patch')], target_abi=[str(work / 'target-abi.h')]),
        runtime=dict(archive=str(archive), sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
    return value
