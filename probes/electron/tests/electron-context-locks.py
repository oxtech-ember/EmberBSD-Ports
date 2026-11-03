#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
"""Check canonical lock keys through the controller and real SDK locks."""
import argparse
import importlib.util
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk-source',type=Path,required=True)
a=p.parse_args()
owner=Path(__file__).resolve().parents[1]/'electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron_build',owner)
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
sdk=a.sdk_source.resolve(strict=True)
sys.path.insert(0,str(sdk/'src'))
from emberbsd_sdk import process
with tempfile.TemporaryDirectory(prefix='electron-context-lock-') as temp:
    root=Path(temp).resolve(); real=root/'real'; real.mkdir(); (real/'parent').mkdir(); (real/'workspace').mkdir()
    alias=root/'alias'; alias.symlink_to(real, target_is_directory=True)
    locks=root/'locks'; locks.mkdir()
    workspace=alias/'parent/../workspace'; work=alias/'parent/../new-work'
    canonical_workspace=real/'workspace'; canonical_work=real/'new-work'
    assert not canonical_work.exists()
    assert b.context_keys(workspace,canonical_workspace,work,canonical_work)==sorted([str(canonical_workspace),str(canonical_work)])
    captured=[]
    def configure(options):
        captured.append(options)
        assert options.workspace == workspace and options.work == work
        assert not canonical_work.exists()
        for contender in (canonical_workspace,canonical_work):
            try:
                with process.ContextLocks([str(contender)],str(locks)):
                    raise AssertionError('conflicting context acquired')
            except process.SDKError as error:
                assert 'object context is busy' in str(error)
    argv=[str(owner),'configure','--workspace',str(workspace),'--work',str(work),
          '--ports-source',str(canonical_workspace),'--sdk-source',str(sdk),
          '--host-prefix',str(root/'prefix'),'--compiler-prefix',str(root/'compiler'),
          '--sysroot',str(root/'sysroot'),'--git',str(root/'git'),
          '--lock-root',str(locks),'--link-context',str(root/'link'), '--target','amd64']
    with patch.object(sys,'argv',argv), patch.object(b,'load_sdk',return_value={'process':process}), patch.object(b,'configure',side_effect=configure):
        b.main()
    assert len(captured)==1 and not canonical_work.exists()
    with process.ContextLocks([str(canonical_workspace),str(canonical_work)],str(locks)):
        pass
print('PASS: canonical alias lock conflicts, new work and unchanged CLI paths')
