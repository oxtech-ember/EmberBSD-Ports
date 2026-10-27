#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise Cargo wrappers with the real SDK link lock and observed tool fixtures.

This Darwin process test does not compile Rust/C/C++ or qualify target tools.
It uses its own lock context; the production heavy-link resource is untouched.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

HELPER = Path(__file__).resolve().parents[1] / 'cargo-config.py'
spec = importlib.util.spec_from_file_location('cargo_config', HELPER)
module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('sdk-source','shell','work'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!='darwin':parser.error('the shared link launcher currently supports Darwin')
    if not all(p.is_absolute() for p in vars(args).values()) or args.work.exists():
        parser.error('select absolute inputs and a new work directory')
    script=args.sdk_source/'scripts/link-launcher.py'
    if not script.is_file():parser.error('selected SDK has no link launcher')
    args.work.mkdir(parents=True)
    rustc=args.work/'rustc'
    rustc.write_text('#!'+sys.executable+'\nprint("host: aarch64-apple-darwin")\n');rustc.chmod(0o755)
    driver=args.work/'driver.py'
    driver.write_text('''import pathlib,sys,time
state=pathlib.Path(sys.argv[1])
if '-c' in sys.argv:
    print('compiler wrapper bypassed linker lock')
    raise SystemExit(0)
if '--status' in sys.argv:
    raise SystemExit(29)
active=state/'active'
try: active.mkdir()
except FileExistsError:
    print('concurrent linker entered the shared resource',flush=True)
    raise SystemExit(73)
try:
    deadline=time.monotonic()+15
    while not (state/'release').exists():
        if time.monotonic()>deadline: raise RuntimeError('fixture release timed out')
        time.sleep(.02)
finally: active.rmdir()
''')
    vendor=args.work/'vendor';vendor.mkdir()
    lock=args.work/'locks';lock.mkdir()
    prefix=shlex.join([sys.executable,'-B',str(script),'--lock-root',str(lock),'--context',str(args.work/'shared-context'),'--'])
    results=[]
    for name,selected in (('serialized',prefix),('missing-launcher-control','')):
        root=args.work/name;root.mkdir();state=root/'state';state.mkdir()
        command=shlex.join([sys.executable,str(driver),str(state)])
        config=root/'config.toml'
        module.configure(config=config,vendor=vendor,output=root/'out',rustc=rustc,
                         shell=args.shell,tool_path=str(Path(sys.executable).parent),mode='cross',
                         target='x86_64-unknown-netbsd',host_cc=command,host_cxx=command,
                         host_ar=command,target_cc=command,target_cxx=command,target_ar=command,
                         host_linker_launcher=selected,target_linker_launcher=selected)
        first=None;second=None
        try:
            first=subprocess.Popen([str(root/'cargo-tools/host-linker')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            deadline=time.monotonic()+10
            while not (state/'active').exists():
                if first.poll() is not None:raise AssertionError(first.communicate())
                if time.monotonic()>deadline:raise AssertionError('first linker did not start')
                time.sleep(.02)
            # C compilation must proceed even while a Rust link owns the lock.
            cc=subprocess.run([str(root/'cargo-tools/host-cc'),'-c'],capture_output=True,text=True,timeout=2)
            assert cc.returncode==0 and 'bypassed linker lock' in cc.stdout,(cc.stdout,cc.stderr)
            second=subprocess.Popen([str(root/'cargo-tools/target-linker')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            if selected:
                time.sleep(.3)
                assert second.poll() is None,'second linker bypassed the resource lock'
            else:
                out,err=second.communicate(timeout=5)
                assert second.returncode==73 and 'concurrent linker entered' in out,(out,err)
            (state/'release').touch()
            first_out,first_err=first.communicate(timeout=10)
            second_out,second_err=second.communicate(timeout=10)
            assert first.returncode==0,(first_out,first_err)
            assert second.returncode==(0 if selected else 73),(second_out,second_err)
            (root/'output.log').write_text(first_out+first_err+second_out+second_err)
            result=dict(case=name,first=first.returncode,second=second.returncode,compiler=cc.returncode)
            if selected:
                failure=subprocess.run([str(root/'cargo-tools/host-linker'),'--status'],capture_output=True,text=True,timeout=10)
                assert failure.returncode==29,(failure.stdout,failure.stderr)
                result['linker_failure']=failure.returncode
            results.append(result)
        finally:
            (state/'release').touch()
            for child in (first,second):
                if child is not None and child.poll() is None:
                    child.terminate();child.communicate(timeout=15)
    (args.work/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Shared SDK host/target link serialization, unblocked CC, failure status and missing-launcher concurrent control passed.')


if __name__=='__main__':main()
