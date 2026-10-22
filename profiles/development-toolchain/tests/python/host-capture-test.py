#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); host capture streams and frontend ownership.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

PROFILE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROFILE / 'runtime/recipe/files'))
import sdk_source
ARGS = sdk_source.arguments(sys.argv[1:])
sys.path.insert(0, str(PROFILE))
import host
from emberbsd_sdk.errors import CommandError, ProcessOwnershipError, SDKError
from emberbsd_sdk.process import ContextLocks, OwnedProcessGroup

CHILD = '''import sys
from pathlib import Path
sys.dont_write_bytecode = True
profile, sdk, variant, fifo, lease = sys.argv[1:]
sys.path.insert(0, str(Path(profile) / 'runtime/recipe/files'))
import sdk_source
sdk_source.load(sdk)
sdk_source.install_signal_handlers()
sys.path.insert(0, profile)
import host
from emberbsd_sdk.process import ContextLocks
if variant == 'before':
    def raw_capture(argv, **options):
        return host.process.capture(argv, env=host.environment(), **options).stdout.decode('utf-8')
    host.capture = raw_capture
with ContextLocks([lease], str(Path(lease).parent)):
    host.capture(['gcc-16', '-dM', '-E', '-x', 'c', '-', '-include', fifo], input=b'\\n')
'''


class CaptureTest(unittest.TestCase):
    def child(self, source, **options):
        return host.capture([sys.executable, '-c', source], **options)

    def test_exact_success_stdin_cwd_and_ignored_stderr(self):
        source = "import os,sys;data=sys.stdin.buffer.read();sys.stderr.write('diagnostic\\n');print(os.getcwd());print(data.hex())"
        with tempfile.TemporaryDirectory(prefix='gcc-capture-cwd-') as directory:
            cwd=Path(directory).resolve()
            self.assertEqual(self.child(source,cwd=str(cwd),input=b'a\x00b\n'),str(cwd)+'\n6100620a\n')

    def test_exact_nonzero_streams_and_status(self):
        with self.assertRaises(CommandError) as error:
            self.child("import sys;sys.stdout.buffer.write(b'out\\x00\\n');sys.stderr.buffer.write(b'err\\n');sys.exit(7)")
        self.assertEqual((error.exception.returncode,error.exception.stdout,error.exception.stderr),(7,b'out\x00\n',b'err\n'))
        self.assertFalse(error.exception.stdout_truncated or error.exception.stderr_truncated)

    def test_exact_signal_status(self):
        with self.assertRaises(CommandError) as error:
            self.child('import os,signal;os.kill(os.getpid(),signal.SIGTERM)')
        self.assertEqual(error.exception.returncode,-signal.SIGTERM)

    def test_large_valid_stdout(self):
        self.assertEqual(len(self.child("import sys;sys.stdout.write('x'*(2*1024*1024))")),2*1024*1024)

    def test_success_stdout_limit_refuses(self):
        with self.assertRaisesRegex(SDKError,'stdout exceeds'):
            self.child("import sys;sys.stdout.write('x'*(16*1024*1024+1))")

    def test_failed_stdout_limit_refuses(self):
        with self.assertRaisesRegex(SDKError,'stdout exceeds'):
            self.child("import sys;sys.stdout.write('x'*(16*1024*1024+1));sys.exit(9)")

    def test_success_stderr_limit_refuses(self):
        with self.assertRaisesRegex(SDKError,'stderr exceeds'):
            self.child("import sys;sys.stderr.write('e'*(1024*1024+1))")

    def test_failed_stderr_limit_refuses(self):
        with self.assertRaisesRegex(SDKError,'stderr exceeds'):
            self.child("import sys;sys.stderr.write('e'*(1024*1024+1));sys.exit(9)")

    def test_invalid_utf8_keeps_strict_decode(self):
        with self.assertRaises(UnicodeDecodeError):
            self.child("import sys;sys.stdout.buffer.write(b'\\xff')")

    def test_unsupported_apis_refuse_before_launch(self):
        for name in ('PRODUCER_STREAM_API','PRODUCER_INPUT_API'):
            for value in (0,True):
                with self.subTest(api=name,value=value), patch.object(host,name,value), patch.object(host,'capture_streamed') as run:
                    with self.assertRaisesRegex(SDKError,'API1'): self.child('raise SystemExit(97)')
                    run.assert_not_called()

    @unittest.skipUnless(sys.platform in ('darwin','linux'),'Qualified POSIX session backend required')
    def test_actual_blocked_gcc16_preprocessor_drains_before_lock_release(self):
        self.assertIsNotNone(shutil.which('gcc-16'),'Native GCC16 is required for this control')
        root=Path(tempfile.mkdtemp(prefix='gcc-capture-ownership-')).resolve()
        unproven=False
        evidence=[]
        try:
            child=root/'child.py';child.write_text(CHILD)
            for variant in ('before','after'):
                case=root/variant;case.mkdir()
                fifo=case/'hold.h';os.mkfifo(fifo)
                lease=str(case/'output')
                argv=[sys.executable,'-B',str(child),str(PROFILE),sdk_source.load(),variant,str(fifo),lease]
                with (case/'controller.log').open('wb') as log:
                    group=OwnedProcessGroup(argv,cwd=str(case),env=host.environment(),stdout=log,stderr=log)
                    try:
                        group.start()
                        def frontends():
                            rows=subprocess.check_output(['ps','-e','-o','pid=,ppid=,command='],text=True)
                            return [line for line in rows.splitlines() if str(fifo) in line and ('/cc1 ' in line or '/cc1plus ' in line)]
                        deadline=time.monotonic()+30
                        observed=[]
                        while time.monotonic()<deadline and group.poll() is None:
                            observed=frontends()
                            if observed:break
                            time.sleep(.02)
                        self.assertTrue(observed,'Actual GCC16 frontend was not observed: '+variant)
                        os.kill(group.pid,signal.SIGTERM)
                        deadline=time.monotonic()+20
                        while time.monotonic()<deadline and group.poll() is None:time.sleep(.02)
                        self.assertEqual(group.poll(),143)
                        remaining=frontends()
                        with ContextLocks([lease],str(case)):released=True
                        self.assertEqual(bool(remaining),variant=='before')
                        evidence.append({'variant':variant,'argv':argv,'controller_status':group.poll(),
                            'observed_real_frontend':observed,'remaining_at_lock_release':remaining,'lock_released':released})
                    finally:
                        try:
                            group.stop()
                            self.assertFalse(group.alive())
                        except ProcessOwnershipError:
                            unproven=True
                            raise
                fifo.unlink()
            print('Blocked preprocessor ownership: '+json.dumps(evidence),flush=True)
        finally:
            if unproven: print('Retained work after unproven control drainage: '+str(root),file=sys.stderr)
            else: shutil.rmtree(root)


unittest.main(argv=[sys.argv[0]]+ARGS)
