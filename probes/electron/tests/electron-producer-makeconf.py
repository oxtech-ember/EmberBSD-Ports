#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check producer selection when inputs are supplied only by MAKECONF."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

bmake, pkgsrc, base = sys.argv[1:4]
owner = Path(__file__).resolve().parents[1] / '../../pkgsrc/devel/electron44'
recipe = (owner / 'Makefile').read_text()
assert recipe.index('.include "../../mk/bsd.prefs.mk"') < recipe.index('.include "producer.mk"')
required = ('WORKSPACE PORTS_SOURCE SDK_SOURCE HOST_PREFIX COMPILER_PREFIX SYSROOT WORK GIT '
            'LOCK_ROOT LINK_CONTEXT TARGET PYTHON NODE_SOURCE NODE_PKGSRC V8_SOURCE '
            'V8_PORTS_SOURCE V8_PKGSRC PERFETTO_SOURCE PERFETTO_PORTS_SOURCE '
            'PERFETTO_ARCHIVE PERFETTO_PATCH PROTOBUF_SOURCE PROTOBUF_PORTS_SOURCE '
            'PROTOBUF_ARCHIVE PROTOBUF_PATCH ML_RUY_SOURCE ML_PTHREADPOOL_SOURCE ML_GEMMLOWP_SOURCE '
            'ML_FARMHASH_SOURCE ML_ML_DTYPES_SOURCE ML_NEON2SSE_SOURCE ML_FXDIV_SOURCE ML_FFT2D_SOURCE '
            'ML_LITERT_SOURCE ML_OPENXLA_SOURCE ML_PATCH ML_PKGSRC_EXPORT ML_PORTS_SOURCE ML_EXPORT_PATCH ML_RUY_ARCHIVE ML_PTHREADPOOL_ARCHIVE '
            'ML_GEMMLOWP_ARCHIVE ML_FARMHASH_ARCHIVE ML_ML_DTYPES_ARCHIVE ML_NEON2SSE_ARCHIVE '
            'ML_FXDIV_ARCHIVE ML_FFT2D_ARCHIVE ML_LITERT_ARCHIVE ML_OPENXLA_ARCHIVE').split()
with tempfile.TemporaryDirectory(prefix='electron-producer-makeconf-') as temp:
    root = Path(temp)
    for item in Path(pkgsrc).resolve().iterdir():
        if item.name != 'devel':
            (root / item.name).symlink_to(item, target_is_directory=item.is_dir())
    package = root / 'devel/electron44'
    package.mkdir(parents=True)
    (package / 'producer.mk').symlink_to((owner / 'producer.mk').resolve())
    conf = root / 'mk.conf'
    prefix = Path(bmake).resolve().parent.parent
    lines = ['.include "' + str(Path(base).resolve()) + '"',
             'LOCALBASE= ' + str(prefix), 'PKG_DBDIR= ' + str(prefix / 'pkgdb'),
             'PKGSRC_COMPILER= clang', 'CLANGBASE= ' + str(prefix)]
    lines += ['EMBERBSD_ELECTRON_' + name + '= /selected/' + name.lower() for name in required]
    lines += ['EMBERBSD_ELECTRON_MACOS_MINIMUM= 14.0', 'EMBERBSD_ELECTRON_SHARED_ICU= yes']
    conf.write_text('\n'.join(lines) + '\n')
    env = {'PATH': os.environ['PATH'], 'HOME': temp, 'TMPDIR': temp, 'MAKECONF': str(conf)}
    def run(early):
        (package / 'Makefile').write_text('DISTNAME= electron-fixture-1\nCATEGORIES= devel\nDISTFILES=\nLICENSE= mit\nFAIL_MSG= echo FAIL\nDO_NADA= :\n' +
            ('.include "../../mk/bsd.prefs.mk"\n' if early else '') +
            '.include "producer.mk"\n' +
            ('' if early else '.include "../../mk/bsd.prefs.mk"\n') +
            '.include "../../mk/bsd.pkg.mk"\n')
        result = subprocess.run([bmake, '-C', str(package), '-n', 'ember-electron-check-inputs'],
                                env=env, text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
        check = result.stdout
        args = subprocess.run([bmake, '-C', str(package), '-v', '_EMBER_ELECTRON_ARGS'],
                              env=env, text=True, capture_output=True, check=True).stdout
        return check, args
    old_check, old_args = run(False)
    new_check, new_args = run(True)
    assert 'FAIL' in old_check and '--macos-minimum' not in old_args
    assert 'FAIL' not in new_check and '--macos-minimum' in new_args and '--shared-icu' in new_args
    # Fetch/checksum remain independent of producer selectors.
    conf.write_text('\n'.join(lines[:5]) + '\n')
    for target in ('fetch', 'checksum'):
        result = subprocess.run([bmake, '-C', str(package), '-n', target], env=env,
                                text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
        assert 'Set EMBERBSD_ELECTRON_' not in result.stdout + result.stderr
print('PASS: MAKECONF producer selections are visible before parse-time checks')
