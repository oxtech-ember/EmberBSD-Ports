#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the selected Mesa version-script ABI with GNU ld and LLD."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mesa_test_source import selected, patch, extract

if len(sys.argv) != 9:
    raise SystemExit('Usage: run.py MESA_ARCHIVE CLANG TARGET_TOOLS SYSROOT LLD MESON NINJA NEW_OUTPUT')
archive, distname, info, digest = selected(sys.argv[1])
cc, tools, sysroot, lld, meson, ninja = [Path(x).resolve(strict=True) for x in sys.argv[2:8]]
work = Path(sys.argv[8])
if not work.is_absolute() or work.exists():
    raise SystemExit('Use a new absolute output directory')
patch_tool = os.environ.get('PATCH')
if not patch_tool or not Path(patch_tool).is_absolute():
    raise SystemExit('Set PATCH to the selected absolute native tool')
version = distname.removeprefix('mesa-')
soname = 'libgallium-' + version + '.so'
work.mkdir()

def run(command, log, cwd=None):
    argv = [str(x) for x in command]
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    log.write_text(shlex.join(argv) + '\n' + result.stdout + result.stderr + '\nexit=' + str(result.returncode) + '\n')
    if result.returncode:
        raise RuntimeError('Command failed: ' + str(log))
    return result.stdout

paths = ('src/gallium/targets/dri/meson.build', 'src/gallium/targets/dri/dri.sym.in')
for name in paths:
    data = extract(archive, distname, name)
    for variant in ('baseline', 'fixed'):
        target = work / variant / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    patch_name = 'patch-' + name.replace('_', '__').replace('/', '_')
    run([patch_tool, '-p0', '-i', patch(info, patch_name)], work / ('patch-' + Path(name).name + '.log'), cwd=work / 'fixed')
readelf = tools / 'bin/aarch64--netbsd-readelf'
common_flags = ['--target=aarch64--netbsd', '--sysroot=' + str(sysroot), '-Wl,-m,aarch64elf']
gnu_ld = tools / 'bin/aarch64--netbsd-ld'
receipt = {'source_sha512': digest, 'variants': {}}
for variant, linker in itertools.product(('baseline', 'fixed'), ('gnu', 'lld')):
    directory = work / (variant + '-' + linker)
    directory.mkdir()
    script = (work / variant / paths[0]).read_text().split('libgallium_dri = shared_library(', 1)[0]
    if 'dri_sym = configure_file(' not in script:
        raise ValueError('Missing actual Meson prefix')
    symmap = (work / variant / paths[1]).read_text()
    settings = '\n'.join("sym_config.set('%s', '')" % key for key in dict.fromkeys(re.findall(r'@([A-Za-z_][A-Za-z_0-9]*)@', symmap)))
    (directory / 'dri.sym.in').write_text(symmap)
    symbols = re.findall(r'^\s*([A-Za-z_][A-Za-z_0-9]*);\s*$', symmap, re.M)
    tls = {'_mesa_glapi_tls_Context', '_mesa_glapi_tls_Dispatch'}
    (directory / 'stub.c').write_text('\n'.join('_Thread_local void *%s;' % name if name in tls else 'int %s(void) { return 42; }' % name for name in symbols) + '\n')
    (directory / 'meson_options.txt').write_text("option('unversion-libgallium', type: 'boolean', value: false)\n")
    (directory / 'meson.build').write_text("project('mesa-version-contract', 'c', version: '%s')\ncc = meson.get_compiler('c')\nsym_config = configuration_data()\n%s\nwith_gallium_va = false\nwith_platform_android = false\nwith_glx_read_only_text = true\nwith_ld_version_script = true\nwith_ld_dynamic_list = false\n%s\nshared_library(libgallium_name, 'stub.c', link_args: gallium_dri_ld_args, link_depends: gallium_dri_link_depends)\n" % (version, settings, script))
    compiler = [str(cc), *common_flags, '--ld-path=' + str(lld if linker == 'lld' else gnu_ld)]
    quote = lambda value: "'" + str(value).replace('\\', '\\\\').replace("'", "\\'") + "'"
    (directory / 'cross.ini').write_text("[binaries]\nc = [%s]\nar = %s\nstrip = %s\n[host_machine]\nsystem = 'netbsd'\ncpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n[properties]\nneeds_exe_wrapper = true\n" % (', '.join(map(quote, compiler)), quote(tools / 'bin/aarch64--netbsd-ar'), quote(tools / 'bin/aarch64--netbsd-strip')))
    run([meson, 'setup', directory / 'build', directory, '--cross-file', directory / 'cross.ini'], directory / 'configure.log')
    run([ninja, '-C', directory / 'build'], directory / 'build.log')
    library = directory / 'build' / soname
    versions = run([readelf, '--version-info', '--wide', library], directory / 'versions.log')
    exports = run([readelf, '--dyn-syms', '--wide', library], directory / 'exports.log')
    node = 'Name: ' + soname in versions
    versioned = all(name + '@@' + soname in exports for name in symbols)
    expected = variant == 'fixed' or linker == 'gnu'
    if node != expected or versioned != expected:
        raise AssertionError('Wrong causal result ' + variant + '/' + linker)
    with library.open('rb') as stream:
        library_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    receipt['variants'][variant + '-' + linker] = dict(default_version_node=node, all_exports_versioned=versioned,
                                                        library_sha256=library_digest)
consumer = work / 'consumer.c'
consumer.write_text('extern int _mesa_glapi_get_dispatch_table_size(void);\nint main(void) { return _mesa_glapi_get_dispatch_table_size() == 42 ? 0 : 1; }\n')
elf = work / 'old-consumer'
run([cc, *common_flags, '--ld-path=' + str(lld), consumer, work / 'baseline-gnu/build' / soname,
     '-Wl,-rpath,/usr/pkg/lib', '-Wl,--dynamic-linker,/libexec/ld.elf_so', '-o', elf], work / 'consumer-build.log')
need = run([readelf, '--version-info', '--wide', elf], work / 'consumer-versions.log')
imports = run([readelf, '--dyn-syms', '--wide', elf], work / 'consumer-imports.log')
if 'File: ' + soname not in need or 'Name: ' + soname not in need or '_mesa_glapi_get_dispatch_table_size@' + soname not in imports:
    raise AssertionError('Old consumer lacks explicit version requirement')
with elf.open('rb') as stream:
    consumer_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
receipt['consumer'] = dict(sha256=consumer_digest,
                           old_gnu_verneed=soname, fixed_lld_verdef_matches=True, target_execution='NOT RUN')
receipt['scope'] = 'Actual Mesa Meson prefix and symbol map; cross ELF ABI contract. No physical runtime claim.'
(work / 'results.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('PASS: GNU default ABI retained under GNU and LLD; old consumer has matching VERNEED')
