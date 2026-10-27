#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native common-feature causal regression.
"""Build real SQLite with/without RBU; no installation or target execution."""
import argparse
import hashlib
import json
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys

RECIPE = Path(__file__).resolve().parents[1]
PORTS = RECIPE.parents[2]
p = argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source', 'host-prefix', 'archive', 'work'):
    p.add_argument('--' + name, required=True, type=Path)
p.add_argument('--abi-flag', action='append', default=[])
p.add_argument('--sanitize', action='store_true')
a = p.parse_args()
assert all(x.is_absolute() for x in (a.sdk_source, a.host_prefix, a.archive, a.work))
sys.path.insert(0, str(a.sdk_source / 'src'))
from emberbsd_sdk import native_checks, sourceprep
from emberbsd_sdk.host_prefix import load_host_prefix
roles = ('cc', 'cxx', 'cpp', 'sh', 'python', 'nm', 'patch', 'cat', 'sed', 'grep',
         'awk', 'cut', 'tr', 'rm', 'mkdir', 'cp', 'mv', 'chmod', 'uname', 'expr',
         'head', 'tail', 'sort', 'touch', 'find', 'xargs', 'ar', 'ranlib')
native = load_host_prefix(a.host_prefix, required_roles=roles)
assert Path(native.tool('python')).resolve() == Path(sys.executable).resolve()
if a.sanitize:
    a.abi_flag += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
assert not a.work.exists()
a.work.mkdir(parents=True)
env = native_checks.check_environment(native, bindings=a.work / 'tools',
    extra_flags={k:a.abi_flag for k in ('cflags', 'cxxflags', 'ldflags')})
env.update(TMPDIR=str(a.work), LC_ALL='C', CCACHE='none')
commands = []

def run(label, command, *, cwd=a.work, expected=0, extra=None):
    argv = list(map(str, command))
    result = subprocess.run(argv, cwd=cwd, env=env | (extra or {}),
                            capture_output=True, timeout=180)
    (a.work / (label + '.stdout')).write_bytes(result.stdout)
    (a.work / (label + '.stderr')).write_bytes(result.stderr)
    commands.append(dict(label=label, argv=argv, status=result.returncode))
    (a.work / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    assert (result.returncode == 0) == (expected == 0), (
        label, result.returncode, result.stdout.decode(), result.stderr.decode())
    return result.stdout, result.stderr

raw = a.archive.read_bytes()
distinfo = (RECIPE / 'distinfo').read_text()
for algorithm, label in (('sha512', 'SHA512'), ('blake2s', 'BLAKE2s')):
    assert f'{label} ({a.archive.name}) = {hashlib.new(algorithm, raw).hexdigest()}' in distinfo
assert f'Size ({a.archive.name}) = {len(raw)} bytes' in distinfo
source = a.work / 'source'; source.mkdir()
sourceprep.extract_archive(a.archive, source, a.archive.name.removesuffix('.tar.gz'), 'SQLite')
source = source / a.archive.name.removesuffix('.tar.gz')
spec = importlib.util.spec_from_file_location('ports_export', PORTS / 'scripts/prepare-pkgsrc.py')
exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)
for patch in sorted((RECIPE / 'patches').iterdir()):
    assert f'SHA1 ({patch.name}) = {exporter.patch_sha1(patch)}' in distinfo
    run(patch.name, [native.tool('patch'), '-f', '-F0', '-p0', '-V', 'none', '-i', patch], cwd=source)
features = dict(line.split('=', 1) for line in (RECIPE / 'features.mk').read_text().splitlines()
                if line.startswith('SQLITE_'))
cppflags = shlex.split(features['SQLITE_CPPFLAGS'])
assert cppflags.count('-DSQLITE_ENABLE_RBU') == 1
configured = a.work / 'configured'; configured.mkdir()
run('configure', [native.tool('sh'), source / 'configure',
    *shlex.split(features['SQLITE_CONFIGURE_ARGS']), '--disable-readline'], cwd=configured,
    extra={'CPPFLAGS':shlex.join(cppflags), 'CC_FOR_BUILD':env['CC']})
flags = next(shlex.split(line.split('=', 1)[1]) for line in
             (configured / 'Makefile').read_text().splitlines() if line.startswith('OPT_FEATURE_FLAGS ='))
assert '-DSQLITE_ENABLE_RBU' in flags
text = (source / 'sqlite3.c').read_text()
start = text.index('#ifndef _SQLITE3RBU_H\n')
end = text.index('#endif /* _SQLITE3RBU_H */', start) + len('#endif /* _SQLITE3RBU_H */')
(source / 'sqlite3rbu.h').write_text(text[start:end] + '\n')
option = a.work / 'option.c'
option.write_text('#include <sqlite3.h>\n#include <stdio.h>\nint main(void) { '
                  'printf("%d\\n",sqlite3_compileoption_used("ENABLE_RBU")); return 0; }\n')
darwin = native.host['os'] == 'Darwin'
libname = 'libsqlite3.0.dylib' if darwin else 'libsqlite3.so.0'
link = ['-dynamiclib', '-Wl,-install_name,@rpath/' + libname] if darwin else ['-shared', '-Wl,-soname,' + libname]
libs = []
exports = []
for label, selected in [('baseline', [x for x in flags if x != '-DSQLITE_ENABLE_RBU']), ('candidate', flags)]:
    out = a.work / label; out.mkdir(); library = out / libname; libs.append(library)
    run(label + '-library', [env['CC'], '-O0', '-fPIC', *selected, '-I' + str(source),
        source / 'sqlite3.c', *link, '-o', library, '-lm', '-lpthread'])
    symbols, _ = run(label + '-symbols', [native.tool('nm'), '--defined-only', '--extern-only', library])
    exports.append({line.split()[-1] for line in symbols.decode().splitlines() if line.split()})
    run(label + '-option-link', [env['CC'], '-Wall', '-Wextra', '-Werror', '-I' + str(source),
        option, library, '-Wl,-rpath,' + str(out), '-o', out / 'option'])
    output, _ = run(label + '-option', [out / 'option'])
    assert output == (b'0\n' if label == 'baseline' else b'1\n')
assert exports[0] <= exports[1], sorted(exports[0] - exports[1])
assert any('sqlite3rbu_open' in name for name in exports[1] - exports[0])
probe = RECIPE / 'tests/rbu.c'
common = [env['CC'], '-Wall', '-Wextra', '-Werror', '-I' + str(source), probe]
_, missing = run('baseline-rbu-refusal', [*common, libs[0], '-o', a.work / 'absent'], expected=1)
assert b'sqlite3rbu_' in missing
run('rbu-link', [*common, libs[1], '-Wl,-rpath,' + str(libs[1].parent), '-o', a.work / 'rbu'])
runtime = a.work / 'rbu-runtime'; runtime.mkdir()
run('rbu-runtime', [a.work / 'rbu'], cwd=runtime)
# Existing generic consumer links once against baseline, then runs unchanged
# against each library. This verifies additive exports and ordinary SQL paths.
consumer = PORTS / 'probes/sqlite/consumer.c'
run('consumer-link', [env['CC'], '-I' + str(source), consumer, libs[0],
    '-Wl,-rpath,' + str(libs[0].parent), '-o', a.work / 'consumer'])
for label, library in zip(('baseline', 'candidate'), libs):
    loader = {'DYLD_LIBRARY_PATH' if darwin else 'LD_LIBRARY_PATH':str(library.parent)}
    run(label + '-consumer', [a.work / 'consumer', a.work / (label + '.db')], extra=loader)
print('PASS: common flags; RBU 0→1 and absent→present API; update/resume/refusal; unchanged consumer and additive exports')
