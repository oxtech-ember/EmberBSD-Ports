#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise existing SUBST old/new replay and transaction recovery."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--sdk-source', required=True, type=Path)
p.add_argument('--patch', required=True, type=Path)
a = p.parse_args()
helper = Path(__file__).resolve().parents[1] / 'stage-local-patch-refresh.py'
with tempfile.TemporaryDirectory(prefix='existing-subst-test-') as tmp:
    root = Path(tmp).resolve()
    def setup(name):
        base = root / name
        recipe = base / 'pkgsrc/cat/demo'
        previous = base / 'previous'
        for d in (recipe / 'patches', previous / 'patches'):
            d.mkdir(parents=True)
        (base / 'pkgsrc/mk').mkdir()
        (base / 'pkgsrc/mk/bsd.prefs.mk').write_text('# framework\n')
        work = base / 'work'
        source = work / 'demo-1'
        source.mkdir(parents=True)
        archive = base / 'demo-1.tar.xz'
        with tarfile.open(archive, 'w:xz') as tar:
            for n, data in [('demo-1/input', b'base @PREFIX@\n'), ('demo-1/third', b'third @PREFIX@\n')]:
                entry = tarfile.TarInfo(n)
                entry.size = len(data)
                entry.mode = 0o644
                tar.addfile(entry, io.BytesIO(data))
        old = b'--- input\n+++ input\n@@ -1 +1 @@\n-base @PREFIX@\n+old @PREFIX@\n'
        new = b'--- input\n+++ input\n@@ -1 +1 @@\n-base @PREFIX@\n+new @PREFIX@\n'
        data = archive.read_bytes()
        rows = (f'BLAKE2s ({archive.name}) = {hashlib.blake2s(data).hexdigest()}\n'
                f'SHA512 ({archive.name}) = {hashlib.sha512(data).hexdigest()}\n'
                f'Size ({archive.name}) = {len(data)} bytes\n')
        for d, patch in ((recipe, new), (previous, old)):
            (d / 'Makefile').write_text('# demo\n')
            (d / 'Makefile.common').write_text('# shared\n')
            (d / 'patches/patch-a').write_bytes(patch)
            (d / 'distinfo').write_text(rows + f'SHA1 (patch-a) = {hashlib.sha1(patch).hexdigest()}\n')
        (work / '.patch_done').write_text(str(recipe / 'patches/patch-a') + '\n')
        (work / '.subst_rewrite_done').write_text('input\nthird\n')
        (source / 'input').write_bytes(b'old /prefix\n')
        (source / 'third').write_bytes(b'third /prefix\n')
        (source / 'sibling.o').write_bytes(b'object')
        db = base / 'sys/usr/pkg/pkgdb/demo-1nb1'
        db.mkdir(parents=True)
        (db / '+BUILD_VERSION').write_text(''.join(f'cat/demo/{n}: {hashlib.sha256((previous / n).read_bytes()).hexdigest()}\n' for n in ('Makefile', 'Makefile.common', 'distinfo', 'patches/patch-a')))
        vals = {'WRKDIR': str(work), 'WRKSRC': str(source), 'PATCH': str(a.patch),
                'PATCH_ARGS': f'-d {source} -E -p0 --batch --forward -V simple -z .orig',
                'DISTDIR': str(base), 'DIST_SUBDIR': '', 'DISTFILES': archive.name, 'DISTNAME': 'demo-1',
                'PKG_DBDIR': '/usr/pkg/pkgdb', 'CROSS_DESTDIR': str(base / 'sys'),
                'PKGBASE': 'demo', 'PKGVERSION_NOREV': '1', 'PATCHFILES': '',
                'PATCHDIR': str(recipe / 'patches'), 'DISTINFO_FILE': str(recipe / 'distinfo'),
                'EXTRACT_ONLY': archive.name, 'EXTRACT_USING': 'bsdtar', 'EXTRACT_SUFX': '.tar.xz',
                'EXTRACT_CMD': '/selected/bsdtar', 'EXTRACT_ENV': 'env',
                'EXTRACT_BEFORE_ARGS': '-xf', 'EXTRACT_AFTER_ARGS': '', 'LOCALPATCHES': '', 'META_PACKAGE': '',
                'SUBST_CLASSES': 'rewrite', 'SUBST_STAGE.rewrite': 'pre-configure',
                'SUBST_FILES.rewrite': 'input third', 'SUBST_VARS.rewrite': '',
                'SUBST_SED.rewrite': '-e replace', 'SUBST_FILTER_CMD.rewrite': '/selected/sed -e replace',
                'SUBST_SKIP_TEXT_CHECK.rewrite': 'no', 'SUBST_NOOP_OK.rewrite': 'no',
                '_SUBST_COOKIE.rewrite': str(work / '.subst_rewrite_done'), 'PKG_FAIL_REASON': '',
                '.MAKE.MAKEFILES': f'{recipe}/Makefile {recipe}/Makefile.common ../../mk/bsd.prefs.mk'}
        config = base / 'vars.json'
        config.write_text(json.dumps(vals))
        fake = base / 'bmake'
        fake.write_text('''#!''' + sys.executable + '''\nimport json,pathlib,sys\nv=json.loads(pathlib.Path(''' + repr(str(config)) + ''').read_text());args=sys.argv[1:];old='-f' in args
for arg in args:
 if arg.startswith('VARNAMES='):
  names=arg[9:].split()
  if names[0]=='PKG_FAIL_REASON':
   with pathlib.Path(''' + repr(str(base / 'metadata-queries')) + ''').open('a') as log: log.write(('old' if old else 'new')+'\\n')
  print('\\n'.join((''' + repr(str(previous / 'Makefile') + ' ' + str(previous / 'Makefile.common') + ' ../../mk/bsd.prefs.mk') + ''' if old and n=='.MAKE.MAKEFILES' else v[n]) for n in names));sys.exit()
if 'pre-patch' in args or 'post-patch' in args or 'pre-extract' in args or 'post-extract' in args:sys.exit()
if 'configure-clean' in args:
 flag=pathlib.Path(''' + repr(str(base / 'fail-clean')) + ''')
 if flag.exists():flag.unlink();sys.exit(8)
 pathlib.Path(''' + repr(str(base / 'configure-clean')) + ''').write_text('done')
 sys.exit()
if 'subst-rewrite' in args:
 d=pathlib.Path(next(x[7:] for x in args if x.startswith('WRKSRC=')))
 c=pathlib.Path(next(x.split('=',1)[1] for x in args if x.startswith('_SUBST_COOKIE.rewrite=')))
 for n in ('input','third'):
  f=d/n;f.write_bytes(f.read_bytes().replace(b'@PREFIX@',b'/prefix'))
 c.write_text('input\\nthird\\n');sys.exit()
sys.exit(3)
''')
        fake.chmod(0o755)
        command = [sys.executable, '-B', str(helper), '--sdk-source', str(a.sdk_source),
                   '--bmake', str(fake), '--recipe', str(recipe), '--expected-work', str(work),
                   '--previous-recipe', str(previous), '--refresh-subst', 'rewrite']
        return base, work, source, command, previous
    base, work, source, command, previous = setup('ok')
    third_time = (source / 'third').stat().st_mtime_ns
    object_time = (source / 'sibling.o').stat().st_mtime_ns
    cookie = (work / '.subst_rewrite_done').read_bytes()
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert (source / 'input').read_bytes() == b'new /prefix\n'
    assert (source / 'third').stat().st_mtime_ns == third_time
    assert (source / 'sibling.o').stat().st_mtime_ns == object_time
    assert (work / '.subst_rewrite_done').read_bytes() == cookie
    base, work, source, command, previous = setup('configure-pre-hook')
    config = base / 'vars.json'
    values = json.loads(config.read_text())
    values['SUBST_STAGE.rewrite'] = 'do-configure-pre-hook'
    config.write_text(json.dumps(values))
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert (source / 'input').read_bytes() == b'new /prefix\n'
    assert (work / '.subst_rewrite_done').read_text() == 'input\nthird\n'
    base, work, source, command, previous = setup('post-configure-rejected')
    config = base / 'vars.json'
    values = json.loads(config.read_text())
    values['SUBST_STAGE.rewrite'] = 'post-configure'
    config.write_text(json.dumps(values))
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'unsupported existing SUBST files or stage' in result.stderr
    assert (source / 'input').read_bytes() == b'old /prefix\n'
    base, work, source, command, previous = setup('retry')
    (base / 'fail-clean').write_text('once')
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert (work / '.emberbsd-patch-refresh.json').exists()
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert (source / 'input').read_bytes() == b'new /prefix\n'
    assert not (work / '.emberbsd-patch-refresh.json').exists()
    for name, target in [('foreign', 'input'), ('unmodified-third', 'third')]:
        base, work, source, command, previous = setup(name)
        (source / target).write_bytes(b'foreign\n')
        result = subprocess.run(command, capture_output=True, text=True)
        assert result.returncode != 0 and 'differs' in result.stderr
    base, work, source, command, previous = setup('wrong-cookie')
    (work / '.subst_rewrite_done').write_text('foreign\n')
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0 and 'cookie differs' in result.stderr
    base, work, source, command, previous = setup('foreign-old-include')
    (previous / 'Makefile.common').write_text('foreign\n')
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'included recipe input differs' in result.stderr
    base, work, source, command, previous = setup('current-include-config-only')
    (base / 'pkgsrc/cat/demo/Makefile.common').write_text('# changed configure dependency only\n')
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert (base / 'configure-clean').is_file()
    base, work, source, command, previous = setup('old-include-fallback')
    current = base / 'pkgsrc/cat/demo/Makefile.common'
    current.write_text('# changed current include\n')
    fake = base / 'bmake'
    fake.write_text(fake.read_text().replace(str(previous / 'Makefile.common'), str(current)))
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'included recipe input differs' in result.stderr
    assert (source / 'input').read_bytes() == b'old /prefix\n'
    base, work, source, command, previous = setup('changed-source-var')
    fake = base / 'bmake'
    fake.write_text(fake.read_text().replace("else v[n]) for n in names", "else ('foreign' if old and n=='EXTRACT_CMD' else v[n])) for n in names"))
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'source preparation inputs changed' in result.stderr
    base, work, source, command, previous = setup('changed-extract-hook')
    fake = base / 'bmake'
    fake.write_text(fake.read_text().replace("if 'pre-patch' in args or 'post-patch' in args or 'pre-extract' in args or 'post-extract' in args:sys.exit()", "if 'pre-extract' in args or 'post-extract' in args:\n if old: print('foreign extract')\n sys.exit()\nif 'pre-patch' in args or 'post-patch' in args:sys.exit()"))
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'extraction hooks changed' in result.stderr
    base, work, source, command, previous = setup('custom-extract')
    (previous / 'Makefile.common').write_text('do-extract:\n\ttrue\n')
    db = base / 'sys/usr/pkg/pkgdb/demo-1nb1/+BUILD_VERSION'
    data = db.read_text().splitlines()
    db.write_text('\n'.join(('cat/demo/Makefile.common: ' + hashlib.sha256((previous / 'Makefile.common').read_bytes()).hexdigest()) if x.startswith('cat/demo/Makefile.common:') else x for x in data) + '\n')
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'custom do-extract' in result.stderr
    base, work, source, command, previous = setup('changed-during-replay')
    fake = base / 'bmake'
    fake.write_text(fake.read_text().replace("if 'subst-rewrite' in args:", "if 'subst-rewrite' in args:\n pathlib.Path(" + repr(str(base / 'pkgsrc/cat/demo/Makefile.common')) + ").write_text('changed during replay')"))
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'recipe input changed during source replay' in result.stderr
    assert (source / 'input').read_bytes() == b'old /prefix\n'
    base, work, source, command, previous = setup('plain-previous')
    config = base / 'vars.json'
    values = json.loads(config.read_text())
    values['SUBST_CLASSES'] = ''
    config.write_text(json.dumps(values))
    (source / 'input').write_bytes(b'old @PREFIX@\n')
    command = command[:-2]
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert (base / 'configure-clean').is_file()
    assert (source / 'input').read_bytes() == b'new @PREFIX@\n'
    base, work, source, command, previous = setup('changed-hook')
    fake = base / 'bmake'
    text = fake.read_text().replace("if 'pre-patch' in args or 'post-patch' in args or 'pre-extract' in args or 'post-extract' in args:sys.exit()", "if 'pre-patch' in args or 'post-patch' in args:\n if old: print('foreign hook')\n sys.exit()\nif 'pre-extract' in args or 'post-extract' in args:sys.exit()")
    fake.write_text(text)
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'changed patch hooks' in result.stderr
    base, work, source, command, previous = setup('changed-unselected-subst')
    config = base / 'vars.json'
    values = json.loads(config.read_text())
    values['SUBST_CLASSES'] = 'rewrite another'
    for attribute in ('STAGE', 'FILES', 'VARS', 'SED', 'FILTER_CMD', 'SKIP_TEXT_CHECK', 'NOOP_OK'):
        values['SUBST_' + attribute + '.another'] = values['SUBST_' + attribute + '.rewrite']
    values['_SUBST_COOKIE.another'] = values['_SUBST_COOKIE.rewrite']
    config.write_text(json.dumps(values))
    fake = base / 'bmake'
    text = fake.read_text().replace("else v[n]) for n in names", "else ('different' if old and n=='SUBST_FILTER_CMD.another' else v[n])) for n in names")
    fake.write_text(text)
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode and 'previous SUBST configuration changed' in result.stderr
    assert (base / 'metadata-queries').read_text().splitlines() == ['old', 'new']
print('PASS: existing SUBST replay, exact inputs, cookie, recovery and mtimes')
