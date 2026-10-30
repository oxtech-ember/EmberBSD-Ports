#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the Git-fingerprinted pkgsrc export stage.
"""Usage: pkgsrc-export-stage.py NEW_WORK GIT PATCH

A fixture Ports repository holds the real stage script and a small exporter
that counts its runs. The stage must be reused for unrelated commits and
rebuilt for a change of any export input or of the pinned pkgsrc gitlink.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

if len(sys.argv) != 4:
    raise SystemExit(__doc__)
work, git, patch = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
assert work.is_absolute() and not os.path.lexists(work)
root = Path(__file__).resolve().parents[3]
fixture = work / 'ports'
(fixture / 'scripts').mkdir(parents=True)
(fixture / 'pkgsrc/cross/demo').mkdir(parents=True)
(fixture / 'profiles/demo/recipe').mkdir(parents=True)
shutil.copy2(root / 'scripts/pkgsrc-export-stage.py', fixture / 'scripts/pkgsrc-export-stage.py')
runs = work / 'runs'
(fixture / 'scripts/prepare-pkgsrc.py').write_text(f'''
import os, subprocess, sys
from pathlib import Path

def configuration(root, *, include_manifests=False):
    root = Path(root)
    return [('cross/demo', root / 'profiles/demo/recipe')], [], [], [], []

if __name__ == '__main__':
    destination, git = Path(sys.argv[1]), sys.argv[sys.argv.index('--git') + 1]
    root = Path(__file__).resolve().parents[1]
    pin = subprocess.run([git, '-C', str(root), 'ls-files', '--stage', 'upstream/pkgsrc'],
                         check=True, capture_output=True, text=True).stdout.split()[1]
    destination.mkdir()
    (destination / 'EMBERBSD-PKGSRC-REVISION').write_text(pin + '\\n')
    with open({str(runs)!r}, 'a') as stream:
        stream.write('run\\n')
''')
(fixture / 'pkgsrc/export.conf').write_text('recipe\tprofiles/demo/recipe\tcross/demo\n')
(fixture / 'pkgsrc/cross/demo/Makefile').write_text('# demo\n')
(fixture / 'profiles/demo/recipe/Makefile').write_text('# recipe\n')
(fixture / 'README').write_text('fixture\n')


def run(*args, check=True):
    return subprocess.run(list(args), cwd=fixture, capture_output=True, text=True, check=check,
                          env=dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.org',
                                   GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.org'))


def commit(message):
    # The gitlink has no checkout here; keep its index entry as staged.
    run(git, 'add', '-A', '--', '.', ':(exclude)upstream')
    run(git, 'commit', '-q', '-m', message)


def pin(value):
    run(git, 'update-index', '--add', '--cacheinfo', '160000,' + value * 40 + ',upstream/pkgsrc')


run(git, 'init', '-q')
pin('a')
commit('fixture')
stages = work / 'stages'
stage = [sys.executable, '-B', str(fixture / 'scripts/pkgsrc-export-stage.py')]


def prepare():
    result = run(*stage, 'prepare', str(stages), '--git', git, '--patch', patch, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def count():
    return len(runs.read_text().splitlines()) if runs.exists() else 0


first = prepare()
assert not first['reused'] and count() == 1, first
assert Path(first['directory']) == stages / first['fingerprint']
assert (Path(first['directory']) / 'pkgsrc/EMBERBSD-PKGSRC-REVISION').read_text() == 'a' * 40 + '\n'
assert [p.name for p in stages.iterdir()] == [first['fingerprint']], 'no partial stage is left'
again = prepare()
assert again == dict(first, reused=True) and count() == 1, again

# A Ports commit outside the export inputs keeps the fingerprint.
(fixture / 'README').write_text('changed\n')
commit('unrelated')
assert prepare() == dict(first, reused=True) and count() == 1

# Every export input changes it: the overlay tree, a recipe outside it,
# the exporter itself and the pinned gitlink.
seen = {first['fingerprint']}
for label, change in [('overlay', lambda: (fixture / 'pkgsrc/cross/demo/Makefile').write_text('# two\n')),
                      ('recipe', lambda: (fixture / 'profiles/demo/recipe/new.mk').write_text('X=1\n')),
                      ('exporter', lambda: (fixture / 'scripts/prepare-pkgsrc.py').write_text(
                          (fixture / 'scripts/prepare-pkgsrc.py').read_text() + '# changed\n')),
                      ('gitlink', lambda: pin('b'))]:
    before = count()
    change()
    commit(label)
    result = prepare()
    assert not result['reused'] and result['fingerprint'] not in seen and count() == before + 1, (label, result)
    seen.add(result['fingerprint'])
assert (stages / result['fingerprint'] / 'pkgsrc/EMBERBSD-PKGSRC-REVISION').read_text() == 'b' * 40 + '\n'

# Uncommitted inputs have no Git fingerprint and are refused.
(fixture / 'profiles/demo/recipe/Makefile').write_text('# dirty\n')
refused = run(*stage, 'prepare', str(stages), '--git', git, '--patch', patch, check=False)
assert refused.returncode == 1 and 'uncommitted pkgsrc export inputs' in refused.stderr, refused.stderr
run(git, 'checkout', '--', 'profiles/demo/recipe/Makefile')
(fixture / '.gitignore').write_text('work/\n')
commit('ignore work')
(fixture / 'pkgsrc/cross/demo/work').mkdir()
refused = run(*stage, 'prepare', str(stages), '--git', git, '--patch', patch, check=False)
assert refused.returncode == 1 and 'cross/demo/work' in refused.stderr, refused.stderr
(fixture / 'pkgsrc/cross/demo/work').rmdir()

# A stage whose receipt or tree differs from its name is refused.
receipt = stages / result['fingerprint'] / 'pkgsrc-stage.json'
saved = receipt.read_text()
receipt.write_text(saved.replace('b' * 40, 'c' * 40))
refused = run(*stage, 'prepare', str(stages), '--git', git, '--patch', patch, check=False)
assert refused.returncode == 1 and 'receipt differs' in refused.stderr, refused.stderr
receipt.write_text(saved)
assert prepare()['reused']
print('pkgsrc export stage: reuse and invalidation checked')
