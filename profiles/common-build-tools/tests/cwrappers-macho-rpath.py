#!/usr/bin/env python3.15
"""Check explicit Mach-O RPATH rules with real baseline and candidate wrappers.

Usage: cwrappers-macho-rpath.py BASELINE_BIN CANDIDATE_BIN CONFIG_DIR NEW_WORK
CONFIG_DIR contains copies of generated cc and ld configurations. Each wrapper
executes echo, as in pkgsrc's upstream wrapper tests. No compiler runs here.
Origin: EmberBSD (AI-assisted). Use Python 3.15 and the standard library.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

assert sys.version_info[:2] == (3, 15)
assert len(sys.argv) == 5, __doc__
old_bin, new_bin, configs, work = map(Path, sys.argv[1:])
assert all(p.is_absolute() and p.is_dir() for p in [old_bin, new_bin, configs])
assert work.is_absolute() and work.resolve() == work and not os.path.lexists(work)
work.mkdir()
loader = '@loader_path/../dbus'
executable = '@executable_path/../dbus'
def rule(source, destination=None):
    return 'R:' + source + ':' + (source if destination is None else destination)
# Each row names the real old result and the required new result.
cases = [
 ('loader', 'cc', loader, [rule(loader)], None, loader),
 ('executable', 'cc', executable, [rule(executable)], None, executable),
 ('root-only', 'cc', '@loader_path', [rule('@loader_path')], None, '@loader_path'),
 ('subdirectory', 'cc', loader + '/child', [rule(loader)], None, loader + '/child'),
 ('unlisted', 'cc', loader, [], None, None),
 ('unlisted-libs', 'cc', '@loader_path/.libs', [], None, None),
 ('partial-prefix', 'cc', loader + '-other', [rule(loader)], None, None),
 ('partial-root', 'cc', '@loader_path_other/lib', [rule('@loader_path_other/lib')], None, None),
 ('rpath-root', 'cc', '@rpath/lib', [rule('@rpath/lib')], None, None),
 ('relative', 'cc', 'relative/lib', [rule('relative/lib')], None, None),
 ('empty', 'cc', '', [], None, None),
 ('short-loader', 'cc', '@loader_pat', [rule('@loader_pat')], None, None),
 ('short-executable', 'cc', '@executable_pat', [rule('@executable_pat')], None, None),
 ('mapped-token', 'cc', loader + '/child', [rule(loader, executable)], None, executable + '/child'),
 ('mapped-absolute', 'cc', loader, [rule(loader, '/allowed/lib')], None, '/allowed/lib'),
 ('absolute-to-token', 'cc', '/allowed/lib', [rule('/allowed/lib', loader)], None, loader),
 ('bad-destination', 'cc', loader, [rule(loader, 'relative/lib')], None, None),
 ('exact-directory', 'cc', loader, [rule(loader + '/', executable)], None, executable),
 ('exact-directory-slash', 'cc', loader + '/', [rule(loader + '/', executable)], None, executable),
 ('destination-slash', 'cc', loader + '/child', [rule(loader, executable + '/')], None, executable + '//child'),
 ('denied', 'cc', loader, [rule(loader, ''), rule(loader)], None, None),
 ('absolute', 'cc', '/allowed/lib', [rule('/allowed/lib')], '/allowed/lib', '/allowed/lib'),
 ('unlisted-absolute', 'cc', '/unlisted/lib', [], None, None),
 ('absolute-libs', 'cc', '/unlisted/.libs', [], '/unlisted/.libs', '/unlisted/.libs'),
 ('ld-loader', 'ld', loader, [rule(loader)], loader, loader),
 ('ld-unlisted', 'ld', loader, [], loader, None),
 ('ld-unlisted-libs', 'ld', '@loader_path/.libs', [], '@loader_path/.libs', None),
 ('ld-mapped', 'ld', loader, [rule(loader, executable)], loader, executable),
 ('ld-bad-destination', 'ld', loader, [rule(loader, 'relative/lib')], loader, None),
 ('ld-exact-directory', 'ld', loader, [rule(loader + '/', executable)], loader, executable),
 ('ld-absolute', 'ld', '/allowed/lib', [rule('/allowed/lib')], '/allowed/lib', '/allowed/lib'),
 ('ld-relative-default', 'ld', 'relative/lib', [], 'relative/lib', 'relative/lib'),
 ('path-list', 'cc', loader + ':/allowed/lib:relative/lib:@rpath/lib',
  [rule(loader), rule('/allowed/lib')], '/allowed/lib', [loader, '/allowed/lib']),
 ('split-rpath', 'cc', ['-Wl,-rpath', '-Wl,' + loader], [rule(loader)], None, loader),
 ('joined-R', 'cc', ['-R' + loader], [rule(loader)], None, loader),
 ('loader-sysroot', 'cc', loader, [rule(loader)], None, loader),
 ('unlisted-sysroot', 'cc', loader, [], None, None),
 ('link-time-default', 'cc', ['-Wl,-rpath-link,' + loader], [rule(loader)], None, None),
]
commands = []
for name, kind, path, rules, old_expected, new_expected in cases:
    raw = (configs / kind).read_text()
    base = [line for line in raw.splitlines()
            if not line.startswith(('worklog=', 'exec=', 'exec_path=', 'path='))]
    base += ['worklog=' + str(work / 'wrapper.log'), 'exec=echo',
             'exec_path=/bin/echo', 'path=/usr/bin:/bin']
    if name.endswith('-sysroot'):
        base.append('sysroot=/fixture-sysroot')
    directory = work / name
    directory.mkdir()
    (directory / kind).write_text('\n'.join(base + ['transform=' + r for r in rules]) + '\n')
    for label, binaries, expected in [('before', old_bin, old_expected), ('after', new_bin, new_expected)]:
        wrapper = binaries / (kind + '-wrapper')
        assert wrapper.is_file() and os.access(wrapper, os.X_OK)
        option = path if isinstance(path, list) else (
            ['-Wl,-rpath,' + path] if kind == 'cc' else ['-rpath', path])
        argv = [str(wrapper), '-o', 'consumer', 'input.o', *option]
        env = dict(os.environ, CWRAPPERS_CONFIG_DIR=str(directory))
        result = subprocess.run(argv, env=env, cwd=work, text=True, capture_output=True, timeout=10)
        prefix = directory / label
        prefix.with_suffix('.stdout').write_text(result.stdout)
        prefix.with_suffix('.stderr').write_text(result.stderr)
        commands.append(dict(case=name, phase=label, argv=argv, exit=result.returncode,
                             stdout=result.stdout, stderr=result.stderr))
        (work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert result.returncode == 0 and not result.stderr, commands[-1]
        words = shlex.split(result.stdout)
        if kind == 'cc':
            actual = [w[len('-Wl,-rpath,'):] for w in words if w.startswith('-Wl,-rpath,')]
        else:
            actual = [words[i + 1] for i, word in enumerate(words[:-1]) if word == '-rpath']
        wanted = expected if isinstance(expected, list) else ([] if expected is None else [expected])
        assert actual == wanted, (name, label, actual, expected)
        if name.endswith('-sysroot'):
            assert not any(w.startswith('-Wl,-rpath-link,') and '@' in w for w in words), words
        if name == 'link-time-default':
            assert '-Wl,-rpath-link,' + loader in words, words
result = dict(status='PASS', cases=len(cases), wrapper_invocations=len(commands),
              wrapper_hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                              for d in [old_bin, new_bin] for p in [d/'cc-wrapper', d/'ld-wrapper']},
              limits='Argument filtering only. The two existing LD plain-relative and absolute .libs '
                     'policies remain unchanged. No D-Bus rebuild/test or installed RPATH acceptance.')
(work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
