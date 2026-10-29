#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Prepare acceptance of the installed common Mesa package, without target tools."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tarfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def query(*args):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout.strip()


def elf(path):
    if not Path(path).is_file():
        return False
    with open(path, 'rb') as stream:
        return stream.read(4) == b'\x7fELF'


def render_command(tools, sysroot, arch, source, output):
    target = {'aarch64': 'aarch64', 'x86_64': 'amd64'}[arch]
    mk = tools / 'target.mk'
    family = 'gcc'
    if mk.is_file():
        values = dict(re.findall(r'^_EMBER_TARGET_([A-Z_]+):= (.+)$', mk.read_text(), re.M))
        family = values.get('FAMILY')
        require(family == 'clang' and values.get('TARGET') == target and
                values.get('SYSROOT') == str(sysroot), 'adapter target/sysroot mismatch')
    cc = tools / 'bin' / f'{arch}--netbsd-{family}'
    readelf = tools / 'bin' / f'{arch}--netbsd-readelf'
    require(all(os.access(p, os.X_OK) for p in (cc, readelf)), 'missing cross compiler or ELF inspector')
    prefix = sysroot / 'usr/pkg'
    runtime = '/usr/pkg/gcc16/lib' if family == 'gcc' else '/usr/pkg/llvm/lib'
    flags = [f'--sysroot={sysroot}', f'-B{prefix}/gcc16/lib/gcc/{arch}--netbsd/16.2.0/'] if family == 'gcc' else []
    command = [str(cc), *flags, '-O2', '-std=c11', '-D_NETBSD_SOURCE', '-Wall', '-Wextra', '-Werror',
               f'-I{prefix}/include', str(source), f'-L{prefix}/lib', '-lEGL', '-lGLESv2', '-lgbm',
               f'-Wl,-rpath-link,{prefix}/lib', f'-Wl,-rpath-link,{sysroot}{runtime}',
               '-Wl,-rpath,/usr/pkg/lib', f'-Wl,-rpath,{runtime}', '-o', str(output)]
    return family, cc, readelf, runtime, command


def target_matches(machine, arch):
    return machine in (f'{arch}--netbsd', f'{arch}-unknown-netbsd')


def main(argv):
    require(len(argv) in (6, 7), 'usage: prepare-mesa-package-tests.py CROSS_TOOLS SYSROOT MESA_SOURCE MESA_BUILD MESA_PACKAGE NEW_WORK [LIBDRM_PACKAGE]')
    tools, sysroot, source, build, package = [Path(p).resolve(strict=True) for p in argv[:5]]
    work = Path(argv[5]); require(work.is_absolute() and not work.exists(), 'NEW_WORK must be a new absolute path')
    arch = os.environ.get('EMBERBSD_CROSS_ARCH', 'aarch64')
    require(arch in ('aarch64', 'x86_64'), 'unsupported Mesa target CPU')
    libdrm_package = Path(argv[6]).resolve(strict=True) if len(argv) == 7 else None
    machine = {'aarch64': 183, 'x86_64': 62}[arch]
    owner = Path(__file__).resolve().parent; prefix = sysroot / 'usr/pkg'; bundle = work / 'bundle'
    family, cc, readelf, runtime_dir, command = render_command(tools, sysroot, arch, bundle / 'source/mesa-render.c', bundle / 'bin/mesa-render')
    require(target_matches(query(str(cc), '-dumpmachine'), arch), 'unexpected cross compiler target')
    info = build / 'meson-info'; version = (source/'VERSION').read_text().strip()
    require(json.loads((info/'intro-projectinfo.json').read_text())['version'] == version, 'Mesa source/build version differs')
    options = {o['name']: o['value'] for o in json.loads((info/'intro-buildoptions.json').read_text())}
    for key, value in {'prefix':'/usr/pkg','llvm':'enabled','shared-llvm':'enabled','build-tests':True,'egl':'enabled','gles2':'enabled','glx':'dri'}.items():
        require(options[key] == value, f'unexpected Mesa option {key}')
    drivers = sorted(options['gallium-drivers']); zink = 'zink' in drivers; iris = 'iris' in drivers; radeon = 'radeonsi' in drivers
    require(not (iris or radeon) or arch == 'x86_64', 'Intel/Radeon require amd64')
    require(bool(libdrm_package) == radeon, 'Radeon requires its libdrm package')
    expected = ['llvmpipe','softpipe','virgl'] + (['v3d'] if arch == 'aarch64' else []) + (['zink'] if zink else []) + (['iris'] if iris else []) + (['radeonsi'] if radeon else [])
    require(drivers == sorted(expected) and sorted(options['platforms']) == ['wayland','x11'], 'unexpected drivers/platforms')
    ninja = (build/'build.ninja').read_text()
    require(all(x in ninja for x in ('-DGALLIVM_USE_ORCJIT=1','-DLLVM_IS_SHARED=1','23.1.4')), 'shared LLVM ORC build required')
    inputs = [Path(__file__), owner/'mesa-render.c', owner/'run-mesa-package-tests.sh', cc, readelf, package, source/'VERSION', build/'build.ninja', build/'compile_commands.json'] + [info/n for n in ('intro-projectinfo.json','intro-buildoptions.json','intro-tests.json')]
    if iris:
        inputs.append(source / 'src/intel/decoder/tests/gentest.xml')
    if radeon:
        inputs.append(libdrm_package)
    initial = {str(p):digest(p) for p in inputs}
    for name in ('bin','source','fixtures'): (bundle/name).mkdir(parents=True, exist_ok=True)
    (work/'elf').mkdir(); (bundle/'target-arch.txt').write_text(arch+'\n')
    shutil.copy2(owner/'mesa-render.c', bundle/'source'); shutil.copy2(owner/'run-mesa-package-tests.sh', bundle); (bundle/'run-mesa-package-tests.sh').chmod(0o755)
    payload = {}
    links = {}
    mesa_elfs = []
    contents = None
    seen_entries = set()
    with tarfile.open(package, 'r:gz') as tar:
        for entry in tar:
            raw_name = entry.name
            require(not raw_name.startswith('/') and '..' not in Path(raw_name).parts, f'unsafe package path {raw_name}')
            name = os.path.normpath(raw_name)
            if name == '.' and entry.isdir():
                continue
            require(name not in ('', '.'), f'unsafe package path {raw_name}')
            if name.startswith('+'):
                if name == '+CONTENTS':
                    require(contents is None and entry.isfile(), 'invalid or duplicate +CONTENTS')
                    contents = tar.extractfile(entry).read().decode()
                continue
            if entry.isdir():
                continue
            require(name not in seen_entries, f'duplicate package path: {name}')
            seen_entries.add(name)
            installed = prefix/name
            require(installed.resolve(strict=True).is_relative_to(prefix.resolve()), f'package path escapes prefix: {name}')
            if entry.issym():
                require(installed.is_symlink() and os.readlink(installed) == entry.linkname, f'package link differs: {name}')
                require(installed.resolve(strict=True).is_relative_to(prefix.resolve()), f'package link escapes prefix: {name}')
                links['/usr/pkg/'+name] = entry.linkname
            elif entry.isfile():
                require(installed.is_file() and not installed.is_symlink() and hashlib.sha256(tar.extractfile(entry).read()).hexdigest() == digest(installed), f'package file differs: {name}')
            else: raise ValueError(f'unsupported package entry: {name}')
            payload['/usr/pkg/'+name] = digest(installed)
            if elf(installed): mesa_elfs.append(installed)
    require(contents is not None and len(re.findall(r'^@name (.*)$', contents, re.M)) == 1 and re.fullmatch(r'MesaLib-'+re.escape(version)+r'(?:nb\d+)?', re.findall(r'^@name (.*)$', contents, re.M)[0]) and set(re.findall(r'^@cwd (.*)$', contents, re.M)) == {'/usr/pkg'}, 'package identity/prefix differs')
    (bundle/'source/MesaLib.CONTENTS').write_text(contents)
    if zink:
        require(all(p in payload for p in ('/usr/pkg/lib/dri/zink_dri.so','/usr/pkg/share/drirc.d/00-zink-defaults.conf')) and re.search(r'^@pkgdep vulkan-loader>=1\.4\.357\.0$',contents,re.M), 'Zink package incomplete')
    iris_files = ('/usr/pkg/lib/dri/iris_dri.so','/usr/pkg/share/drirc.d/00-iris-defaults.conf')
    require(all(p in payload for p in iris_files) == iris, 'Iris payload differs')
    require(('/usr/pkg/lib/dri/radeonsi_dri.so' in payload) == radeon and mesa_elfs, 'Radeon payload or Mesa libraries differ')
    (bundle/'mesa-package-files.sha256').write_text(''.join(f'{h}  {p}\n' for p,h in sorted(payload.items())))
    (bundle/'mesa-package-links.tsv').write_text(''.join(f'{p}\t{t}\n' for p,t in sorted(links.items())))
    (work/'render-build.command').write_text(shlex.join(command)+'\n')
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True); (work/'render-build.log').write_text(proc.stdout)
    require(proc.returncode == 0, 'render consumer compile/link failed')
    tests=[]
    for test in json.loads((info/'intro-tests.json').read_text()):
        cmd=test['cmd']; name=test['name']; executable=Path(cmd[0]).name
        if not cmd[0].startswith(str(build)+'/'): continue
        require(elf(cmd[0]), f'missing target test ELF: {name}')
        if name == 'genxml_test':
            require(b'MESA_GENXML_TEST_DIR\0' in Path(cmd[0]).read_bytes(), 'genxml test lacks relocated fixture support')
        require(cmd[1:] == (['-quiet'] if name == 'genxml_test' and iris else []), f'unhandled test arguments: {name}')
        require(all(re.fullmatch(r'[A-Za-z0-9_-]+', x) for x in (name,executable)) and test['workdir'] is None and test['protocol'] in ('exitcode','gtest'), f'unsupported test: {name}')
        expected_env = {'HOME':str(source/'src/util/tests/drirc_home'),'DRIRC_CONFIGDIR':str(source/'src/util/tests/drirc_configdir')} if name == 'xmlconfig' else ({'BUILD_FULL_PATH':cmd[0]} if name == 'process' else ({'BUILD_FULL_PATH':cmd[0],'MESA_PROCESS_NAME':'hello'} if name == 'process_with_overrides' else {}))
        require(test['env'] == expected_env and isinstance(test['timeout'], int) and 1 <= test['timeout'] <= 600, f'unsupported environment/timeout: {name}')
        dest=bundle/'bin'/executable; h=digest(cmd[0]); require(not dest.exists() or digest(dest)==h, f'test basename collision: {executable}')
        initial[cmd[0]]=h; shutil.copy2(cmd[0], dest); tests.append((name,executable,test['timeout']))
    iris_tests='mda_tests intel_device_info_test isl_surf_get_image_offset isl_aux_info isl_tile_std_y isl_tilememcpy isl_surf_get_image_range_B_tile intel_compiler_gen_tests intel_compiler_brw_tests jay_tests intel_compiler_elk_tests genxml_test'.split()
    names=[t[0] for t in tests]; require(sorted(set(names)&set(iris_tests)) == (sorted(iris_tests) if iris else []), 'incomplete Intel test set')
    if radeon:
        required_amd = {'ac_surface_modifier_test', 'ac_surface_meta_address_test', 'ac_nir_tests'}
        require(required_amd.issubset(names), 'incomplete Radeon test set')
    require(len(tests)>=37+(arch=='aarch64')+zink+(len(iris_tests) if iris else 0) and ('zink_format_test' in names)==zink and ('qpu_disasm' in names)==(arch=='aarch64') and sum(n.startswith('lp_test_') for n in names)==7 and 'xmlconfig' in names, 'missing expected upstream tests')
    (bundle/'upstream-tests.tsv').write_text(''.join('\t'.join(map(str,row))+'\n' for row in tests))
    for name in ('drirc_home','drirc_configdir'): shutil.copytree(source/'src/util/tests'/name,bundle/'fixtures'/name)
    if iris:
        (bundle/'fixtures/genxml').mkdir()
        shutil.copy2(source/'src/intel/decoder/tests/gentest.xml', bundle/'fixtures/genxml/gentest.xml')
    runtime={}; seen=set(); queue=mesa_elfs+list((bundle/'bin').iterdir())
    if radeon:
        with tarfile.open(libdrm_package, 'r:gz') as tar:
            members = tar.getmembers()
            contents = [m for m in members if m.name == '+CONTENTS' and m.isfile()]
            ids = [m for m in members if m.name.removeprefix('./') == 'share/libdrm/amdgpu.ids' and m.isfile()]
            require(len(contents) == len(ids) == 1, 'invalid libdrm package inventory')
            metadata = tar.extractfile(contents[0]).read().decode()
            require(re.findall(r'^@name (.*)$', metadata, re.M) == ['libdrm-2.4.134nb8'] and
                    set(re.findall(r'^@cwd (.*)$', metadata, re.M)) == {'/usr/pkg'}, 'unexpected libdrm package identity')
            data = tar.extractfile(ids[0]).read()
        installed_ids = prefix / 'share/libdrm/amdgpu.ids'
        require(installed_ids.is_file() and not installed_ids.is_symlink() and
                hashlib.sha256(data).hexdigest() == digest(installed_ids), 'installed amdgpu.ids differs from libdrm package')
        require('share/libdrm/amdgpu.ids' in metadata.splitlines(), 'libdrm package does not register amdgpu.ids')
        runtime['/usr/pkg/share/libdrm/amdgpu.ids'] = digest(installed_ids)
        (bundle/'source/libdrm.CONTENTS').write_text(metadata)

    if zink:
        loader=prefix/'lib/libvulkan.so.1'; require(loader.is_file(), 'missing Zink loader'); queue.append(loader)
    while queue:
        path=queue.pop(0); real=path.resolve(strict=True)
        require(real.is_relative_to(sysroot) or real.is_relative_to(bundle), 'ELF input escapes sysroot/bundle')
        if path.is_relative_to(prefix):
            require(real.is_relative_to(prefix), 'library symlink escapes target prefix')
            for item in (path,real): runtime['/'+str(item.relative_to(sysroot))]=digest(item)
        if real in seen: continue
        seen.add(real)
        with real.open('rb') as stream:
            header = stream.read(20)
        require(len(header)==20 and header[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',header,16)[0] in (2,3) and struct.unpack_from('<H',header,18)[0]==machine, f'wrong target ELF: {real}')
        dynamic=query(str(readelf),'-d',str(real)); (work/'elf'/(hashlib.sha256(str(real).encode()).hexdigest()[:16]+'.txt')).write_text(str(real)+'\n'+dynamic+'\n')
        paths=[x for row in re.findall(r'\((?:RUNPATH|RPATH)\).*\[([^]]+)\]',dynamic) for x in row.split(':')]
        allowed=['/usr/pkg/lib',runtime_dir,'/usr/pkg/lib/python3.15/config-3.15','/usr/lib','/lib']+([f'/usr/pkg/gcc16/{arch}--netbsd/lib'] if family=='gcc' else [])
        require(all(x.startswith('/') and os.path.normpath(x) in allowed for x in paths), f'foreign ELF runtime path: {real}')
        for name in re.findall(r'\(NEEDED\).*\[([^]]+)\]',dynamic):
            require(re.fullmatch(r'lib[A-Za-z0-9_.+-]+',name) is not None, f'invalid NEEDED: {name}')
            forbidden = ('libstdc++.so', 'libgcc_s.so') if family == 'clang' else ('libc++.so', 'libc++abi.so', 'libunwind.so')
            require(not name.startswith(forbidden), f'incompatible {family} runtime dependency: {name}')
            dependency=next((sysroot/d.lstrip('/')/name for d in paths+[runtime_dir,'/usr/pkg/lib','/usr/lib','/lib'] if (sysroot/d.lstrip('/')/name).is_file()),None)
            require(dependency is not None, f'unresolved target dependency {name} from {real}'); queue.append(dependency)
    require('/usr/pkg/lib/libLLVM.so.23.1' in runtime, 'missing shared LLVM23 runtime closure')
    (bundle/'runtime-libraries.sha256').write_text(''.join(f'{h}  {p}\n' for p,h in sorted(runtime.items())))
    initial.update({str(sysroot/p.lstrip('/')):h for p,h in runtime.items()})
    for path,h in initial.items(): require(digest(path)==h, f'input changed during preparation: {path}')
    (work/'inputs.sha256').write_text(''.join(f'{h}  {p}\n' for p,h in sorted(initial.items())))
    (bundle/'source/receipt.json').write_text(json.dumps(dict(package_sha256=initial[str(package)], compiler=str(cc), compiler_version=query(str(cc),'--version'), source=str(source),build=str(build),sysroot=str(sysroot),target_arch=arch,options=options,input_sha256=initial,target_invocations=len(tests)),indent=2)+'\n')
    artifacts=sorted(p for p in bundle.rglob('*') if p.is_file()); (bundle/'artifacts.sha256').write_text(''.join(f'{digest(p)}  {p.relative_to(bundle)}\n' for p in artifacts))
    archive=work/'mesa-package-tests.tar.gz'
    with tarfile.open(archive,'w:gz') as tar: tar.add(bundle,arcname='.')
    print(f'{digest(archive)}  {archive}\n{len(tests)} upstream invocations; {len(runtime)} installed library paths; no runtime libraries bundled')


if __name__ == '__main__':
    try: main(sys.argv[1:])
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, tarfile.TarError) as error: sys.exit(str(error))
