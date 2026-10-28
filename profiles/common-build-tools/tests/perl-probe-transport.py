#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). No SSH connection is made by these tests.
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('transport', ROOT / 'pkgsrc/lang/perl5/files/probe-transport.py')
TRANSPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRANSPORT)
CONFIGURE = None


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.previous = Path.cwd()
        self.ssh, self.scp = self.directory / 'ssh', self.directory / 'scp'
        for tool in (self.ssh, self.scp):
            tool.write_text('fixture')
            tool.chmod(0o755)
        self.tools = patch.dict(os.environ, {'EMBERBSD_PERL_SSH': str(self.ssh), 'EMBERBSD_PERL_SCP': str(self.scp)})
        self.tools.start()
        os.chdir(self.directory)
        Path('try').write_bytes(b'probe fixture')
        self.args = argparse.Namespace(host='target.example', user='builder', port=22,
            directory='/private/probes/perl', failure=self.directory / 'failed',
            timeout=60, operation='run', values=['./try'])

    def tearDown(self):
        self.tools.stop()
        os.chdir(self.previous)
        self.temp.cleanup()

    def mock_run(self, codes):
        return patch.object(TRANSPORT.subprocess, 'run', side_effect=[
            subprocess.CompletedProcess([], code) for code in codes])

    def test_explicit_transport_paths_and_nondefault_port(self):
        self.args.port = 2222
        with patch.dict(os.environ, {'EMBERBSD_PERL_SSH': str(self.ssh),
                                     'EMBERBSD_PERL_SCP': str(self.scp)}), self.mock_run([0, 0, 0]) as call:
            self.assertEqual(TRANSPORT.execute(self.args), 0)
        argv = [row.args[0] for row in call.call_args_list]
        self.assertEqual([row[0] for row in argv], [str(self.ssh), str(self.scp), str(self.ssh)])
        self.assertTrue(all('2222' in row for row in argv))
        self.assertEqual(argv[1][argv[1].index('-S') + 1], str(self.ssh))

    def test_explicit_ssh_config_reaches_ssh_and_scp(self):
        config = self.directory / 'ssh_config'
        config.write_text('Host fixture\n')
        with patch.dict(os.environ, {'EMBERBSD_PERL_SSH_CONFIG': str(config)}), self.mock_run([0, 0, 0]) as call:
            self.assertEqual(TRANSPORT.execute(self.args), 0)
        for invocation in call.call_args_list:
            argv = invocation.args[0]
            self.assertEqual(argv[argv.index('-F') + 1], str(config))

    def test_relative_ssh_config_is_rejected(self):
        with patch.dict(os.environ, {'EMBERBSD_PERL_SSH_CONFIG': 'relative'}):
            with patch.object(TRANSPORT.subprocess, 'run') as call:
                with self.assertRaises(TRANSPORT.TransportError):
                    TRANSPORT.execute(self.args)
                call.assert_not_called()

    def test_missing_or_relative_transport_is_rejected(self):
        for ssh in ('', 'ssh'):
            with self.subTest(ssh=ssh), patch.dict(os.environ,
                    {'EMBERBSD_PERL_SSH': ssh, 'EMBERBSD_PERL_SCP': str(self.scp)}):
                with patch.object(TRANSPORT.subprocess, 'run') as call:
                    with self.assertRaises(TRANSPORT.TransportError):
                        TRANSPORT.execute(self.args)
                    call.assert_not_called()

    def test_probe_failure_is_a_feature_result(self):
        with self.mock_run([0, 0, 1]) as call:
            self.assertEqual(TRANSPORT.execute(self.args), 1)
        self.assertFalse(self.args.failure.exists())
        for invocation in call.call_args_list:
            self.assertIn('-oBatchMode=yes', invocation.args[0])
            self.assertLessEqual(invocation.kwargs['timeout'], 60)

    def test_failed_copy_never_runs_probe(self):
        with self.mock_run([0, 1]) as call:
            with self.assertRaises(TRANSPORT.TransportError):
                TRANSPORT.execute(self.args)
        self.assertEqual(call.call_count, 2)

    def test_ssh_failure_is_not_a_feature_result(self):
        with self.mock_run([0, 0, 255]):
            with self.assertRaises(TRANSPORT.TransportError):
                TRANSPORT.execute(self.args)

    def test_timeout_is_transport_failure(self):
        with patch.object(TRANSPORT.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ssh', 60)):
            with self.assertRaises(TRANSPORT.TransportError):
                TRANSPORT.execute(self.args)

    def test_path_escape_and_symlink_are_rejected(self):
        self.args.operation = 'to'
        Path('link').symlink_to('try')
        for value in ('../try', '/etc/passwd', 'link'):
            self.args.values = [value]
            with patch.object(TRANSPORT.subprocess, 'run') as call:
                with self.assertRaises(TRANSPORT.TransportError):
                    TRANSPORT.execute(self.args)
                call.assert_not_called()

    def test_fixture_pipeline_is_scoped(self):
        self.args.values = ['cat tryp.c | ./tryp ']
        with self.mock_run([0]) as call:
            self.assertEqual(TRANSPORT.execute(self.args), 0)
        self.assertEqual(call.call_args.args[0][-1],
            'cd /private/probes/perl && cat tryp.c | ./tryp')

    def test_receive_probe_outputs(self):
        self.args.operation = 'from'
        self.args.values = ['try.out', 'try.ret', './fromtry.out']
        with self.mock_run([0, 0, 0]) as call:
            self.assertEqual(TRANSPORT.execute(self.args), 0)
        self.assertEqual(call.call_count, 3)
        self.assertEqual(call.call_args.args[0][-1], 'fromtry.out')

    def test_receive_rejects_remote_or_option_local_operands(self):
        self.args.operation = 'from'
        for value in ('unintended.invalid:probe.out', '-probe.out', './-probe.out'):
            with self.subTest(value=value):
                self.args.values = [value]
                with self.mock_run([0]) as call:
                    with self.assertRaises(TRANSPORT.TransportError):
                        TRANSPORT.execute(self.args)
                    call.assert_not_called()

    def test_cli_failure_is_sticky(self):
        argv = ['transport', '--host', self.args.host, '--user', self.args.user,
            '--directory', self.args.directory, '--failure', str(self.args.failure),
            'run', '--', './try']
        with patch.object(sys, 'argv', argv), self.mock_run([0, 1]):
            self.assertEqual(TRANSPORT.main(), 255)
        self.assertIn('status 1', self.args.failure.read_text())
        with patch.object(sys, 'argv', argv), patch.object(TRANSPORT.subprocess, 'run') as call:
            self.assertEqual(TRANSPORT.main(), 255)
            call.assert_not_called()
        self.assertIn('status 1', self.args.failure.read_text())


class ConfigureTests(unittest.TestCase):
    def test_generated_wrappers_propagate_failure(self):
        source = CONFIGURE.read_text()
        start = source.index('\t# EmberBSD: retain upstream probes')
        end = source.index('\tif $test ! -f $run; then', start)
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            cross = work / 'Cross'
            cross.mkdir()
            binpath = work / 'bin'
            binpath.mkdir()
            shell = str(Path(sys.executable).parent / 'mksh')
            (binpath / 'ssh').write_text('#!' + shell + '\nexit 255\n')
            (binpath / 'ssh').chmod(0o755)
            (binpath / 'scp').write_text('#!' + shell + '\nexit 255\n')
            (binpath / 'scp').chmod(0o755)
            env = dict(os.environ, test='test', chmod='chmod', targethost='target.example',
                targetuser='builder', targetport='22', targetdir='/private/probes/perl',
                EMBERBSD_PERL_PROBE_SHELL=str(Path(sys.executable).parent / 'mksh'),
                EMBERBSD_PERL_SSH=str(binpath / 'ssh'), EMBERBSD_PERL_SCP=str(binpath / 'scp'),
                EMBERBSD_PERL_PROBE_PYTHON=sys.executable,
                EMBERBSD_PERL_PROBE_TRANSPORT=str(SPEC.origin),
                PATH=str(binpath) + os.pathsep + os.environ['PATH'])
            for name in ('run', 'to', 'from', 'targetmkdir'):
                env[name] = str(cross / name)
            subprocess.run([shell, '-c', source[start:end]], env=env, check=True)
            self.assertEqual((cross / 'run').read_text().splitlines()[0],
                             '#!' + env['EMBERBSD_PERL_PROBE_SHELL'])
            (work / 'try').write_text('fixture')
            result = subprocess.run([cross / 'run', './try'], cwd=work, env=env,
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 255, result.stderr)
            self.assertIn('status 255', (cross / 'transport-failed').read_text())

    def test_actual_nonblocking_fixture_roundtrip(self):
        source = CONFIGURE.read_text()
        start = source.index('\t\techo "$startsh" >mtry')
        end = source.index('\t\tcase $probe_status in', start)
        shell = str(Path(sys.executable).parent / 'mksh')
        setup = '''startsh='#!''' + shell + ''''
to_remote() { for f in "$@"; do cp "$f" remote/; done; }
from_remote() { for f in "$@"; do cp "remote/$f" .; done; }
run_remote() { cp "$1" remote/; (cd remote && "$@"); }
'''
        for cross in (False, True):
            with self.subTest(cross=cross), tempfile.TemporaryDirectory() as directory:
                work = Path(directory)
                (work / 'remote').mkdir()
                (work / 'try').write_text('#!' + shell + '\necho 42\necho 13 >&4\n')
                (work / 'try').chmod(0o755)
                env = dict(os.environ, targethost='target.example' if cross else '',
                    run='run_remote' if cross else '', to='to_remote', **{'from': 'from_remote'})
                subprocess.run([shell, '-c', setup + source[start:end] + '\ntest "$probe_status" = 0'],
                    cwd=work, env=env, check=True)
                self.assertEqual((work / 'try.out').read_text(), '42\n')
                self.assertEqual((work / 'try.err').read_text(), '13\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--configure', type=Path, required=True)
    options, remaining = parser.parse_known_args()
    CONFIGURE = options.configure
    unittest.main(argv=[sys.argv[0], *remaining])
