#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted); not submitted upstream.
"""Exercise pkgsrc producer bindings with bmake and an isolated controller."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--bmake', required=True, type=Path)
a = p.parse_args()
bmake = a.bmake.resolve(strict=True)
owner = Path(__file__).resolve().parents[1]/'../../pkgsrc/devel/electron44'
main = (owner/'Makefile').read_text()
assert 'DISTFILES=' in main and 'WRKSRC=' in main and 'do-patch:' in main
assert '.include "producer.mk"' in main
with tempfile.TemporaryDirectory(prefix='electron-package-phases-') as temp:
    root=Path(temp); files=root/'fixture files'; files.mkdir()
    shutil.copyfile(owner/'producer.mk',root/'producer.mk')
    (files/'build-electron.py').write_text('''import json, os, pathlib, sys
args=sys.argv[1:]
with open(os.environ['PHASE_RECORD'],'a') as f: f.write(json.dumps(args)+'\\n')
if args[0] == 'configure':
    work=pathlib.Path(args[args.index('--work')+1]); work.mkdir(); (work/'configuration.json').write_text('fixture')
if args[0] == 'build' and os.environ.get('FAIL_BUILD') == '1': sys.exit(27)
''')
    (files/'install-runtime.py').write_text('''import json,os,sys
with open(os.environ['PHASE_RECORD'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
if sys.argv[1] == 'plist': print('bin/electron')
''')
    (root/'Makefile').write_text('''RUN = @
TEST = /bin/test
ERROR_MSG = /bin/echo
FAIL_MSG = /bin/false
FILESDIR = @FILES@
DESTDIR = @DEST@
PREFIX = /usr/pkg
.include "producer.mk"
plist-fixture:
\t@${GENERATE_PLIST}
'''.replace('@FILES@',str(files)).replace('@DEST@',str(root/'package dest')))
    record=root/'argv.jsonl'; work=root/'producer work'
    variables={'WORKSPACE':str(root/'prepared workspace'), 'PORTS_SOURCE':str(root/'ports source'),
      'SDK_SOURCE':str(root/'sdk source'), 'HOST_PREFIX':str(root/'host prefix'),
      'PYTHON':sys.executable,'COMPILER_PREFIX':str(root/'compiler prefix'),
      'SYSROOT':str(root/'target sysroot'),'WORK':str(work),'GIT':str(root/'git tool'),
      'LOCK_ROOT':str(root/'locks root'),'LINK_CONTEXT':str(root/'link context'),
      'TARGET':'amd64','JOBS':'3','NODE_SOURCE':str(root/'node source'),
      'NODE_PKGSRC':str(root/'node pkgsrc'),'V8_SOURCE':str(root/'v8 source'),
      'V8_PORTS_SOURCE':str(root/'v8 ports'),'V8_PKGSRC':str(root/'v8 pkgsrc'),
      'MACOS_SDK':str(root/'mac sdk'),'COMPILER_FAMILY':'clang','MACOS_MINIMUM':'15.0',
      'KEEP_GOING':'0'}
    for provider in ('PROTOBUF','PERFETTO'):
        for name in ('SOURCE','PORTS_SOURCE','ARCHIVE','PATCH'):
            variables[provider+'_'+name]=str(root/(provider.lower()+' '+name.lower()))
    ml_keys = ('ML_RUY_SOURCE','ML_PTHREADPOOL_SOURCE','ML_GEMMLOWP_SOURCE','ML_FARMHASH_SOURCE',
               'ML_ML_DTYPES_SOURCE','ML_NEON2SSE_SOURCE','ML_FXDIV_SOURCE','ML_FFT2D_SOURCE',
               'ML_LITERT_SOURCE','ML_OPENXLA_SOURCE','ML_PATCH','ML_PKGSRC_EXPORT','ML_PORTS_SOURCE','ML_EXPORT_PATCH',
               'ML_RUY_ARCHIVE','ML_PTHREADPOOL_ARCHIVE','ML_GEMMLOWP_ARCHIVE','ML_FARMHASH_ARCHIVE',
               'ML_ML_DTYPES_ARCHIVE','ML_NEON2SSE_ARCHIVE','ML_FXDIV_ARCHIVE','ML_FFT2D_ARCHIVE',
               'ML_LITERT_ARCHIVE','ML_OPENXLA_ARCHIVE', 'BORINGSSL_SOURCE', 'BORINGSSL_ARCHIVE',
               'ML_LITERT_PORTS_SOURCE')
    variables.update({key:str(root/key.lower()) for key in ml_keys})
    env=dict(os.environ,PHASE_RECORD=str(record))
    env.pop('MAKE_JOBS',None)
    def run(target, values=variables, **extra):
        cmd=[str(bmake),'-f',str(root/'Makefile'),target]
        cmd += ['EMBERBSD_ELECTRON_'+k+'='+v for k,v in values.items()]
        return subprocess.run(cmd,cwd=root,env=dict(env,**extra),text=True,capture_output=True)
    def rows():
        return [json.loads(x) for x in record.read_text().splitlines()] if record.exists() else []
    def expected(phase):
        order=('WORKSPACE','PORTS_SOURCE','SDK_SOURCE','HOST_PREFIX','COMPILER_PREFIX','SYSROOT','WORK','GIT','LOCK_ROOT','LINK_CONTEXT','TARGET','NODE_SOURCE','NODE_PKGSRC','V8_SOURCE','V8_PORTS_SOURCE','V8_PKGSRC')
        result=[phase]
        for key in order: result += ['--'+key.lower().replace('_','-'),variables[key]]
        result += ['--jobs', variables['JOBS']]
        # These appear in the source-defined optional mapping order.
        for key in ('COMPILER_FAMILY','MACOS_SDK','PROTOBUF_SOURCE','PROTOBUF_PORTS_SOURCE',
                    'PROTOBUF_ARCHIVE','PROTOBUF_PATCH','PERFETTO_SOURCE','PERFETTO_PORTS_SOURCE',
                    'PERFETTO_ARCHIVE','PERFETTO_PATCH','MACOS_MINIMUM',*ml_keys):
            result += ['--'+key.lower().replace('_','-'),variables[key]]
        result += ['--shared-undici','--shared-abseil','--shared-icu','--shared-re2']
        if phase=='build': result += ['--keep-going','0']
        return result
    for name in ('NODE_SOURCE','PROTOBUF_SOURCE','PROTOBUF_ARCHIVE','PERFETTO_SOURCE','ML_RUY_SOURCE'):
        missing=dict(variables); del missing[name]
        r=run('do-configure',missing); assert r.returncode!=0 and not rows(), (r.stdout,r.stderr)
    for name in ('SHARED_UNDICI','SHARED_ABSEIL','SHARED_ICU','SHARED_RE2'):
        disabled=dict(variables,**{name:'no'})
        r=run('do-configure',disabled)
        assert r.returncode!=0 and not rows() and 'common Ports provider' in r.stderr, (r.stdout,r.stderr)
    r=run('do-configure'); assert r.returncode==0,(r.stdout,r.stderr)
    assert rows()==[expected('configure')], rows()
    r=run('do-configure'); assert r.returncode==0 and len(rows())==1,(r.stdout,r.stderr,rows())
    r=run('do-build'); assert r.returncode==0,(r.stdout,r.stderr)
    assert rows()[-1]==expected('build'), rows()[-1]
    assert '--keep-going' not in rows()[0]
    no_jobs=dict(variables); del no_jobs['JOBS']
    r=run('do-build',no_jobs); assert r.returncode==0 and '--jobs' not in rows()[-1],(r.stdout,r.stderr,rows()[-1])
    fallback_cmd=[str(bmake),'-f',str(root/'Makefile'),'do-build','MAKE_JOBS=7']
    fallback_cmd += ['EMBERBSD_ELECTRON_'+k+'='+v for k,v in no_jobs.items()]
    r=subprocess.run(fallback_cmd,cwd=root,env=env,text=True,capture_output=True)
    assert r.returncode==0 and rows()[-1][rows()[-1].index('--jobs')+1]=='7',(r.stdout,r.stderr,rows()[-1])
    r=run('do-build',FAIL_BUILD='1'); assert r.returncode!=0,(r.stdout,r.stderr)
    assert rows()[-1]==expected('build')
    expected_install=['--sdk-source',variables['SDK_SOURCE'],'--work',variables['WORK'],
                      '--destdir',str(root/'package dest'),'--prefix','/usr/pkg',
                      '--target','amd64','--lock-root',variables['LOCK_ROOT']]
    r=run('do-install'); assert r.returncode==0,(r.stdout,r.stderr)
    assert rows()[-1]==['install',*expected_install],rows()[-1]
    r=run('plist-fixture'); assert r.returncode==0 and r.stdout.strip()=='bin/electron',(r.stdout,r.stderr)
    assert rows()[-1]==['plist',*expected_install],rows()[-1]
    (work/'configuration.json').unlink()
    before=rows(); r=run('do-configure'); assert r.returncode!=0 and rows()==before,(r.stdout,r.stderr)
    assert work.is_dir() and not (work/'configuration.json').exists()
print('PASS: bmake producer phases, argv quoting, input guards, reuse and failures')
