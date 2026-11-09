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
    def classify(current, *, directory=work, package='fixture', upstream='1.0'):
        return subprocess.run([sys.executable, str(root / 'cross-bulk-workdir.py'),
                               str(directory), package, upstream, current],
                              capture_output=True, text=True)
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
        # A revision change alone cannot establish object incompatibility.
        refused = classify('fixture-1.0nb2')
        assert refused.returncode != 0 and 'revision changed' in refused.stderr, refused.stderr
        assert refused.stdout.strip() == ''
        assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    refused = classify('fixture-1.0nb2')
    assert refused.returncode != 0 and (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    # Exercise the real controller path, not just the classifier. Selecting
    # this package for a build must not silently turn an nbN bump into a clean.
    refused = run('fixture-1.0nb1', 'fixture-1.0nb2', '1.0')
    assert refused.returncode != 0 and 'revision changed' in refused.stderr, refused.stderr
    assert work.is_dir() and obj.read_bytes() == b'object'
    assert not (root / 'work.retired').exists()
    assert not (rundir / 'bmk-args').exists()
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    (work / '.build_done').write_text('fixture-1.0nb2\n')
    assert run('fixture-1.0nb1', 'fixture-1.0nb2', '1.0').returncode == 0
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert run(None, 'fixture-1.0nb2', '1.0').returncode != 0 and obj.exists()
    assert run('other-9.9', 'fixture-1.0nb2', '1.0').returncode != 0 and obj.exists()
    assert not (root / 'work.retired').exists()
    (work / '.package_done').write_text('not-an-identity\n')
    ambiguous = run('fixture-1.0nb1', 'fixture-1.0nb2', '1.0')
    assert ambiguous.returncode != 0 and work.exists() and 'revision changed' in ambiguous.stderr, ambiguous.stderr
    assert not (root / 'work.retired').exists()
    (work / '.package_done').unlink()
    css = root / 'cssparser'
    css.mkdir()
    (css / '.extract_done').write_text('cxx-rust-cssparser-0.1.0nb4\n')
    (css / '.package_done').write_text('cxx-rust-cssparser-0.1.0nb4\n')
    css_object = css / 'kept.o'
    css_object.write_bytes(b'compiled object')
    css_saved = {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
                 for p in css.iterdir()}
    reused = classify('cxx-rust-cssparser-0.1.0nb4', directory=css,
                      package='cxx-rust-cssparser', upstream='0.1.0')
    assert reused.returncode == 0 and reused.stdout.strip() == 'same', reused.stderr
    outside = classify('cxx-rust-cssparser-0.1.0nb5', directory=css,
                       package='cxx-rust-cssparser', upstream='0.1.0')
    assert outside.returncode != 0 and 'revision changed' in outside.stderr
    assert {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
            for p in css.iterdir()} == css_saved
    (css / '.extract_done').write_text('not a package identity\n')
    unknown = classify('cxx-rust-cssparser-0.1.0nb5', directory=css,
                       package='cxx-rust-cssparser', upstream='0.1.0')
    assert unknown.returncode != 0 and 'unknown package identity' in unknown.stderr
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
    def stopped_by(**change):
        saved = {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
                 for p in (obj, patch_cookie, work / '.build_done',
                           work / '.depends', work / '.rdepends')}
        resolved.update(change)
        result = run('fixture-1.0nb2', 'fixture-1.0nb2', '1.0')
        assert result.returncode != 0 and work.is_dir(), result.stderr
        assert 'dependency metadata changed; WRKDIR preserved' in result.stderr
        assert 'scoped' in result.stderr
        assert not (root / 'work.retired').exists()
        assert {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
                for p in saved} == saved
        assert sorted(p.name for p in rundir.iterdir()) == ['bmk-args']
        resolved.update(FIXTURE_RESOLVE='ok', FIXTURE_DEPENDS=(work / '.depends').read_text().rstrip('\n'),
                        FIXTURE_RDEPENDS=(work / '.rdepends').read_text().rstrip('\n'))
        return result
    # The dependency was replaced by a newer revision since the resolution.
    stopped_by(FIXTURE_RDEPENDS='full\texpat>=2.10.0\texpat-2.10.0nb1')
    # The recipe lists another dependency now.
    stopped_by(FIXTURE_DEPENDS='full\texpat>=2.10.0nb1\t../../textproc/expat')
    # A docs tool revision is not evidence that compiled objects are incompatible.
    old_tool = 'tool\tpy315-gi-docgen-[0-9]*\t../../devel/py-gi-docgen'
    old_resolved_tool = 'tool\tpy315-gi-docgen-[0-9]*\tpy315-gi-docgen-2026.1'
    for leaf, row in (('.depends', old_tool), ('.rdepends', old_resolved_tool)):
        with (work / leaf).open('a') as stream:
            stream.write(row + '\n')
    resolved.update(FIXTURE_DEPENDS=(work / '.depends').read_text().rstrip('\n'),
                    FIXTURE_RDEPENDS=(work / '.rdepends').read_text().rstrip('\n'))
    result = stopped_by(FIXTURE_DEPENDS=resolved['FIXTURE_DEPENDS'].replace(
                   'py315-gi-docgen-[0-9]*', 'py315-gi-docgen>=2026.1nb1'),
               FIXTURE_RDEPENDS=resolved['FIXTURE_RDEPENDS'].replace(
                   'py315-gi-docgen-[0-9]*', 'py315-gi-docgen>=2026.1nb1').replace(
                   '\tpy315-gi-docgen-2026.1', '\tpy315-gi-docgen-2026.1nb1'))
    assert '-' + old_tool in result.stderr
    assert '+' + old_tool.replace('py315-gi-docgen-[0-9]*', 'py315-gi-docgen>=2026.1nb1') in result.stderr
    assert '-' + old_resolved_tool in result.stderr
    assert ('+tool\tpy315-gi-docgen>=2026.1nb1\tpy315-gi-docgen-2026.1nb1') in result.stderr
    # Resolver error: keep WRKDIR, surface the cause, and stop (do not rebuild).
    resolved.update(FIXTURE_RESOLVE='no')
    result = run('fixture-1.0nb2', 'fixture-1.0nb2', '1.0')
    assert result.returncode != 0 and work.exists(), result.stderr
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert 'kept WRKDIR dependency check failed' in result.stderr
    assert 'fixture: dependency resolve failed' in result.stderr
    assert 'dependency metadata changed' not in result.stderr
    assert not (root / 'work.retired').exists()
    resolved.update(FIXTURE_RESOLVE='ok')
    # cmp status 2 is a comparison error: keep WRKDIR and stop (do not treat as change).
    resolved['FIXTURE_CMP'] = 'error'
    result = run('fixture-1.0nb2', 'fixture-1.0nb2', '1.0')
    assert result.returncode != 0 and work.exists(), result.stderr
    assert (obj.stat().st_ino, obj.stat().st_mtime_ns) == before
    assert 'kept WRKDIR dependency check failed: cmp status 2' in result.stderr
    assert 'dependency metadata changed' not in result.stderr
    assert not (root / 'work.retired').exists()
    resolved.pop('FIXTURE_CMP', None)
    assert run('fixture-1.0nb2', 'fixture-2.0', '2.0').returncode == 0
    assert not work.exists() and (root / 'work.retired/kept.o').read_bytes() == b'object'
print('PASS: retry preserves objects, revision-only and unknown changes preserve and stop, dependency changes preserve and stop, incompatible upstream version retires')
