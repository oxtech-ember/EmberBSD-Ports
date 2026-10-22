#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Execute real ncurses install scripts.
"""Check native tic selection against a hostile PATH and real terminal data."""
import argparse
import hashlib
import json
import os
import shlex
from pathlib import Path
import subprocess


def metadata_producer_paths(paths, native, target_prefix):
    logical = Path(target_prefix)
    if logical in paths:
        raise ValueError('A producer path cannot equal the logical target prefix.')
    selected = [p.resolve(strict=True) for p in paths]
    if logical in selected:
        raise ValueError('A producer path cannot resolve to the logical target prefix.')
    return [str(p) for p in selected] + ([] if native == logical else [str(native)])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('before', 'after', 'native_prefix', 'new_work'):
        cli.add_argument(name, type=Path)
    cli.add_argument('--shell', default='/bin/sh')
    cli.add_argument('--target-config', type=Path, required=True)
    cli.add_argument('--target-prefix', default='/usr/pkg')
    cli.add_argument('--target-metadata-dir', type=Path, required=True)
    cli.add_argument('--producer-path', type=Path, action='append', required=True)
    args = cli.parse_args()
    before, after, native = (p.resolve(strict=True) for p in (args.before, args.after, args.native_prefix))
    work = args.new_work
    if not work.is_absolute() or work.resolve() != work or work.exists() or work.is_symlink():
        raise ValueError('Use a new absolute canonical work directory.')
    if any(work.is_relative_to(p) for p in (before.parent, after.parent, native)):
        raise ValueError('Keep output outside the selected inputs.')
    target = args.target_config.resolve(strict=True)
    metadata = args.target_metadata_dir.resolve(strict=True)
    producer_paths = metadata_producer_paths(args.producer_path, native, args.target_prefix)
    host_prefix = None if native == Path(args.target_prefix) else str(native)
    pc_files = [metadata / (name + '.pc') for name in ('ncurses', 'ncurses++', 'gnuform', 'gnumenu', 'gnupanel')]
    tic, infocmp = native / 'bin/tic', native / 'bin/infocmp'
    old = ': "${tic_path:=tic}"'
    new = ': "${tic_path:=' + str(tic) + '}"'
    original, repaired = before.read_text(), after.read_text()
    if original.count(old) != 1 or original.replace(old, new) != repaired:
        raise ValueError('Require actual before/after scripts with only the tic selection changed.')
    inputs = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (before, after, target, tic, infocmp, native / 'bin/ncurses6-config', *pc_files)}
    work.mkdir(mode=0o700)
    (work / 'tmp').mkdir()
    (work / 'bin').mkdir()
    marker = work / 'wrong-tic-selected'
    (work / 'bin/tic').write_text('#!/bin/sh\nprintf wrong-tool > ' + shlex.quote(str(marker)) + '\nexit 87\n')
    (work / 'bin/tic').chmod(0o755)
    environment = dict(os.environ)
    for name in ('tic_path', 'TIC_PATH', 'TIC', 'TERMINFO', 'TERMINFO_DIRS', 'DESTDIR'):
        environment.pop(name, None)
    environment.update(PATH=str(work / 'bin') + ':/usr/bin:/bin', LC_ALL='C',
                       TMPDIR=str(work / 'tmp'), TMP=str(work / 'tmp'), TEMP=str(work / 'tmp'))
    commands = []

    def run(label, argv, env=environment):
        result = subprocess.run(list(map(str, argv)), cwd=work, env=env, capture_output=True, timeout=60)
        (work / (label + '.stdout')).write_bytes(result.stdout)
        (work / (label + '.stderr')).write_bytes(result.stderr)
        commands.append(dict(label=label, argv=list(map(str, argv)), status=result.returncode))
        (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        return result

    def terminal(text):
        return b'\n'.join(line for line in text.splitlines() if not line.startswith(b'#'))

    source = run('native-terminal', [infocmp, '-x', '-I', '-A', native / 'share/terminfo', 'scrt'])
    if source.returncode:
        raise ValueError('The native provider must contain the actual extended scrt entry.')
    terms = work / 'scrt.src'
    terms.write_bytes(source.stdout)
    for label, script, expected in [('before', before, False), ('after', after, True)]:
        prefix = work / label
        (prefix / 'bin').mkdir(parents=True)
        env = dict(environment, prefix=str(prefix), INSTALL_PREFIX=str(prefix),
                   BINDIR=str(prefix / 'bin'), TICDIR=str(prefix / 'share/terminfo'),
                   tic_source=str(terms))
        result = run(label, [args.shell, script], env)
        if not expected:
            if result.returncode == 0 or not marker.exists():
                raise ValueError('The original install script did not expose the PATH tool selection.')
            marker.unlink()
        elif result.returncode or marker.exists() or str(tic).encode() not in result.stdout:
            raise ValueError('The repaired script did not use the selected native tic.')
    dump = run('roundtrip', [infocmp, '-x', '-I', '-A', work / 'after/share/terminfo', 'scrt'])
    if dump.returncode or terminal(dump.stdout) != terminal(source.stdout):
        raise ValueError('Native terminfo compile/readback changed the real terminal data.')
    text = target.read_text()
    if not text.startswith('#!/bin/sh\n') or (host_prefix and host_prefix in text) or '@SHELL@' in text:
        raise ValueError('The target helper retains a build-host interpreter.')
    syntax = run('target-config-syntax', ['/bin/sh', '-n', target])
    valid = run('target-config-values', ['/bin/sh', target, '--version', '--prefix', '--abi-version'])
    expected = ('6.6.20251230\n' + args.target_prefix + '\n6\n').encode()
    if syntax.returncode or valid.returncode or valid.stdout != expected or valid.stderr:
        raise ValueError('The actual target helper changed its version/prefix/ABI contract.')
    for label, arguments in [('no-arguments', []), ('unknown-option', ['--emberbsd-invalid-option'])]:
        result = run('target-config-' + label, ['/bin/sh', target, *arguments])
        if result.returncode != 1 or result.stdout or b'Usage:' not in result.stderr or (host_prefix and host_prefix.encode() in result.stderr):
            raise ValueError('The target helper failed its real recursive error/help branch: ' + label)
    flags = run('target-config-flags', ['/bin/sh', target, '--cflags', '--libs'])
    lines = flags.stdout.splitlines()
    if flags.returncode or len(lines) != 2 or flags.stderr:
        raise ValueError('The actual target helper failed its consumer flags CLI.')
    if any(path in text or path.encode() in flags.stdout for path in producer_paths) or b'-rpath-link' in flags.stdout:
        raise ValueError('The target helper exports producer paths.')
    prefix = args.target_prefix
    cflags = {'-D_NETBSD_SOURCE', '-DNCURSES_WIDECHAR', '-I' + prefix + '/include/ncurses', '-I' + prefix + '/include'}
    allowed_libs = {'-lncurses', '-L' + prefix + '/lib', '-Wl,-R' + prefix + '/lib'}
    libs = shlex.split(lines[1].decode())
    if set(shlex.split(lines[0].decode())) != cflags or not set(libs).issubset(allowed_libs) or '-lncurses' not in libs:
        raise ValueError('The actual helper changed its target consumer flags.')
    for pc in pc_files:
        value = pc.read_text()
        if any(path in value for path in producer_paths) or '-rpath-link' in value:
            raise ValueError('The pkg-config file exports producer paths: ' + pc.name)
        if 'prefix=' + prefix not in value.splitlines() or 'version=6.6.20251230' not in value.splitlines():
            raise ValueError('The actual pkg-config file changed its target identity: ' + pc.name)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in inputs.items()):
        raise ValueError('Selected input changed during the test.')
    (work / 'result.json').write_text(json.dumps(dict(status='pass', inputs_sha256=inputs,
        scope='Actual configured install scripts, hostile PATH control, real native scrt compile/readback, target-helper POSIX shell CLI and consumer flags, and five real pkg-config files without selected producer paths. No target execution.'), indent=2) + '\n')
    print('PASS: native tic selection, real terminfo roundtrip and clean target consumer metadata')


if __name__ == '__main__':
    main()
