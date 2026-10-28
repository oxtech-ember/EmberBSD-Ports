#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Test selected metadata Git with actual source scripts and real Git worktrees."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser()
for name in ('source', 'git', 'host-prefix'): p.add_argument('--'+name, type=Path, required=True)
a=p.parse_args(); patch=Path(__file__).resolve().parents[1]/'patches/explicit-control-git.patch'
assert all(x.is_absolute() for x in (a.source,a.git,a.host_prefix))
def run(argv, cwd, env, *, success=True):
    r=subprocess.run([str(x) for x in argv],cwd=cwd,env=env,text=True,capture_output=True)
    assert (r.returncode==0)==success, (argv,r.stdout,r.stderr)
    return r.stdout.strip()
base_env=dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
              GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
              GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid')
with tempfile.TemporaryDirectory(prefix='electron-control-git-') as temp:
    src=Path(temp)/'src'; src.mkdir()
    for file in ('build/util/lastchange.py','electron/script/get-git-ref-paths.py','electron/script/get-git-version.py'):
        prefix='electron/' if file.startswith('electron/') else ''
        data=subprocess.check_output([str(a.git),'-C',str(a.source/prefix),'show','HEAD:'+file.removeprefix(prefix)])
        dest=src/file; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
    run([a.git,'apply','--check',patch],src,base_env);run([a.git,'apply',patch],src,base_env)
    (src/'third_party').mkdir(); (src/'third_party/depot_tools').symlink_to(a.source/'third_party/depot_tools',target_is_directory=True)
    run([a.git,'init','-q'],src,base_env);run([a.git,'add','build/util/lastchange.py'],src,base_env)
    run([a.git,'commit','-qm','fixture\n\nChange-Id: Iabc'],src,base_env)
    electron=src/'electron';run([a.git,'init','-q'],electron,base_env)
    run([a.git,'add','script'],electron,base_env);run([a.git,'commit','-qm','fixture'],electron,base_env)
    run([a.git,'tag','v44.0.0'],electron,base_env)
    linked=Path(temp)/'linked';run([a.git,'worktree','add','-q','--detach',linked],electron,base_env)
    selected=dict(base_env,PATH=str(a.host_prefix/'bin'),EMBERBSD_CONTROL_GIT=str(a.git))
    fallback=dict(base_env,PATH=str(a.git.parent));fallback.pop('EMBERBSD_CONTROL_GIT',None)
    for tree in (electron,linked):
        ref=tree/'script/get-git-ref-paths.py'; version=tree/'script/get-git-version.py'
        expected=run([a.git,'rev-parse','--git-dir'],tree,base_env)
        expected=Path(expected) if Path(expected).is_absolute() else tree/expected
        for env in (selected,fallback):
            lines=run([sys.executable,ref],tree,env).splitlines()
            assert Path(lines[1]).resolve()==(expected/'HEAD').resolve()
            assert run([sys.executable,version],tree,env)=='44.0.0'
        missing=dict(selected,EMBERBSD_CONTROL_GIT=str(Path(temp)/'missing-git'))
        run([sys.executable,ref],tree,missing,success=False)
        run([sys.executable,version],tree,missing,success=False)
    rev=run([a.git,'rev-parse','HEAD'],src,base_env)
    script=src/'build/util/lastchange.py'
    for env in (selected,fallback):
        output=run([sys.executable,script,'--print-only','--revision-id-only','-s',src],src,env)
        assert output==rev, (output,rev)
    run([sys.executable,script,'--print-only','--revision-id-only','-s',src],src,missing,success=False)
    print('selected and fallback Git, unavailable Git, checkout, worktree and lastchange passed')
