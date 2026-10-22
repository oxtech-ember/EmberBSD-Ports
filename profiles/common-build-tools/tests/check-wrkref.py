#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkgsrc work-reference append controls.
# This test uses a stock fragment. It does not build or register packages.
from pathlib import Path

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time

args = sys.argv[1:]
if len(args) != 2:
    raise SystemExit('Usage: check-wrkref.py STOCK_PKGSRC NEW_WORK')
pkgsrc = Path(args[0]).resolve()
root = Path(args[1])
root.mkdir()
root = root.resolve()
profile = Path(__file__).resolve().parents[1]
python = sys.executable
bmake = shutil.which(os.environ.get('BMAKE', 'bmake'))
mksh = shutil.which(os.environ.get('MKSH', 'mksh'))
patch = shutil.which(os.environ.get('PATCH', 'patch'))
assert bmake and mksh and patch, 'Set BMAKE, MKSH and PATCH to available executables'
source = pkgsrc / 'mk/check/check-wrkref.mk'
original = source.read_bytes()
assert b'_check_wrkref_output_open' not in original, 'Input already has the patch'
(root / 'stock.mk').write_bytes(original)
patched = root / 'patched'
(patched / 'mk/check').mkdir(parents=True)
(patched / 'mk/check/check-wrkref.mk').write_bytes(original)
process = subprocess.run([patch, '-F0', '-p1', '-i', str(profile / 'patches/pkgsrc-wrkref-append-stream.patch')], cwd=patched, capture_output=True, timeout=30)
(root / 'patch.stdout').write_bytes(process.stdout)
(root / 'patch.stderr').write_bytes(process.stderr)
assert process.returncode == 0, process.stderr
(root / 'candidate.mk').write_bytes((patched / 'mk/check/check-wrkref.mk').read_bytes())
(root / 'candidate.patch').write_bytes((profile / 'patches/pkgsrc-wrkref-append-stream.patch').read_bytes())
work = root / 'controls'
work.mkdir()
stage = work / 'stage'
prefix = '/usr/pkg'
files = ['share/alpha', 'share/a name', 'share/skip-one', 'share/omit1', 'share/omega', 'share/alpha']
prior = '/usr/pkg/share/prior'
for relative in set(files + ['share/prior']):
    p = stage / 'usr/pkg' / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('A real /forbidden/build reference\n')
observe = work / 'observe-echo.py'
observe.write_text(r"""from pathlib import Path
import json
import os
import sys

path = Path(os.environ['ERROR_TMP'])
if path.is_file():
    actual = os.fstat(1)
    expected = path.stat()
    if (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino):
        with open(os.environ['OPEN_TRACE'], 'a') as trace:
            trace.write(json.dumps({'offset': os.lseek(1, 0, os.SEEK_CUR)}) + '\n')
os.write(1, (' '.join(sys.argv[1:]) + '\n').encode())
""")
xargs = work / 'observe-xargs.py'
xargs.write_text(r"""from pathlib import Path
import os
import subprocess
import sys

payload = sys.stdin.buffer.read()
Path(os.environ['LIST_CAPTURE']).write_bytes(payload)
process = subprocess.run(['/usr/bin/xargs'] + sys.argv[1:], input=payload)
sys.exit(process.returncode)
""")
makefile = work / 'control.mk'
makefile.write_text(""".SHELL: name=ksh path=${MKSH}
.SILENT:
RUN= set -e;
STEP_MSG= :
SHCOMMENT= echo >/dev/null '***'
SORT= /usr/bin/sort
EGREP= /usr/bin/grep -E
RM= /bin/rm
TRUE= :
PREFIX= /usr/pkg
CHECK_WRKREF= extra
CHECK_WRKREF_EXTRA_DIRS= /forbidden
CHECK_WRKREF_SKIP= share/skip* /usr/pkg/share/omit?
PKGNAME= wrkref-control
PKG_FILELIST_CMD= /bin/cat ${INPUT:Q}
.include "${FRAGMENT}"
error-check:
.PHONY: error-check
""")
results = {}
for case in ['normal', 'append', 'printing-comment', 'parent-fd', 'empty', 'empty-existing', 'skipped', 'open-failure', 'empty-open-denied', 'skipped-open-denied', 'read-failure', 'write-failure']:
    pair = {}
    for variant in ['stock', 'candidate']:
        out = work / (case + '-' + variant)
        out.mkdir()
        error = out / 'error'
        error.mkdir()
        tmp = error / '_check-wrkref.tmp'
        errorfile = error / '_check-wrkref'
        trace = out / 'opens.jsonl'
        capture = out / 'list.txt'
        source = out / 'input.txt'
        input_files = [] if case in {'empty', 'empty-existing', 'empty-open-denied', 'read-failure'} else ['/usr/pkg/share/skip-one', '/usr/pkg/share/omit1'] if case in {'skipped', 'skipped-open-denied'} else ['/usr/pkg/' + p for p in files]
        if case != 'read-failure':
            source.write_text(''.join((p + '\n' for p in input_files)))
        if case == 'append':
            tmp.write_text(str(stage) + prior + '\n')
        if case == 'empty-existing':
            tmp.touch()
        if case == 'open-failure':
            tmp.mkdir()
        if case in {'empty-open-denied', 'skipped-open-denied'}:
            errorfile.touch()
            error.chmod(0o500)
        env = dict(os.environ, LC_ALL='C', ERROR_TMP=str(tmp), OPEN_TRACE=str(trace), LIST_CAPTURE=str(capture))
        echo = 'echo' if case == 'write-failure' else shlex.join([python, str(observe)])
        command = [bmake, '-r', '-f', str(makefile), 'MKSH=' + mksh, 'FRAGMENT=' + str(root / (variant + '.mk')), 'ERROR_DIR=' + str(error), 'DESTDIR=' + str(stage), 'INPUT=' + str(source), 'ECHO=' + echo, 'XARGS=' + shlex.join([python, str(xargs)]), '_check-wrkref']
        # Apply the file-size limit inside mksh after make starts the recipe.
        parent_fd_log = out / 'parent-fd.log'
        if case == 'printing-comment':
            command.insert(-1, 'SHCOMMENT=echo COMMENT')
        if case == 'parent-fd':
            command.insert(-1, 'PARENT_FD_LOG=' + str(parent_fd_log))
            command.insert(-1, "RUN=exec 3>>\"${PARENT_FD_LOG}\"; trap 'echo parent-fd-ok >&3' EXIT; set -e;")
        if case == 'write-failure':
            command.insert(-1, 'RUN=set -e; ulimit -f 0;')
        start = time.monotonic()
        try:
            p = subprocess.run(
                command, env=env, cwd=work, capture_output=True, timeout=60)
        finally:
            error.chmod(0o700)
        elapsed = time.monotonic() - start
        (out / 'stdout').write_bytes(p.stdout)
        (out / 'stderr').write_bytes(p.stderr)
        data = capture.read_bytes() if capture.exists() else None
        diagnostic = errorfile.read_bytes() if errorfile.exists() else None
        offsets = [json.loads(s)['offset'] for s in trace.read_text().splitlines()] if trace.exists() else []
        state = 'directory' if tmp.is_dir() else 'file' if tmp.is_file() else 'absent'
        pair[variant] = dict(exit=p.returncode, list=data.decode() if data is not None else None, diagnostic=diagnostic.decode() if diagnostic is not None else None, tmp_state=state, tmp_bytes=tmp.stat().st_size if tmp.is_file() else None, argv=command, offsets=offsets, elapsed_seconds=elapsed, stderr=p.stderr.decode(), stdout=p.stdout.decode(), parent_fd=parent_fd_log.read_text() if parent_fd_log.exists() else None)
    old = pair['stock']
    new = pair['candidate']
    for field in ['exit', 'list', 'diagnostic', 'tmp_state', 'tmp_bytes']:
        assert old[field] == new[field], (case, field, old[field], new[field])
    if case in {'normal', 'append', 'printing-comment', 'parent-fd'}:
        assert old['exit'] == 0, (case, 'normal check failed')
        assert old['stdout'] == new['stdout'], (case, 'stdout differs')
        if case == 'printing-comment':
            assert old['stdout'].count('COMMENT [') == 4
        if case == 'parent-fd':
            assert old['parent_fd'] == new['parent_fd'] == 'parent-fd-ok\n'
        expected = ''.join((str(stage) + s + '\n' for s in sorted(input_files) if '/skip' not in s and '/omit' not in s))
        if case == 'append':
            expected = str(stage) + prior + '\n' + expected
        assert old['list'] == expected, (case, 'list oracle')
        assert 'still have references' in old['diagnostic'] and 'share/alpha' in old['diagnostic']
        assert len(old['offsets']) == 4 and old['offsets'] == [0] * 4, (case, 'original open descriptions', old['offsets'])
        assert len(new['offsets']) == 4 and new['offsets'][0] == 0 and all((x > 0 for x in new['offsets'][1:])), (case, 'one append description', new['offsets'])
    if case in {'empty', 'skipped', 'empty-open-denied', 'skipped-open-denied'}:
        assert old['exit'] == 0 and old['tmp_state'] == 'absent' and (old['list'] is None)
    if case == 'empty-existing':
        assert old['exit'] == 0 and old['tmp_state'] == 'file' and (old['tmp_bytes'] == 0) and (old['list'] is None)
    if case in {'open-failure', 'write-failure'}:
        assert old['exit'] != 0
    if case == 'write-failure':
        assert old['tmp_state'] == 'file' and new['tmp_state'] == 'file' and (old['tmp_bytes'] == 0) and (new['tmp_bytes'] == 0), ('write control did not reach target', pair)
    if case == 'read-failure':
        assert 'No such file' in old['stderr'] and 'No such file' in new['stderr']
    results[case] = pair
    print('PASS', case, old['exit'], old['elapsed_seconds'], new['elapsed_seconds'], flush=True)
result = dict(cases=results, source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [root / 'stock.mk', root / 'candidate.mk', root / 'candidate.patch']}, scope='Real pkgsrc check-wrkref fragment, BSD make, mksh, actual sort/grep/xargs. ECHO descriptor offsets observe repeated opens versus one shared append description. Left-input read failure status is unchanged from upstream; this is not a new failure-propagation claim.')
(work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS all controls', flush=True)
