#!/usr/bin/env python3
"""Check selected native-stage Mach-O providers without active-prefix fallback."""
import argparse
import os
import shlex
import shutil
from pathlib import Path
import subprocess
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--awk', required=True)
p.add_argument('--od', required=True)
p.add_argument('--lipo', required=True)
p.add_argument('--otool', required=True)
p.add_argument('--scanner', required=True)
p.add_argument('--image', required=True)
p.add_argument('--stage-root', type=Path, required=True)
p.add_argument('--host-prefix', type=Path, required=True)
p.add_argument('--expected-library', type=Path, required=True)
a = p.parse_args()
assert a.expected_library.is_file(), 'negative control requires an existing active-prefix library'
with tempfile.TemporaryDirectory(prefix='macho-stage-check-') as tmp:
    tmp = Path(tmp)
    requires = tmp / 'requires'
    probes = tmp / 'probes'
    lipo = tmp / 'lipo'
    lipo.write_text('#!/bin/sh\n'
                    'if [ "$2" = "-verify_arch" ]; then\n'
                    '    printf "%s\\t%s\\n" "$1" "$3" >> "$MACHO_TEST_PROBES"\n'
                    'fi\n'
                    'exec "$MACHO_TEST_LIPO" "$@"\n')
    lipo.chmod(0o755)

    def run(stage, destdir='', copies=1):
        requires.write_text('')
        probes.write_text('')
        env = dict(os.environ, MACHO_USE_LOAD_COMMANDS='yes', MACHO_OD=a.od,
                   MACHO_LIPO=shlex.quote(str(lipo)), MACHO_TEST_LIPO=a.lipo,
                   MACHO_TEST_PROBES=str(probes), MACHO_OTOOL=a.otool, DESTDIR=str(destdir), CROSS_DESTDIR='',
                   EMBERBSD_NATIVE_STAGE_ROOT=str(stage),
                   EMBERBSD_NATIVE_STAGE_PREFIX=str(a.host_prefix),
                   WRKDIR=str(tmp / 'unrelated'), SKIP_SYSTEM_LIBS='1',
                   PKG_INFO_CMD='/usr/bin/false', DEPENDS_FILE=str(tmp / 'deps'),
                   REQUIRES_FILE=str(requires))
        result = subprocess.run([a.awk, '-f', a.scanner], input=(a.image + '\n') * copies, env=env,
                                text=True, capture_output=True, check=True)
        return result.stdout, requires.read_text().splitlines()
    out, libs = run(a.stage_root)
    assert not out and str(a.expected_library) in libs, (out, libs)
    assert not any(str(a.stage_root) in lib for lib in libs), libs
    out, repeated = run(a.stage_root, copies=2)
    assert not out and repeated == libs * 2, (out, repeated)
    pairs = probes.read_text().splitlines()
    assert pairs and len(pairs) == len(set(pairs)), pairs
    missing, _ = run(tmp / 'empty-stage')
    assert 'missing library:' in missing and str(a.host_prefix) in missing, missing
    # The package currently being assembled wins over a same-name older
    # stage provider. Give the overlapping stage file an invalid Mach-O so
    # selecting it would fail the real architecture check.
    destdir = tmp / 'destdir'
    for lib in libs:
        physical = a.stage_root / lib.lstrip('/')
        target = destdir / lib.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(physical, target)
    overlap = tmp / 'empty-stage' / str(a.expected_library).lstrip('/')
    overlap.parent.mkdir(parents=True, exist_ok=True)
    overlap.write_bytes(b'not a Mach-O')
    out, resolved = run(tmp / 'empty-stage', destdir)
    assert not out and str(a.expected_library) in resolved, (out, resolved)
print('PASS: staged Mach-O provider, logical metadata and no active-prefix fallback')
