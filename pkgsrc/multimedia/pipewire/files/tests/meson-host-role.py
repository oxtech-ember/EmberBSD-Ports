#!/usr/bin/env python3
"""Verify PipeWire's build-machine Meson environment with real compilers."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

p = argparse.ArgumentParser()
for name in ('bmake', 'recipe', 'makeconf', 'meson', 'ninja', 'cross-file',
             'target-cc', 'host-sdk'):
    p.add_argument('--' + name, required=True)
a = p.parse_args()
env = os.environ.copy()
env['MAKECONF'] = a.makeconf
out = subprocess.check_output([a.bmake, '-C', a.recipe, '-V', '${MAKE_ENV}'], env=env, text=True)
values = dict(x.split('=', 1) for x in shlex.split(out) if '=' in x)
for name in ('CC_FOR_BUILD', 'CXX_FOR_BUILD', 'AR_FOR_BUILD', 'CPPFLAGS_FOR_BUILD',
             'CFLAGS_FOR_BUILD', 'CXXFLAGS_FOR_BUILD', 'LDFLAGS_FOR_BUILD'):
    if name not in values:
        raise SystemExit('missing recipe build-machine variable: ' + name)
if not values['CC_FOR_BUILD'] or not Path(shlex.split(values['CC_FOR_BUILD'])[0]).is_absolute():
    raise SystemExit('build compiler must be an explicit command')
with tempfile.TemporaryDirectory(prefix='pipewire-meson-role-') as tmp:
    root = Path(tmp)
    (root / 'meson.build').write_text("project('role-check', 'c')\nexecutable('gen', 'gen.c', native: true)\nexecutable('target', 'target.c')\n")
    (root / 'gen.c').write_text('#ifndef BUILD_ROLE\n#error missing build role\n#endif\n#ifdef TARGET_ROLE\n#error leaked target role\n#endif\nint main(void){return 0;}\n')
    (root / 'target.c').write_text('#ifndef TARGET_ROLE\n#error missing target role\n#endif\n#ifdef BUILD_ROLE\n#error leaked build role\n#endif\nint main(void){return 0;}\n')
    env.update({name: values[name] for name in values if name.endswith('_FOR_BUILD')})
    env.update(CC=a.target_cc, CFLAGS='-DTARGET_ROLE', CFLAGS_FOR_BUILD=values['CFLAGS_FOR_BUILD'] + ' -DBUILD_ROLE', SDKROOT=a.host_sdk)
    subprocess.run([a.meson, 'setup', str(root / 'build'), str(root), '--cross-file', a.cross_file], env=env, check=True, capture_output=True)
    subprocess.run([a.ninja, '-C', str(root / 'build'), '-j1'], env=env, check=True, capture_output=True)
    host_magic = (root / 'build/gen').read_bytes()[:4]
    target_magic = (root / 'build/target').read_bytes()[:4]
    if host_magic not in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf') or target_magic != b'\x7fELF':
        raise SystemExit('unexpected build or target executable format')
    subprocess.run([str(root / 'build/gen')], check=True, env=env)
    env['CC_FOR_BUILD'] = a.target_cc
    negative = subprocess.run([a.meson, 'setup', str(root / 'negative'), str(root), '--cross-file', a.cross_file], env=env, capture_output=True)
    if negative.returncode == 0:
        raise SystemExit('negative control unexpectedly accepted target compiler for build machine')
print('PASS: real Meson uses SDK build compiler and target cross compiler independently')
