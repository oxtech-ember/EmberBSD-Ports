#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Controlled Mesa package fixture; fake compiler/ELF inspector, no target claim."""
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tarfile
import tempfile
from unittest.mock import patch

owner = Path(__file__).resolve().parents[1] / 'cross/prepare-mesa-package-tests.py'
spec = importlib.util.spec_from_file_location('mesa_package_fixture', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
header = b'\x7fELF\x02\x01' + bytes(10) + struct.pack('<HH', 3, 62) + bytes(32)
class Result:
    returncode = 0
    stdout = ''

def fake_run(cmd, **kwargs):
    Path(cmd[cmd.index('-o') + 1]).write_bytes(header)
    return Result()

def fake_query(*cmd):
    if '-dumpmachine' in cmd: return 'x86_64--netbsd'
    if '--version' in cmd: return 'fixture clang'
    return ' 0x00000001 (NEEDED) Shared library: [libLLVM.so.23.1]\n'

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); tools=root/'tools'; (tools/'bin').mkdir(parents=True)
    sysroot=root/'sysroot'; prefix=sysroot/'usr/pkg'; (prefix/'lib/dri').mkdir(parents=True)
    source=root/'source'; build=root/'build'; info=build/'meson-info'; info.mkdir(parents=True)
    for name in ('drirc_home','drirc_configdir'): (source/'src/util/tests'/name).mkdir(parents=True)
    (source/'VERSION').write_text('26.2.5\n')
    (build/'build.ninja').write_text('-DGALLIVM_USE_ORCJIT=1 -DLLVM_IS_SHARED=1 23.1.4')
    (build/'compile_commands.json').write_text('[]')
    (info/'intro-projectinfo.json').write_text(json.dumps({'version':'26.2.5'}))
    opts={'prefix':'/usr/pkg','llvm':'enabled','shared-llvm':'enabled','build-tests':True,'egl':'enabled','gles2':'enabled','glx':'dri','gallium-drivers':['llvmpipe','softpipe','virgl','radeonsi'],'platforms':['wayland','x11']}
    (info/'intro-buildoptions.json').write_text(json.dumps([{'name':k,'value':v} for k,v in opts.items()]))
    names=['lp_test_'+str(i) for i in range(7)]+['xmlconfig']+['case'+str(i) for i in range(29)]+['ac_surface_modifier_test','ac_surface_meta_address_test','ac_nir_tests']
    tests=[]
    for name in names:
        path=build/name; path.write_bytes(header)
        env={'HOME':str(source/'src/util/tests/drirc_home'),'DRIRC_CONFIGDIR':str(source/'src/util/tests/drirc_configdir')} if name=='xmlconfig' else {}
        tests.append(dict(name=name,cmd=[str(path)],workdir=None,protocol='exitcode',env=env,timeout=10))
    (info/'intro-tests.json').write_text(json.dumps(tests))
    (prefix/'lib/dri/radeonsi_dri.so').write_bytes(header); (prefix/'lib/libLLVM.so.23.1').write_bytes(header)
    for name in ('x86_64--netbsd-clang','x86_64--netbsd-readelf'): (tools/'bin'/name).symlink_to('/usr/bin/true')
    (tools/'target.mk').write_text(f'_EMBER_TARGET_FAMILY:= clang\n_EMBER_TARGET_TARGET:= amd64\n_EMBER_TARGET_SYSROOT:= {sysroot}\n')
    package=root/'mesa.tgz'
    def archive(contents, duplicate=False, duplicate_contents=False, escape=False):
        with tarfile.open(package,'w:gz') as tar:
            rootdir = tarfile.TarInfo('./'); rootdir.type = tarfile.DIRTYPE; tar.addfile(rootdir)
            entry=tarfile.TarInfo('+CONTENTS'); data=contents.encode(); entry.size=len(data); tar.addfile(entry,io.BytesIO(data))
            if duplicate_contents: tar.addfile(entry,io.BytesIO(data))
            tar.add(prefix/'lib/dri/radeonsi_dri.so',arcname='lib/dri/radeonsi_dri.so')
            if duplicate: tar.add(prefix/'lib/dri/radeonsi_dri.so',arcname='./lib//dri/radeonsi_dri.so')
            if escape: tar.add(root/'outside/payload.so',arcname='escape/payload.so')
    valid='@name MesaLib-26.2.5nb8\n@cwd /usr/pkg\n'
    os.environ['EMBERBSD_CROSS_ARCH']='x86_64'
    with patch.object(m,'query',side_effect=fake_query), patch.object(m.subprocess,'run',side_effect=fake_run):
        archive(valid); m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'ok')])
        for index,contents,duplicate in ((1,valid,True),(2,valid+'@cwd /elsewhere\n',False),(3,valid.replace('26.2.5','26.2.4'),False),(4,valid+'@name Other-1\n',False)):
            archive(contents,duplicate)
            try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/f'bad{index}')])
            except ValueError: pass
            else: raise AssertionError(f'invalid fixture {index} accepted')
        (root/'outside').mkdir(); (root/'outside/payload.so').write_bytes(header); (prefix/'escape').symlink_to(root/'outside')
        archive(valid, escape=True)
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-escape')])
        except ValueError: pass
        else: raise AssertionError('escaping regular payload accepted')
        archive(valid)
        original_tests = tests[:]
        (info/'intro-tests.json').write_text(json.dumps([t for t in tests if t['name'] != 'ac_nir_tests']))
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-amd')])
        except ValueError as error: assert 'incomplete Radeon test set' in str(error)
        else: raise AssertionError('missing Radeon test accepted')
        (info/'intro-tests.json').write_text(json.dumps(original_tests))
        archive(valid, duplicate_contents=True)
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-contents')])
        except ValueError: pass
        else: raise AssertionError('duplicate metadata accepted')
        archive(valid)
        tests[0]['timeout']=0
        (info/'intro-tests.json').write_text(json.dumps(tests))
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-test')])
        except ValueError: pass
        else: raise AssertionError('invalid test metadata accepted')
        tests[0]['timeout']=10
        (info/'intro-tests.json').write_text(json.dumps(tests))
        def wrong_family(*cmd):
            if '-d' in cmd: return ' (NEEDED) Shared library: [libstdc++.so.7]\n'
            return fake_query(*cmd)
        with patch.object(m,'query',side_effect=wrong_family):
            try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-family')])
            except ValueError: pass
            else: raise AssertionError('GNU dependency accepted for Clang')
print('PASS: controlled Radeon fixture and negative package/version/ABI cases; no target execution')
