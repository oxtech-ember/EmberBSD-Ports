#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), current Python source and metadata regression.
"""Check the canonical recipe without compiling or accepting a runtime."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
RECIPE = ROOT / 'pkgsrc/lang/python315'
PROFILE = ROOT / 'profiles/common-build-tools'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_source(recipe, manifest, archive):
    version = re.search(r'^PY_DISTVERSION=\s*(3\.15\.[0-9]+)$',
                        (recipe / 'dist.mk').read_text(), re.M)
    require(version is not None, 'invalid current Python version')
    version = version[1]
    name = f'Python-{version}.tar.xz'
    rows = [line.split('\t') for line in manifest.splitlines()
            if line.startswith('Python-')]
    info = (recipe / 'distinfo').read_text()
    hashes = re.findall(r'^SHA256 \(' + re.escape(name) + r'\) = ([0-9a-f]{64})$', info, re.M)
    require(len(hashes) == 1, 'missing or duplicate recipe archive checksum')
    require(rows == [[name, hashes[0], f'https://www.python.org/ftp/python/{version}/{name}']],
            'missing, duplicate or changed common source selection')
    require(archive.name == name, 'archive version differs from recipe')
    require(hashlib.sha256(archive.read_bytes()).hexdigest() == hashes[0], 'archive checksum mismatch')
    sizes = re.findall(r'^Size \(' + re.escape(name) + r'\) = ([0-9]+) bytes$', info, re.M)
    require(sizes == [str(archive.stat().st_size)], 'archive size mismatch')
    return version


def verify_patches(recipe):
    info = (recipe / 'distinfo').read_text()
    declared = re.findall(r'^SHA1 \((patch-[^)]+)\) = ([0-9a-f]{40})$', info, re.M)
    patches = sorted((recipe / 'patches').glob('patch-*'))
    require(len(declared) == len(patches) and
            {p.name for p in patches} == {name for name, sha in declared}, 'missing, duplicate or undeclared patch')
    for name, sha in declared:
        content = b''.join(line for line in (recipe / 'patches' / name).read_bytes().splitlines(True)
                           if b'$NetBSD' not in line)
        require(hashlib.sha1(content).hexdigest() == sha, 'patch checksum differs: ' + name)
    return patches


def rejected(function, message):
    try:
        function()
    except ValueError:
        return
    raise ValueError('accepted invalid input: ' + message)


def run(command, output, **kwargs):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
    output.write_bytes(result.stdout)
    require(result.returncode == 0, f'command failed; see {output}')


def source_invariants(source):
    makefile = (source / 'Makefile.pre.in').read_text()
    require(re.search(r'^PY3LIBRARY=$', makefile, re.M), 'PY3LIBRARY must stay empty')
    require('-o 0 -o 1 $(COMPILEALL_OPTS)' in makefile, 'installed bytecode levels changed')
    require('-o 0 -o 1 -o 2 $(COMPILEALL_OPTS)' not in makefile, 'unexpected bytecode level 2')
    require('false && test "$cross_compiling"' not in (source / 'configure').read_text(),
            'cross-host validation was disabled')


def check_plist(source):
    # These installed source trees have no generated Python source entries.
    # Bytecode is checked by packaging; intentional syntax-error fixtures exist.
    prefix = 'lib/python${PY_VER_SUFFIX}/'
    listed = {line[len(prefix):] for line in (RECIPE / 'PLIST').read_text().splitlines()
              if line.startswith(prefix + 'test/') or line.startswith(prefix + 'ensurepip/')}
    suffixes = ('.py', '.cpp', '.whl')
    expected = {str(path.relative_to(source / 'Lib'))
                for tree in ('test', 'ensurepip') for path in (source / 'Lib' / tree).rglob('*')
                if path.is_file() and path.name.endswith(suffixes)}
    listed = {name for name in listed if name.endswith(suffixes)}
    require(listed == expected, 'PLIST source mismatch; missing=' + str(sorted(expected - listed))
            + '; stale=' + str(sorted(listed - expected)))


def build_details(source, work):
    # Execute the real generator with declared target metadata and a different
    # source micro version. No target interpreter or synthetic executable runs.
    fixture = work / 'details-source'
    (fixture / 'Tools/build').mkdir(parents=True)
    (fixture / 'Include').mkdir()
    generator = fixture / 'Tools/build/generate-build-details.py'
    shutil.copy2(source / 'Tools/build/generate-build-details.py', generator)
    header = (source / 'Include/patchlevel.h').read_text()
    (fixture / 'Include/patchlevel.h').write_text(
        re.sub(r'(#define PY_MICRO_VERSION\s+)\d+', r'\g<1>199', header))
    spec = importlib.util.spec_from_file_location('python_build_details', generator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    values = dict(installed_base='/usr/pkg', LDVERSION='3.15', EXE='', MULTIARCH='netbsd',
                  LIBDIR='/usr/pkg/lib', LIBPL='/usr/pkg/lib/python3.15/config-3.15',
                  LDLIBRARY='libpython3.15.so', LIBRARY='libpython3.15.a', PY3LIBRARY='',
                  LIBPYTHON='', LIBPC='/usr/pkg/lib/pkgconfig', INCLUDEPY='/usr/pkg/include/python3.15',
                  STATIC_LIBPYTHON=1, PYTHONFRAMEWORK='', EXT_SUFFIX='.so', SOABI='cpython-315',
                  ALT_SOABI='', ABIFLAGS='')
    with patch.object(module.sysconfig, 'get_config_var', side_effect=values.get), \
         patch.object(module.sysconfig, 'get_path', return_value='/usr/pkg/bin'), \
         patch.object(module.sysconfig, 'get_platform', return_value='netbsd-aarch64'), \
         patch.object(module.sysconfig, 'get_python_version', return_value='3.15'), \
         patch.dict(os.environ, {'_PYTHON_HOST_PLATFORM': 'netbsd-aarch64',
                                'PYTHON_BUILD_DETAILS_PLATFORM': 'netbsd-11.0-evbarm'}):
        data = module.generate_data('1.0')
        require(data['language']['version_info']['micro'] == 199, 'host language version leaked')
        require(data['implementation']['version']['micro'] == 199, 'host implementation version leaked')
        require(data['platform'] == 'netbsd-11.0-evbarm', 'host platform leaked')
        require(data['suffixes']['extensions'] == ['.cpython-315.so', '.abi3.so', '.so'], 'wrong target suffixes')
        require(data['abi']['stable_abi_suffix'] == '.abi3.so', 'wrong stable ABI suffix')
        require(data['libpython']['static'] == values['LIBPL'] + '/libpython3.15.a', 'shared static-library path')
        values['LDLIBRARY'] = values['LIBRARY']
        data = module.generate_data('1.0')
        require(data['libpython']['static'] == values['LIBDIR'] + '/libpython3.15.a', 'static-only library path')
        # Native generation must use the interpreter version and suffixes.
        with patch.dict(os.environ, {}, clear=True):
            data = module.generate_data('1.0')
            require(data['implementation']['version']['micro'] == sys.version_info.micro, 'native version changed')
            require(data['suffixes']['extensions'] == module.importlib.machinery.EXTENSION_SUFFIXES, 'native suffixes changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('distfiles', type=Path)
    parser.add_argument('work', type=Path)
    parser.add_argument('--archive', type=Path, help='Check these candidate bytes against the selected recipe')
    parser.add_argument('--pkgsrc', type=Path, help='Use an existing normal export without modifying it')
    args = parser.parse_args()
    args.work.mkdir()
    manifest = (PROFILE / 'sources.tsv').read_text()
    name = next(line.split('\t')[0] for line in manifest.splitlines() if line.startswith('Python-'))
    archive = args.archive or args.distfiles / name
    version = verify_source(RECIPE, manifest, archive)
    for invalid in (manifest.replace(next(l for l in manifest.splitlines(True) if l.startswith('Python-')), ''),
                    manifest + next(l for l in manifest.splitlines(True) if l.startswith('Python-')),
                    manifest.replace('Python-' + version, 'Python-0.0.0'),
                    manifest.replace('https://www.python.org/ftp/python/', 'https://example.invalid/')):
        rejected(lambda: verify_source(RECIPE, invalid, archive), 'source selection')
    fixture = args.work / 'recipe'
    fixture.mkdir()
    for name in ('dist.mk', 'distinfo'):
        shutil.copy2(RECIPE / name, fixture / name)
    info = (fixture / 'distinfo').read_text()
    (fixture / 'distinfo').write_text(re.sub(r'^Size .*$', f'Size ({archive.name}) = 1 bytes', info, flags=re.M))
    rejected(lambda: verify_source(fixture, manifest, archive), 'wrong size')
    (fixture / 'distinfo').write_text(info)
    changed = args.work / archive.name
    shutil.copy2(archive, changed)
    with changed.open('ab') as stream:
        stream.write(b'changed')
    rejected(lambda: verify_source(fixture, manifest, changed), 'changed bytes')
    changed.unlink()
    patches = verify_patches(RECIPE)
    shutil.copytree(RECIPE / 'patches', fixture / 'patches')
    (fixture / 'patches' / patches[0].name).unlink()
    rejected(lambda: verify_patches(fixture), 'missing patch')
    shutil.copy2(patches[0], fixture / 'patches' / patches[0].name)
    with (fixture / 'patches' / patches[0].name).open('ab') as stream:
        stream.write(b'changed\n')
    rejected(lambda: verify_patches(fixture), 'changed patch')
    pristine = args.work / 'pristine'
    with tarfile.open(archive) as source:
        source.extractall(pristine, filter='data')
    pristine = pristine / ('Python-' + version)
    check_plist(pristine)
    patched = args.work / 'patched'
    shutil.copytree(pristine, patched)
    for delta in patches:
        run(['patch', '-f', '-N', '-F', '0', '-p0', '-d', str(patched.resolve())],
            args.work / (delta.name + '.log'), input=delta.read_bytes())
    repeated = subprocess.run(['patch', '-f', '-N', '-F', '0', '-p0', '-d', str(patched.resolve())],
                              input=patches[0].read_bytes(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (args.work / 'repeated-patch.log').write_bytes(repeated.stdout)
    require(repeated.returncode != 0, 'repeated patch accepted')
    env = dict(os.environ, PYTHON_CROSS_TARGETS='aarch64--netbsd aarch64-unknown-netbsd11.0 x86_64--netbsd x86_64-unknown-netbsd11.0')
    run(['sh', str(PROFILE / 'tests/python-cross-configure.sh'), str(pristine.resolve()),
         str(patched.resolve()), str((args.work / 'cross-cases').resolve())], args.work / 'cross-cases.log', env=env)
    source_invariants(patched)
    build_details(patched, args.work)
    exported = args.pkgsrc or args.work / 'pkgsrc'
    if not args.pkgsrc:
        run(['sh', str(ROOT / 'scripts/prepare-pkgsrc.sh'), str(exported.resolve())], args.work / 'export.log')
    for original in RECIPE.rglob('*'):
        if original.is_file():
            require(original.read_bytes() == (exported / 'lang/python315' / original.relative_to(RECIPE)).read_bytes(), 'exported recipe differs')
    require(re.search(r'^PYTHON_VERSION_DEFAULT\?=\s*315$', (exported / 'lang/python/pyversion.mk').read_text(), re.M), 'export selected an old interpreter')
    print('PASS: current Python source URL, SHA256, Size, source-selection negatives and patch checksums')
    print('PASS: zero-fuzz patches, repeat refusal, NetBSD cross cases and target/native build-details')
    print('PASS: PLIST source entries and normal exported recipe; no compilation or runtime acceptance')


if __name__ == '__main__':
    main()
