# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD compiler-rt profile runtime regression, AI-assisted.
"""Exercise a caller-built compiler-rt profile archive; never install it."""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
for name in ('cc', 'profdata', 'archive', 'value-source', 'work'):
    p.add_argument('--' + name, required=True, type=Path)
p.add_argument('--include-dir', action='append', default=[], type=Path)
p.add_argument('--flag', action='append', default=[], help='one selected compiler/linker argument')
p.add_argument('--link-prefix', action='append', default=[], help='one argument of a selected link launcher')
p.add_argument('--map-style', choices=('darwin', 'gnu'), required=True)
p.add_argument('--sanitize', action='store_true')
p.add_argument('--only-limits', action='store_true')
a = p.parse_args()
for value in (a.cc, a.profdata, a.archive, a.value_source, *a.include_dir):
    if not value.is_absolute() or not value.exists():
        p.error('select existing absolute tool, source, archive and include paths')
if not a.work.is_absolute():
    p.error('--work must be absolute')
a.work.mkdir(parents=True, exist_ok=False)
env = os.environ.copy()
env['LLVM_PROFILE_FILE'] = str(a.work / 'default.profraw')
if a.sanitize:
    env.update(ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    a.flag += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']

def run(name, argv):
    with (a.work / (name + '.log')).open('w') as output:
        output.write('ARGV ' + shlex.join(map(str, argv)) + '\n')
        output.flush()
        subprocess.run(list(map(str, argv)), env=env, cwd=a.work, stdout=output,
                       stderr=subprocess.STDOUT, check=True)

common = [a.cc, '-O1', '-g', *a.flag, *['-I' + str(d) for d in a.include_dir]]
tests = [('limits', Path(__file__).with_name('profile-value-limits.c'), []),
         ('mcdc', Path(__file__).with_name('profile-merge-mcdc.c'),
          ['-fcoverage-mapping', '-fcoverage-mcdc']),
         ('short', a.value_source.parent.parent / 'instrprof-merge-short.c', []),
         ('value', a.value_source, ['-mllvm', '-enable-value-profiling=true',
                                    '-mllvm', '-vp-static-alloc=true',
                                    '-mllvm', '-vp-counters-per-site=3'])]
if a.only_limits:
    tests = tests[:1]
for name, source, flags in tests:
    obj, exe, linkmap = (a.work / (name + suffix) for suffix in ('.o', '', '.map'))
    instrument = [] if name == 'limits' else ['-fprofile-instr-generate']
    run(name + '-compile', [*common, *instrument, *flags,
                             '-c', source, '-o', obj])
    maparg = '-Wl,-map,' if a.map_style == 'darwin' else '-Wl,-Map,'
    run(name + '-link', [*a.link_prefix, *common, obj, a.archive,
                          maparg + str(linkmap), '-o', exe])
    contents = linkmap.read_text()
    required = ['InstrProfilingValue.c.o'] if name == 'limits' else ['InstrProfilingMerge.c.o']
    if name == 'value':
        required += ['InstrProfilingMergeFile.c.o', 'InstrProfilingValue.c.o']
    selected = a.archive.resolve()
    entries = re.findall(r'(?m)(/[^\n]*?\.a)\(([^()]*)\)', contents)
    providers = [(Path(path).resolve(), member) for path, member in entries
                 if member.startswith(('InstrProfiling', 'GCDAProfiling'))
                 or Path(path).name.startswith('libclang_rt.profile')]
    if (not providers or any(path != selected for path, _ in providers)
            or any(not any(path == selected and item == member
                           for path, item in providers) for member in required)):
        raise ValueError('link map does not select only the requested profile archive')
    argv = [exe, a.work / 'value.profraw'] if name == 'value' else [exe]
    run(name + '-run', argv)
    print(name + ': PASS', flush=True)
if a.only_limits:
    sys.exit(0)
profile = a.work / 'value.profdata'
run('profdata-merge', [a.profdata, 'merge', '-o', profile, a.work / 'value.profraw'])
run('profdata-show', [a.profdata, 'show', '--all-functions', '--counts', '--ic-targets', profile])
s = (a.work / 'profdata-show.log').read_text()
foo = s[s.index('  foo:'):]
actual = {(int(i), name, int(count)) for i, name, count in
          re.findall(r'\[\s*(\d+),\s*(callee[123]),\s*(\d+)\s*\]', foo)}
expected = {(0, 'callee3', 10), (0, 'callee2', 6), (0, 'callee1', 2),
            (1, 'callee1', 5), (1, 'callee2', 3), (1, 'callee3', 1)}
if actual != expected:
    raise ValueError('value-profile counts differ: ' + repr(actual))
print('six indirect value counts: PASS', flush=True)
