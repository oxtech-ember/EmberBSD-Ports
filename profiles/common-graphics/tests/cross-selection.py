#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc cross composition contracts.
"""Check graphics composition with an existing target LLVM metadata helper.

This preserves the complete cross-selection regression. Unlike source-phases.py,
its positive metadata-helper/byte tests require that real prepared input.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc','makeconf','llvm-config','scanner','utility-path','work'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if any(not value.is_absolute() for value in vars(args).values()) or args.work.exists():
        parser.error('use absolute inputs and a new work directory')
    args.work.mkdir()
    prefix=args.scanner.parent.parent
    if not Path(sys.executable).resolve().is_relative_to(prefix.resolve()):
        parser.error('run with the selected native prefix Python')
    config=args.work/'mk.conf'
    config.write_text('.include "'+str(args.makeconf)+'"\n.if defined(BSD_PKG_MK)\n'
        'WRKOBJDIR='+str(args.work/'objects')+'\nEMBERBSD_COMMON_GRAPHICS_CROSS=yes\n'
        'EMBERBSD_GRAPHICS_LLVM_CONFIG='+str(args.llvm_config)+'\nEMBERBSD_WAYLAND_SCANNER='+str(args.scanner)+'\n'
        '.include "'+str(args.pkgsrc/'EMBERBSD-COMMON-GRAPHICS-MK.CONF')+'"\n.endif\n')
    environment=dict(os.environ,PATH=str(args.utility_path))
    make=[str(prefix/'bin/bmake'),'-m',str(prefix/'share/mk'),'SHELL='+str(prefix/'bin/mksh')]
    checks=[]

    def run(name,command,success=True):
        result=subprocess.run([str(item) for item in command],env=environment,capture_output=True,text=True)
        output=result.stdout+result.stderr
        (args.work/(name+'.log')).write_text(output)
        assert (result.returncode==0)==success,name+'\n'+output
        return result.stdout

    def base(package):
        return [*make,'-C',args.pkgsrc/package,'MAKECONF='+str(config)]

    def query(name,command,names,extra=()):
        values=run(name,[*command,*extra,*[part for key in names for part in ('-V','${'+key+'}')]]).splitlines()
        assert len(values)==len(names),values
        return dict(zip(names,values))

    mesa=base('graphics/MesaLib')
    names=['PKG_FAIL_REASON','PREFIX','LOCALBASE','TOOLBASE','TOOL_PYTHONBIN','PYTHONBIN',
        'LLVM_CONFIG_PATH','MESON_BINARY.llvm-config','SUBST_SED.python','MESON_CROSS_FILE',
        'MESON_BINARY.c','MESON_BINARY.cpp','TOOLS_DIGEST','CROSS_MACHINE_ARCH']
    values=query('mesa',mesa,names)
    assert not values['PKG_FAIL_REASON'],values
    assert values['PREFIX']==values['LOCALBASE']=='/usr/pkg'
    assert values['TOOL_PYTHONBIN']==values['TOOLBASE']+'/bin/python3.15'
    assert values['PYTHONBIN']=='/usr/pkg/bin/python3.15' and values['TOOL_PYTHONBIN'] in values['SUBST_SED.python']
    assert values['LLVM_CONFIG_PATH']==values['MESON_BINARY.llvm-config']==str(args.llvm_config)
    run('llvm-input-positive',[*mesa,'emberbsd-graphics-llvm-input-check'])
    checks.append('real Mesa prefix/Python/LLVM selection and consuming-phase input check')
    for package in ('devel/py-mako','textproc/py-markupsafe'):
        native=query(Path(package).name+'-native',base(package),
            ['PKG_FAIL_REASON','OPSYS','LOCALBASE','PKGSRC_COMPILER','EMBERBSD_COMMON_GRAPHICS','LLVM_CONFIG_PATH'],
            ['USE_CROSS_COMPILE=no'])
        assert not native['PKG_FAIL_REASON'] and native['OPSYS']=='Darwin'
        assert native['LOCALBASE']==values['TOOLBASE'] and native['PKGSRC_COMPILER']=='clang'
        assert not native['EMBERBSD_COMMON_GRAPHICS'] and not native['LLVM_CONFIG_PATH']
    checks.append('native Mako and MarkupSafe dependencies retain host configuration')
    Path(values['MESON_CROSS_FILE']).parent.mkdir(parents=True,exist_ok=True)
    run('cross-file',[*mesa,values['MESON_CROSS_FILE']])
    cross=Path(values['MESON_CROSS_FILE']).read_text()
    assert values['CROSS_MACHINE_ARCH'] in ('aarch64','x86_64')
    assert "system = 'netbsd'" in cross and "cpu_family = '"+values['CROSS_MACHINE_ARCH']+"'" in cross
    assert "llvm-config = '"+str(args.llvm_config)+"'" in cross
    checks.append('actual Meson cross file binds selected target metadata')
    for name,override,expected in (
        ('opt-in','EMBERBSD_COMMON_GRAPHICS_CROSS=no','requires EMBERBSD_COMMON_GRAPHICS_CROSS=yes'),
        ('target-prefix','CROSS_LOCALBASE=/opt/mesa','one final /usr/pkg prefix'),
        ('host-python','TOOL_PYTHONBIN=/usr/bin/false','canonical build-host Python'),
        ('base-x11','X11_TYPE=native','requires modular target X11')):
        failure=query(name,mesa,['PKG_FAIL_REASON'],[override])['PKG_FAIL_REASON']
        assert expected in failure,failure
        checks.append(name+' refused')
    # Build-only LLVM input guards now run at their first consuming phase.
    for name,override,expected in (
        ('unprepared-helper','EMBERBSD_GRAPHICS_LLVM_CONFIG=/usr/bin/false','receipt-guarded llvm-config'),
        ('overridden-llvm','LLVM_CONFIG_PATH=/usr/bin/false','overridden LLVM_CONFIG_PATH')):
        run(name,[*mesa,override,'emberbsd-graphics-llvm-input-check'],success=False)
        assert expected in (args.work/(name+'.log')).read_text()
        checks.append(name+' refused before configure')
    drm=base('x11/libdrm')
    metadata=query('libdrm',drm,['PKG_FAIL_REASON','MESON_BINARY.python','REPLACE.tool-python.new','MESON_CROSS_FILE'])
    assert not metadata['PKG_FAIL_REASON'],metadata
    assert metadata['MESON_BINARY.python']==metadata['REPLACE.tool-python.new']==values['TOOL_PYTHONBIN']
    Path(metadata['MESON_CROSS_FILE']).parent.mkdir(parents=True,exist_ok=True)
    run('drm-cross-file',[*drm,metadata['MESON_CROSS_FILE']])
    assert "python = '"+values['TOOL_PYTHONBIN']+"'" in Path(metadata['MESON_CROSS_FILE']).read_text()
    checks.append('actual libdrm native Python binding')
    # Run the existing byte verifier independently of later library/API checks.
    recipe=(args.pkgsrc/'graphics/MesaLib/Makefile').read_text()
    match=re.search(r'^\tcd \$\{LLVM_CONFIG_PATH:H:H:Q\} && \\\n.*?^\tdone < inputs.sha256\n',recipe,re.M|re.S)
    assert match,'missing production LLVM receipt verifier'
    guard=args.work/'guard.mk'
    guard.write_text('TEST=test\nTOOLS_DIGEST='+values['TOOLS_DIGEST']+'\nLLVM_CONFIG_PATH='+str(args.llvm_config)+'\nverify:\n'+match[0])
    clone=args.work/'changed-helper'
    shutil.copytree(args.llvm_config.parent.parent,clone)
    with (clone/'bin/llvm-config.real').open('ab') as stream:stream.write(b'changed executable\n')
    command=[*make,'-r','-f',guard,'verify']
    run('receipt-positive',command)
    run('receipt-negative',[*command,'LLVM_CONFIG_PATH='+str(clone/'bin/llvm-config')],success=False)
    assert 'LLVM helper receipt mismatch: bin/llvm-config.real' in (args.work/'receipt-negative.log').read_text()
    checks.append('unchanged production byte verifier rejects modified real helper')
    summary={'passed':checks,'scope':'actual pkgsrc and machine-file contracts; full target Mesa build/runtime remains separate'}
    (args.work/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':
    main()
