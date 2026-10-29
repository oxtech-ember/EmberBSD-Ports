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
    libdrm=root/'libdrm.tgz'
    ids=prefix/'share/libdrm/amdgpu.ids'; ids.parent.mkdir(parents=True); ids.write_text('Radeon IDs fixture')
    with tarfile.open(libdrm,'w:gz') as tar:
        contents=b'@name libdrm-2.4.134nb8\n@cwd /usr/pkg\nshare/libdrm/amdgpu.ids\n'
        meta=tarfile.TarInfo('+CONTENTS'); meta.size=len(contents); tar.addfile(meta,io.BytesIO(contents))
        tar.add(ids,arcname='share/libdrm/amdgpu.ids')
    def archive(contents, duplicate=False, duplicate_contents=False, escape=False, iris=False):
        with tarfile.open(package,'w:gz') as tar:
            rootdir = tarfile.TarInfo('./'); rootdir.type = tarfile.DIRTYPE; tar.addfile(rootdir)
            entry=tarfile.TarInfo('+CONTENTS'); data=contents.encode(); entry.size=len(data); tar.addfile(entry,io.BytesIO(data))
            if duplicate_contents: tar.addfile(entry,io.BytesIO(data))
            tar.add(prefix/'lib/dri/radeonsi_dri.so',arcname='lib/dri/radeonsi_dri.so')
            if duplicate: tar.add(prefix/'lib/dri/radeonsi_dri.so',arcname='./lib//dri/radeonsi_dri.so')
            if escape: tar.add(root/'outside/payload.so',arcname='escape/payload.so')
            if iris:
                tar.add(prefix/'lib/dri/iris_dri.so', arcname='lib/dri/iris_dri.so')
                tar.add(prefix/'share/drirc.d/00-iris-defaults.conf', arcname='share/drirc.d/00-iris-defaults.conf')
    valid='@name MesaLib-26.2.5nb8\n@cwd /usr/pkg\n'
    os.environ['EMBERBSD_CROSS_ARCH']='x86_64'
    with patch.object(m,'query',side_effect=fake_query), patch.object(m.subprocess,'run',side_effect=fake_run):
        archive(valid+'@cwd /usr/pkg\n'); m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'ok'),str(libdrm)])
        for index,contents,duplicate in ((1,valid,True),(2,valid+'@cwd /elsewhere\n',False),(3,valid.replace('26.2.5','26.2.4'),False),(4,valid+'@name Other-1\n',False)):
            archive(contents,duplicate)
            try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/f'bad{index}'),str(libdrm)])
            except ValueError: pass
            else: raise AssertionError(f'invalid fixture {index} accepted')
        (root/'outside').mkdir(); (root/'outside/payload.so').write_bytes(header); (prefix/'escape').symlink_to(root/'outside')
        archive(valid, escape=True)
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-escape'),str(libdrm)])
        except ValueError: pass
        else: raise AssertionError('escaping regular payload accepted')
        archive(valid)
        original_tests = tests[:]
        (info/'intro-tests.json').write_text(json.dumps([t for t in tests if t['name'] != 'ac_nir_tests']))
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-amd'),str(libdrm)])
        except ValueError as error: assert 'incomplete Radeon test set' in str(error)
        else: raise AssertionError('missing Radeon test accepted')
        (info/'intro-tests.json').write_text(json.dumps(original_tests))
        archive(valid, duplicate_contents=True)
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-contents'),str(libdrm)])
        except ValueError: pass
        else: raise AssertionError('duplicate metadata accepted')
        archive(valid)
        tests[0]['timeout']=0
        (info/'intro-tests.json').write_text(json.dumps(tests))
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-test'),str(libdrm)])
        except ValueError: pass
        else: raise AssertionError('invalid test metadata accepted')
        tests[0]['timeout']=10
        (info/'intro-tests.json').write_text(json.dumps(tests))
        def wrong_family(*cmd):
            if '-d' in cmd: return ' (NEEDED) Shared library: [libstdc++.so.7]\n'
            return fake_query(*cmd)
        with patch.object(m,'query',side_effect=wrong_family):
            try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-family'),str(libdrm)])
            except ValueError: pass
            else: raise AssertionError('GNU dependency accepted for Clang')
        # Radeon IDs must match the exact package and cannot be omitted.
        ids.write_text('tampered')
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'bad-ids'),str(libdrm)])
        except ValueError as error: assert 'amdgpu.ids differs' in str(error)
        else: raise AssertionError('changed amdgpu.ids accepted')
        ids.write_text('Radeon IDs fixture')
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'missing-libdrm')])
        except ValueError as error: assert 'Radeon requires' in str(error)
        else: raise AssertionError('missing libdrm package accepted')
        # Actual Intel branch must retain and hash the relocated genxml fixture.
        opts['gallium-drivers'].append('iris')
        (info/'intro-buildoptions.json').write_text(json.dumps([{'name':k,'value':v} for k,v in opts.items()]))
        intel = 'mda_tests intel_device_info_test isl_surf_get_image_offset isl_aux_info isl_tile_std_y isl_tilememcpy isl_surf_get_image_range_B_tile intel_compiler_gen_tests intel_compiler_brw_tests jay_tests intel_compiler_elk_tests genxml_test'.split()
        for name in intel:
            path=build/name; path.write_bytes(header + (b'MESA_GENXML_TEST_DIR\0' if name == 'genxml_test' else b''))
            tests.append(dict(name=name,cmd=[str(path)] + (['-quiet'] if name == 'genxml_test' else []),workdir=None,protocol='exitcode',env={},timeout=10))
        (info/'intro-tests.json').write_text(json.dumps(tests))
        (prefix/'lib/dri/iris_dri.so').write_bytes(header)
        (prefix/'share/drirc.d').mkdir(parents=True)
        (prefix/'share/drirc.d/00-iris-defaults.conf').write_text('fixture')
        xml=source/'src/intel/decoder/tests/gentest.xml'; xml.parent.mkdir(parents=True); xml.write_text('<genxml/>')
        archive(valid, iris=True)
        m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'intel-ok'),str(libdrm)])
        bundle=root/'intel-ok/bundle'
        assert (bundle/'fixtures/genxml/gentest.xml').read_text() == '<genxml/>'
        assert 'fixtures/genxml/gentest.xml' in (bundle/'artifacts.sha256').read_text()
        test_binary=build/'genxml_test'; test_binary.write_bytes(header)
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'intel-old-binary'),str(libdrm)])
        except ValueError as error: assert 'lacks relocated fixture support' in str(error)
        else: raise AssertionError('old Intel binary accepted')
        test_binary.write_bytes(header + b'MESA_GENXML_TEST_DIR\0')
        xml.unlink()
        try: m.main([str(tools),str(sysroot),str(source),str(build),str(package),str(root/'intel-missing'),str(libdrm)])
        except (ValueError, FileNotFoundError): pass
        else: raise AssertionError('missing Intel XML accepted')
print('PASS: Radeon and Intel fixture, relocated XML and negative package/version/ABI cases; no target execution')
