#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
"""Construct an ExtUtils build context from an installed target Perl Config."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for name in ('host-perl', 'target-config', 'sysroot'):
    p.add_argument('--' + name, required=True)
for name in ('cc', 'ld', 'ar', 'ranlib', 'output'):
    p.add_argument('--' + name)
p.add_argument('--metadata-only', action='store_true')
p.add_argument('--cflags', default='')
p.add_argument('--ldflags', default='')
a = p.parse_args()
sysroot = Path(a.sysroot).resolve(strict=True)
requested = Path(a.target_config)
source = requested.resolve(strict=True)
source.relative_to(sysroot)
if requested.name != 'Config.pm':
    p.error('target-config must name the installed target Config.pm')
for tool in ((a.host_perl,) if a.metadata_only else (a.host_perl, a.cc, a.ld, a.ar, a.ranlib)):
    if not tool or not os.path.isabs(tool) or not os.access(tool, os.X_OK):
        p.error('build tools must be selected absolute executables')
with tempfile.TemporaryDirectory() as scratch:
    for name in ('Config.pm', 'Config_heavy.pl'):
        member = (source.parent / name).resolve(strict=True)
        member.relative_to(sysroot)
        shutil.copyfile(member, Path(scratch) / name)
    command = [a.host_perl, '-I' + scratch, '-MConfig', '-MJSON::PP',
               '-e', 'print encode_json({%Config})']
    env = dict(os.environ)
    env.pop('PERL5LIB', None)
    env.pop('PERL5OPT', None)
    env.pop('EMBERBSD_PERL_BUILD_CONFIG', None)
    values = json.loads(subprocess.check_output(command, env=env))
if a.metadata_only:
    keys = ('prefix', 'installarchlib', 'installscript', 'installvendorbin',
            'installvendorscript', 'installvendorarch', 'installvendorlib',
            'installvendorman1dir', 'installvendorman3dir')
    for key in keys:
        value = values[key]
        if not value or any(c.isspace() or c in "';" for c in value):
            p.error('target Perl metadata is not representable in pkgsrc variables')
        print(f"{key}='{value}';")
    raise SystemExit(0)
for key in ('archlibexp', 'privlibexp'):
    path = Path(values[key])
    if not path.is_absolute():
        p.error('target Config contains a relative library path')
    values[key] = str(sysroot / path.relative_to('/'))
values.update(cc=a.cc, ld=a.ld, ar=a.ar, ranlib=a.ranlib,
              ccflags=a.cflags, optimize='', ldflags=a.ldflags,
              lddlflags='-shared ' + a.ldflags,
              libpth=f'{sysroot}/usr/lib {sysroot}/usr/pkg/lib')
if not a.output:
    p.error('output is required for a build context')
out = Path(a.output)
if not out.is_absolute():
    p.error('output must be absolute')
out.write_text(json.dumps(values, sort_keys=True) + '\n')
