#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise retry classification and the actual shell workdir transition."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

script = Path(__file__).resolve().parents[1] / 'cross-bulk.sh'
classifier = script.parent / 'cross-bulk-workdir.py'
text = script.read_text()
fn = text[text.index('prepare_wrkdir()\n'):text.index('\n# Retire successful', text.index('prepare_wrkdir()\n'))]
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    work = root / 'work'
    work.mkdir()
    obj = work / 'kept.o'
    obj.write_bytes(b'object')
    cookie = work / '.extract_done'
    rundir = root / 'run'
    rundir.mkdir()
    # Stands in for pkgsrc: lists (.depends) and resolves (.rdepends) the
    # dependencies into the files named on the command line.
    bmk = ('bmk() {\n'
           '    printf "%s\\n" "$*" > "$run/bmk-args"\n'
           '    [ "$FIXTURE_RESOLVE" = ok ] || { echo "fixture: dependency resolve failed" >&2; return 1; }\n'
           '    for a; do case $a in _DEPENDS_FILE=*) d=${a#*=};; _RDEPENDS_FILE=*) r=${a#*=};; esac; done\n'
           '    printf "%s\\n" "$FIXTURE_DEPENDS" > "$d"\n'
           '    eval "last=\\${$#}"\n'
           '    [ "$last" != "$r" ] || printf "%s\\n" "$FIXTURE_RDEPENDS" > "$r"\n'
           '}\n')
    resolved = dict(FIXTURE_RESOLVE='ok', FIXTURE_DEPENDS='full\texpat>=2.10.0\t../../textproc/expat',
                    FIXTURE_RDEPENDS='full\texpat>=2.10.0\texpat-2.10.0')
    def run(identity, current, version):
        if identity is None:
            cookie.unlink(missing_ok=True)
        else:
            cookie.write_text(identity + '\n')
        shell = root / 'case.sh'
        shell.write_text('#!/bin/sh\nhost_python="$1"; base=fixture; version="$2"; name="$3"\n'
                         'run="$5"; PKGSRCDIR=/ports\n'
                         'retire() { mv "$1" "$1.retired"; }\n'
                         'cmp() { if [ "$FIXTURE_CMP" = error ]; then echo "cmp: simulated comparison error" >&2; return 2; fi; command cmp "$@"; }\n' + bmk + fn +
                         '\nprepare_wrkdir "$4" job t/fixture USE_CROSS_COMPILE=no\n')
        return subprocess.run(['/bin/sh', str(shell), sys.executable, version, current, str(work),
                               str(rundir)], cwd=script.parent, capture_output=True, text=True,
                              env=dict(os.environ, **resolved))
    # The function resolves the classifier alongside $0.
    (root / 'cross-bulk-workdir.py').write_bytes(classifier.read_bytes())
    obj.unlink()
    assert run(None, 'fixture-1.0nb2', '1.0').returncode == 0
    obj.write_bytes(b'object')
    before = (obj.stat().st_ino, obj.stat().st_mtime_ns)
    assert run('fixture-1.0nb1', 'fixture-1.0nb1', '1.0').returncode == 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    # patch-cookie records applied paths, or is empty when no patches apply.
    # A configure failure leaves this cookie without .configure_done.
    patch_cookie = work / '.patch_done'
    for applied in ('', '/ports/cat/fixture/patches/patch-source\n'):
        patch_cookie.write_text(applied)
        assert run('fixture-1.0nb1', 'fixture-1.0nb1', '1.0').returncode == 0
        assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
        assert run('fixture-1.0nb1', 'fixture-1.0nb2', '1.0').returncode != 0
        assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert run('fixture-1.0nb1', 'fixture-1.0nb2', '1.0').returncode != 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    (work / '.build_done').write_text('fixture-1.0nb2\n')
    assert run('fixture-1.0nb1', 'fixture-1.0nb2', '1.0').returncode == 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert run(None, 'fixture-1.0nb2', '1.0').returncode != 0 and obj.exists()
    assert not (rundir / 'bmk-args').exists()
    # A kept WRKDIR whose dependencies pkgsrc listed and resolved is kept
    # only while the same bmake arguments still list and resolve them alike.
    (work / '.depends').write_text(resolved['FIXTURE_DEPENDS'] + '\n')
    assert run('fixture-1.0nb2', 'fixture-1.0nb2', '1.0').returncode == 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    args = (rundir / 'bmk-args').read_text().split()
    assert args[:3] == ['-C', '/ports/t/fixture', 'USE_CROSS_COMPILE=no'] and args[-1].endswith('.depends')
    (work / '.rdepends').write_text(resolved['FIXTURE_RDEPENDS'] + '\n')
    assert run('fixture-1.0nb2', 'fixture-1.0nb2', '1.0').returncode == 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert (rundir / 'bmk-args').read_text().split()[-1].endswith('.rdepends')
    assert sorted(p.name for p in rundir.iterdir()) == ['bmk-args']
    def retired_by(**change):
        resolved.update(change)
        result = run('fixture-1.0nb2', 'fixture-1.0nb2', '1.0')
        assert result.returncode == 0 and not work.exists(), result.stderr
        assert 'kept WRKDIR resolved other dependencies' in result.stderr
        retired = root / 'work.retired'
        assert (retired / 'kept.o').read_bytes() == b'object'
        retired.rename(work)
        assert sorted(p.name for p in rundir.iterdir()) == ['bmk-args']
        resolved.update(FIXTURE_RESOLVE='ok', FIXTURE_DEPENDS=(work / '.depends').read_text().rstrip('\n'),
                        FIXTURE_RDEPENDS=(work / '.rdepends').read_text().rstrip('\n'))
    # The dependency was replaced by a newer revision since the resolution.
    retired_by(FIXTURE_RDEPENDS='full\texpat>=2.10.0\texpat-2.10.0nb1')
    # The recipe lists another dependency now.
    retired_by(FIXTURE_DEPENDS='full\texpat>=2.10.0nb1\t../../textproc/expat')
    # Resolver error: keep WRKDIR, surface the cause, and stop (do not rebuild).
    resolved.update(FIXTURE_RESOLVE='no')
    result = run('fixture-1.0nb2', 'fixture-1.0nb2', '1.0')
    assert result.returncode != 0 and work.exists(), result.stderr
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert 'kept WRKDIR dependency check failed' in result.stderr
    assert 'fixture: dependency resolve failed' in result.stderr
    assert 'kept WRKDIR resolved other dependencies' not in result.stderr
    assert not (root / 'work.retired').exists()
    resolved.update(FIXTURE_RESOLVE='ok')
    # cmp status 2 is a comparison error: keep WRKDIR and stop (do not treat as change).
    resolved['FIXTURE_CMP'] = 'error'
    result = run('fixture-1.0nb2', 'fixture-1.0nb2', '1.0')
    assert result.returncode != 0 and work.exists(), result.stderr
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert 'kept WRKDIR dependency check failed: cmp status 2' in result.stderr
    assert 'kept WRKDIR resolved other dependencies' not in result.stderr
    assert not (root / 'work.retired').exists()
    resolved.pop('FIXTURE_CMP', None)
    assert run('fixture-1.0nb2', 'fixture-2.0', '2.0').returncode == 0
    assert not work.exists() and (root / 'work.retired/kept.o').read_bytes() == b'object'
print('PASS: retry preserves objects, unknown fails closed, dependency change retires, resolver/cmp error keeps and stops')
