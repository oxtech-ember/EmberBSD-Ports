#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
"""Exercise controller job defaults with the selected SDK resolver."""
import argparse
from contextlib import nullcontext, redirect_stderr
import importlib.util
import io
from pathlib import Path
import sys
from unittest.mock import patch

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-source',type=Path,required=True)
args=parser.parse_args(); sdk=args.sdk_source.resolve(strict=True)
sys.path.insert(0,str(sdk/'src'))
from emberbsd_sdk import cpu_capacity
owner=Path(__file__).resolve().parents[1]/'electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron_build_jobs',owner)
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
class Locks:
    @staticmethod
    def ContextLocks(*args, **kwargs): return nullcontext()
base=[str(owner),'configure']
for key in ('workspace','ports-source','host-prefix','compiler-prefix','sysroot','work','git','lock-root','link-context'):
    base += ['--'+key,'/tmp/electron-jobs-'+key]
base += ['--sdk-source',str(sdk),'--target','amd64']
for extra, expected in [([],11),(['--jobs','3'],3)]:
    selected=[]
    with patch.object(sys,'argv',base+extra), patch.object(b,'load_sdk',return_value={'process':Locks,'cpu_capacity':cpu_capacity}), patch.object(b,'configure',side_effect=lambda options: selected.append(options.jobs)), patch.object(cpu_capacity,'available_cpu_count',return_value=11), patch.object(cpu_capacity,'resolve_jobs',wraps=cpu_capacity.resolve_jobs) as resolver:
        b.main()
    assert selected==[expected] and resolver.call_count==1
for value in ('0','-1','not-an-integer'):
    selected=[]
    with patch.object(sys,'argv',base+['--jobs',value]), patch.object(b,'load_sdk',return_value={'process':Locks,'cpu_capacity':cpu_capacity}), patch.object(b,'configure',side_effect=lambda options: selected.append(options)), redirect_stderr(io.StringIO()):
        try: b.main()
        except SystemExit as error: assert error.code != 0
        else: raise AssertionError('accepted invalid jobs: '+value)
    assert not selected
print('PASS: SDK job default, explicit override and invalid controls')
