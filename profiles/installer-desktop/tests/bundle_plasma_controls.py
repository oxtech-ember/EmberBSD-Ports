# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Selected bundler process and ownership controls.
"""Reuse SDK process APIs; models inject errors at real bundler boundaries."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shlex
import shutil
import signal
import sys
import time
from unittest.mock import patch


def run_controls(f, bundler, valid):
    from package_set_fixture import check
    from emberbsd_sdk.errors import CommandError, ProcessOwnershipError
    from emberbsd_sdk import jsonio
    from emberbsd_sdk.jsonio import read_json
    from emberbsd_sdk.process import OwnedProcessGroup
    count = 0

    def passed(name):
        nonlocal count
        count += 1
        print('PASS: ' + name)

    def command(destination, sdk=None):
        return [sys.executable, '-B', '-I', '-S', str(bundler), '--sdk-source',
                str(sdk or f.sdk), str(valid), str(destination)]

    def shell(name, body):
        path = f.work / name
        path.write_text('#!/bin/sh\n' + body + '\n'); path.chmod(0o755)
        return str(path)

    def reject(name, env, code, message, sdk=None):
        destination = f.work / name
        result = f.status(command(destination, sdk), env=env)
        text = result.stdout + result.stderr
        (f.work / (name + '.log')).write_bytes(text)
        check(result.returncode == code and message.encode() in text,
              f'{name}: wrong refusal {result.returncode}: {text!r}')
        check(not os.path.lexists(destination), name + ': published output')
        check(not list(f.work.glob('.' + name + '-*')), name + ': unexpected staging')
        passed(name)

    fatal = shell('fatal', 'printf reason97 >&2; exit 97')
    reject('version-97', dict(f.env, BSDTAR=fatal), 97, 'reason97')
    metadata = shell('metadata-fatal', 'if [ "$1" = -xOf ]; then printf reason97 >&2; exit 97; fi\nexec ' + shlex.quote(f.tar) + ' "$@"')
    reject('metadata-97', dict(f.env, BSDTAR=metadata), 97, 'reason97')
    terminated = shell('terminated', 'kill -TERM $$')
    reject('producer-signal', dict(f.env, BSDTAR=terminated), 143, 'command failed (-15)')
    marker = f.work / 'unexpected-producer'
    forbidden = shell('forbidden', 'touch ' + shlex.quote(str(marker)) + '; exit 97')
    for module, constant in (('stream', 'PRODUCER_STREAM_API'), ('tarstream', 'TAR_STREAM_API'),
                             ('tarstream', 'TAR_HEADER_FACTS_API'), ('publication', 'DIRECTORY_PUBLICATION_API')):
        sdk = f.work / ('old-sdk-' + constant)
        shutil.copytree(Path(f.sdk) / 'src', sdk / 'src')
        path = sdk / 'src/emberbsd_sdk' / (module + '.py')
        text = path.read_text(); check(text.count(constant + ' = 1') == 1, 'Missing capability control')
        path.write_text(text.replace(constant + ' = 1', constant + ' = 0'))
        reject('old-' + constant, dict(f.env, BSDTAR=forbidden), 1, 'capabilities is required', sdk)
        check(not marker.exists(), 'Old SDK started a producer')
    sdk = f.work / 'missing-publication-sdk'
    shutil.copytree(Path(f.sdk) / 'src', sdk / 'src')
    (sdk / 'src/emberbsd_sdk/publication.py').unlink()
    reject('missing-publication', dict(f.env, BSDTAR=forbidden), 1, 'capabilities is required', sdk)
    check(not marker.exists(), 'Missing SDK module started a producer')

    # The outer CLI receives TERM while its auditor is in a real tar producer.
    # Each nested SDK session owns its own drain; the bundle must retain work.
    ready = f.work / 'auditor-ready'
    blocker = shell('blocking-tar', 'if [ "$1" = -cf ]; then\n  : > ' + shlex.quote(str(ready)) +
                    '\n  sleep 30\nfi\nexec ' + shlex.quote(f.tar) + ' "$@"')
    destination = f.work / 'cli-term'
    log = f.work / 'cli-term.log'
    with log.open('wb') as output:
        group = OwnedProcessGroup(command(destination), cwd=f.work,
                                  env=dict(f.env, BSDTAR=blocker), stdout=output, stderr=output)
        try:
            group.start()
            deadline = time.monotonic() + 30
            while not ready.exists():
                check(group.poll() is None and time.monotonic() < deadline, 'Auditor did not reach the signal control')
                time.sleep(0.02)
            group.stop()
            check(group.poll() == 128 + signal.SIGTERM, 'CLI lost its TERM status')
        finally:
            group.stop()
    retained = list(f.work.glob('.cli-term-*'))
    check(not destination.exists() and len(retained) == 1, 'Interrupted auditor work was not retained')
    check(('Retained incomplete auditor workspace: ' + str(retained[0])).encode() in log.read_bytes(), 'Missing retained-path diagnostic')
    passed('cli-term-retention')

    spec = importlib.util.spec_from_file_location('bundle_under_test', bundler)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.load_sdk(['--sdk-source', f.sdk])
    real_command = module.command
    sample = b'@cwd /usr/pkg\n@comment first\rbin/fake\nbin/real\r\n'
    check(set(module.installed_files(sample, Path('fixture.tgz'))) == {b'/usr/pkg/bin/real'},
          'PLIST parser changed binary Ruby line semantics')
    check(module.lines(b'a\fb\nlast\r') == [b'a\fb', b'last'] and module.lines(b'') == [],
          'PLIST parser normalized other control bytes')
    passed('binary-plist-line-separators')

    # This uses the production stream wrapper with a small, explicit test bound.
    producer = shell('bounded-output', "printf 123456789; printf bounded-reason >&2; exit 97")
    with patch.object(module, 'METADATA_LIMIT', 8):
        try:
            module.command([producer], f.env)
        except CommandError as error:
            check(error.returncode == 97 and error.stdout == b'12345678' and
                  error.stdout_truncated and error.stderr == b'bounded-reason', 'Lost status or clipped prefix')
        else:
            raise AssertionError('Overflowing failed producer was accepted')
    passed('bounded-output-status-97')

    for name, during_audit, problem, marker_fails in (
        ('model-audit-97', True, CommandError(97, ['auditor'], stderr=b'audit-97'), False),
        ('model-unknown-before-audit', False, ProcessOwnershipError(0, 'fixture unknown ownership'), False),
        ('model-unknown-marker-fails', True, ProcessOwnershipError(0, 'fixture unknown ownership'), True)):
        destination = f.work / name
        def dispatch(argv, env):
            selected = any(str(a).endswith('/prepare-package-set.py') for a in argv) if during_audit else '-xOf' in argv
            if selected:
                raise problem
            return real_command(argv, env)
        out, err = io.StringIO(), io.StringIO()
        with patch.object(module, 'command', dispatch), patch.dict(os.environ, f.env), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), contextlib.ExitStack() as stack:
            if marker_fails:
                stack.enter_context(patch.object(jsonio, 'write_json', side_effect=OSError('fixture marker failure')))
            code = module.main(['--sdk-source', f.sdk, str(valid), str(destination)])
        (f.work / (name + '.log')).write_text(out.getvalue() + err.getvalue())
        retained = list(f.work.glob('.' + name + '-*'))
        check(code == (97 if isinstance(problem, CommandError) else 1) and
              not destination.exists() and len(retained) == 1, name + ': lost failure or retained work')
        check('Retained incomplete auditor workspace: ' + str(retained[0]) in err.getvalue(), 'Missing retained path')
        if marker_fails:
            check('Cannot write quarantine marker: fixture marker failure' in err.getvalue(), 'Marker failure hidden')
        elif isinstance(problem, ProcessOwnershipError):
            check(read_json(retained[0] / '.producer-ownership-unproven.json')['status'] == 'unproven', 'Missing quarantine marker')
        passed(name)

    source = f.work / 'source-change-input'; shutil.copytree(valid, source)
    destination = f.work / 'source-change-output'
    def change_source(argv, env):
        value = real_command(argv, env)
        if '-cJf' in argv:
            with (source / 'target.txt').open('ab') as stream:
                stream.write(b'changed\n')
        return value
    out, err = io.StringIO(), io.StringIO()
    with patch.object(module, 'command', change_source), patch.dict(os.environ, f.env), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = module.main(['--sdk-source', f.sdk, str(source), str(destination)])
    (f.work / 'source-change.log').write_text(out.getvalue() + err.getvalue())
    check(code == 1 and 'Source package set changed' in err.getvalue() and
          not destination.exists() and not list(f.work.glob('.source-change-output-*')), 'Changed source was published')
    passed('source-change-before-publication')
    destination = f.work / 'reported-oversize'
    out, err = io.StringIO(), io.StringIO()
    with patch.object(module, 'INSTALLER_LIMIT', 1), patch.dict(os.environ, f.env), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = module.main(['--sdk-source', f.sdk, str(valid), str(destination)])
    (f.work / 'reported-oversize.log').write_text(out.getvalue() + err.getvalue())
    check(code == 0 and destination.is_dir() and 'exceeds the current installer capacity' in out.getvalue(),
          'Reporting limit became a generation barrier')
    check(read_json(destination / 'PROVENANCE.json')['installer_capacity'] ==
          dict(limit_bytes=1, fits_current_limit=False), 'Oversize report lost its explicit limit')
    passed('oversize-reported-without-generation-barrier')
    print(f'PASS: {count} bundler process and retention controls; injected ownership errors are models')
