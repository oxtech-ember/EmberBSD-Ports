#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Verify immutable SDK compiler bindings with real Ninja and native Clang."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser()
for name in ('host-prefix','sdk-source','macos-sdk'): p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args(); assert sys.platform=='darwin'
path=Path(__file__).resolve().parents[1]/'electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron_build',path);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
sdk=b.load_sdk(a.sdk_source)
native=sdk['host_prefix'].load_host_prefix(a.host_prefix,required_roles=('python','ninja','cc','cxx','cpp'))
assert Path(sys.executable).resolve()==Path(native.tool('python')).resolve()
env=dict(PATH=native.path,HOME=os.environ.get('HOME','/'),LC_ALL='C')
with tempfile.TemporaryDirectory(prefix='binding-invalidation-') as tmp:
    root=Path(tmp);prefix=root/'bindings';src=root/'sample.c';src.write_text('int main(void) { return VALUE; }\n')
    clang=native.tool('cc');linker=str(a.host_prefix/'bin/ld64.lld')
    args=[clang,'-isysroot',str(a.macos_sdk)]
    def record(value):
        return dict(format='emberbsd-compiler-binding',version=1,aliases={},
          commands={'cc':args,'cxx':args,'cpp':args},
          flags={'cppflags':[],'cflags':['-DVALUE='+str(value)],'cxxflags':[],'ldflags':[]},
          link_flags={'cc':['--ld-path='+linker], 'cxx':['--ld-path='+linker]})
    def manifest(binding):
        (root/'build.ninja').write_text('rule cc\n command = '+binding['cc']+' -c sample.c -o sample.o\n description = COMPILE\n'
            'rule link\n command = '+binding['cc']+' sample.o -o sample\n description = LINK\n'
            'build sample.o: cc sample.c\nbuild sample: link sample.o\ndefault sample\n')
    def ninja():
        r=subprocess.run([native.tool('ninja'),'-C',str(root)],env=env,text=True,capture_output=True)
        assert r.returncode==0, r.stdout+r.stderr
        return r.stdout
    first=b.bind_versioned(sdk,native,prefix,record(1));manifest(first)
    output=ninja();assert 'COMPILE' in output and 'LINK' in output,output
    assert subprocess.run([root/'sample']).returncode==1
    assert 'no work to do' in ninja()
    same=b.bind_versioned(sdk,native,prefix,record(1));assert same==first
    second=b.bind_versioned(sdk,native,prefix,record(2));assert first!=second
    manifest(second);output=ninja();assert 'COMPILE' in output and 'LINK' in output,output
    assert subprocess.run([root/'sample']).returncode==2
    assert 'no work to do' in ninja() and Path(first['cc']).is_file()
    changed_link=record(2); changed_link['link_flags']['cc'].append('-Wl,-dead_strip')
    third=b.bind_versioned(sdk,native,prefix,changed_link); assert third != second
    manifest(third);output=ninja();assert 'COMPILE' in output and 'LINK' in output,output
    assert subprocess.run([root/'sample']).returncode==2 and 'no work to do' in ninja()
    config=Path(first['cc']).parent/'commands.json'; config.chmod(0o644); config.write_text('{}')
    try: b.bind_versioned(sdk,native,prefix,record(1)); raise AssertionError('damaged binding accepted')
    except Exception as error: assert 'compiler binding differs' in str(error)
    print('real SDK bindings and Ninja: first build, no-op and changed flags rebuild passed')
