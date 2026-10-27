#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Exercise ordinary pkgsrc phase environments with actual native Rust links."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

PROFILE=Path(__file__).resolve().parents[1]
BINDING='ALL_ENV+= SDKROOT=${OSX_SDK_PATH:Q}\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('pkgsrc','bmake','makeconf','shell','host-prefix','sdk-source','lock-root','link-context','work'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!='darwin':parser.error('this runtime check requires native Darwin')
    if not all(p.is_absolute() for p in vars(args).values()) or args.work.exists():parser.error('select absolute inputs and new work')
    args.work.mkdir(parents=True)
    policy=(PROFILE/'darwin-bootstrap.mk.conf').read_text();assert policy.count(BINDING)==1
    makeconf=args.makeconf.read_text()
    include=re.compile(r'^\.include "[^"\n]*/EMBERBSD-DARWIN-BOOTSTRAP-MK\.CONF"$',re.M)
    assert len(include.findall(makeconf))==1,'use a rendered native MAKECONF with its explicit profile include'
    helper=PROFILE.parent/'common-build-tools/cargo-config.py'
    spec=importlib.util.spec_from_file_location('cargo_config',helper);cargo=importlib.util.module_from_spec(spec);spec.loader.exec_module(cargo)
    prefix=args.host_prefix
    launcher=shlex.join([str(prefix/'bin/python3.15'),'-B',str(args.sdk_source/'scripts/link-launcher.py'),
                        '--lock-root',str(args.lock_root),'--context',str(args.link_context),'--'])
    results=[]
    for case in ('missing-binding','selected-sdk','poisoned-inherited-sdk'):
        root=args.work/case;root.mkdir();config=root/'mk.conf'
        selected=root/'EMBERBSD-DARWIN-BOOTSTRAP-MK.CONF'
        selected.write_text(policy.replace(BINDING,'') if case=='missing-binding' else policy)
        (root/'EMBERBSD-DEVELOPMENT-MK.CONF').symlink_to(args.pkgsrc/'EMBERBSD-DEVELOPMENT-MK.CONF')
        config.write_text(include.sub(lambda match:'.include '+json.dumps(str(selected)),makeconf))
        env=dict(os.environ);env.pop('SDKROOT',None);env.pop('DEVELOPER_DIR',None)
        if case=='poisoned-inherited-sdk':env['SDKROOT']='/unselected-native-sdk'
        names=('OSX_SDK_PATH','MACOSX_DEPLOYMENT_TARGET','MAKE_ENV','CONFIGURE_ENV','TEST_ENV')
        command=[str(args.bmake),'-m',str(prefix/'share/mk'),'SHELL='+str(args.shell),
                 'MAKECONF='+str(config),'EMBERBSD_DARWIN_BOOTSTRAP=yes','WRKOBJDIR='+str(root/'objects')]
        for name in names:command+=['-V','${'+name+'}']
        proc=subprocess.run(command,cwd=args.pkgsrc/'devel/zlib',env=env,capture_output=True,text=True,check=True)
        values=proc.stdout.splitlines();assert len(values)==len(names),(values,proc.stderr)
        sdk,deployment=values[:2]
        phases={name:dict(word.split('=',1) for word in shlex.split(value)) for name,value in zip(names[2:],values[2:])}
        for name,phase in phases.items():
            if case=='missing-binding':assert 'SDKROOT' not in phase,(name,phase.get('SDKROOT'))
            else:assert phase.get('SDKROOT')==sdk,(name,phase.get('SDKROOT'),sdk)
        # Use exactly pkgsrc's ordinary build environment, with no outer SDKROOT.
        buildenv=dict(env,**phases['MAKE_ENV'])
        source=root/'crate';(source/'src').mkdir(parents=True)
        (source/'Cargo.toml').write_text('[package]\nname="native-sdk-environment"\nversion="0.1.0"\nedition="2021"\n')
        (source/'build.rs').write_text('fn main() { println!("cargo:rerun-if-changed=build.rs"); }\n')
        (source/'src/main.rs').write_text('fn main() { println!("ordinary native ABI environment passed"); }\n')
        vendor=root/'vendor';vendor.mkdir()
        flags=['-isysroot',sdk,'-mmacosx-version-min='+deployment,'--start-no-unused-arguments',
               '--ld-path='+str(prefix/'bin/ld64.lld'),'--end-no-unused-arguments']
        cargo_config=root/'cargo/config.toml'
        cargo.configure(config=cargo_config,vendor=vendor,output=root/'out',rustc=prefix/'bin/rustc',
                        shell=args.shell,tool_path=buildenv['PATH'],mode='native',target='',
                        host_cc=shlex.join([str(prefix/'bin/clang'),*flags]),
                        host_cxx=shlex.join([str(prefix/'bin/clang++'),*flags]),host_ar=str(prefix/'bin/llvm-ar'),
                        target_cc='',target_cxx='',target_ar='',host_linker_launcher=launcher)
        runner=[sys.executable,'-B','-I','-S',str(helper),'run','--cargo',str(prefix/'bin/cargo'),
                '--config',str(cargo_config),'--source',str(source),'--']
        lock=subprocess.run(runner+['generate-lockfile','--offline'],env=buildenv,capture_output=True,text=True)
        assert lock.returncode==0,lock.stdout+lock.stderr
        argv=runner+['run','--offline','--locked','--jobs','1','-vv']
        run=subprocess.run(argv,env=buildenv,capture_output=True,text=True)
        output=run.stdout+run.stderr;(root/'cargo.log').write_text(output)
        assert run.returncode==0 and 'ordinary native ABI environment passed' in output,output
        discovery='invoking `"xcrun"' in output
        assert discovery==(case=='missing-binding'),output
        results.append(dict(case=case,phase_sdkroots={key:value.get('SDKROOT') for key,value in phases.items()},
                            argv=argv,exit_code=run.returncode,attempted_ambient_sdk_discovery=discovery))
    (args.work/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Three real pkgsrc phase environments and native Cargo build-script/executable links passed; missing binding reproduced xcrun discovery.')


if __name__=='__main__':main()
