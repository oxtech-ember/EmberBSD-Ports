#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Selected generator bytes invalidate stale gencode regardless of tool mtimes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(sys.argv[1])/'src'))
from emberbsd_sdk import inventory, jsonio
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',owner); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from types import SimpleNamespace
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp).resolve(); work=root/'work'; work.mkdir(); prefix=root/'prefix'; (prefix/'bin').mkdir(parents=True)
    sdkroot=root/'sdk'; sdkroot.mkdir(); sysroot=root/'sysroot'; sysroot.mkdir()
    tool=prefix/'bin/protoc'; tool.write_text('new-compiler'); past=time.time()-30; os.utime(tool,(past,past))
    package=prefix/'pkgdb/p'; package.mkdir(parents=True); metadata=package/'+BUILD_INFO'; metadata.write_text('BUILD_DATE=old')
    opts=SimpleNamespace(work=work,host_prefix=prefix,sdk_source=sdkroot,sysroot=sysroot)
    sdk={'inventory':inventory,'jsonio':jsonio}; values={'emberbsd_protoc':str(tool),'emberbsd_protoc_runtime_inputs':[str(tool),str(metadata)]}; env={}
    old_values={'emberbsd_protoc_runtime_inputs':list(values['emberbsd_protoc_runtime_inputs'])}
    output=work/'generated'; output.write_text('old-generator-output')
    m.protoc_selection(opts,sdk,env,values); descriptor=work/'protoc-selection.json'
    assert m.additive_protoc_selection(old_values,values,work)=={'emberbsd_protoc_runtime_inputs'}
    m.write_protoc_selection(work,sdk,opts.protoc_selection)
    (work/'build.ninja').write_text('rule gen\n  command = cp '+str(tool)+' $out\nbuild generated: gen | protoc-selection.json\n')
    def run(): return subprocess.run([sys.argv[2],'-C',str(work),'generated'],check=True,capture_output=True,text=True).stdout
    assert 'cp ' in run() and output.read_text()=='new-compiler'
    before=(descriptor.stat().st_mtime_ns,output.stat().st_mtime_ns)
    metadata.write_text('BUILD_DATE=new'); values2={'emberbsd_protoc':str(tool),'emberbsd_protoc_runtime_inputs':[str(tool),str(metadata)]}; env2={}
    m.protoc_selection(opts,sdk,env2,values2); m.write_protoc_selection(work,sdk,opts.protoc_selection)
    assert 'no work to do' in run() and before==(descriptor.stat().st_mtime_ns,output.stat().st_mtime_ns)
    tool.write_text('changed-compiler'); os.utime(tool,(past,past)); values3={'emberbsd_protoc':str(tool),'emberbsd_protoc_runtime_inputs':[str(tool),str(metadata)]}; env3={}
    m.protoc_selection(opts,sdk,env3,values3); m.write_protoc_selection(work,sdk,opts.protoc_selection)
    assert 'cp ' in run() and output.read_text()=='changed-compiler'
    other=root/'other-prefix'; (other/'bin').mkdir(parents=True); (other/'bin/protoc').write_text('changed-compiler')
    other_opts=SimpleNamespace(work=work,host_prefix=other,sdk_source=sdkroot,sysroot=sysroot)
    other_values={'emberbsd_protoc':str(other/'bin/protoc'),'emberbsd_protoc_runtime_inputs':[]}; other_env={}
    m.protoc_selection(other_opts,sdk,other_env,other_values)
    assert env3['EMBERBSD_PROTOC_SELECTION_SHA256']==other_env['EMBERBSD_PROTOC_SELECTION_SHA256']
    for label in ('first-runtime','second-runtime'):
        rt=root/label; (rt/'view').mkdir(parents=True); (rt/'view/library.dylib').write_text('same-runtime')
    scoped_digests=[]
    for label in ('first-runtime','second-runtime'):
        rt=root/label
        scoped=SimpleNamespace(work=work,host_prefix=prefix,sdk_source=sdkroot,sysroot=sysroot,
                               host_runtime_root=rt,protoc_runtime_view=rt/'view')
        scoped_values={'emberbsd_protoc':str(tool),'emberbsd_protoc_runtime_inputs':[str(rt/'view/library.dylib')]}
        scoped_env={}; m.protoc_selection(scoped,sdk,scoped_env,scoped_values)
        assert '$PROTOC_RUNTIME_VIEW/library.dylib' in scoped.protoc_selection['files']
        scoped_digests.append(scoped_env['EMBERBSD_PROTOC_SELECTION_SHA256'])
    assert scoped_digests[0]==scoped_digests[1]
    try:
        m.additive_protoc_selection(old_values,{'emberbsd_protoc_runtime_inputs':values['emberbsd_protoc_runtime_inputs']+['/foreign']},work)
    except ValueError:
        pass
    else:
        raise AssertionError('unrelated input change accepted')
print('PASS: selected protoc bytes invalidate stale Ninja output; metadata/no-op/relocation stay stable')
