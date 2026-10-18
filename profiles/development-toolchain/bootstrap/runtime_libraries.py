# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; GCC runtime selection and completed-stage guards.
from pathlib import Path
from emberbsd_sdk import inventory, paths
from host import require, manifests
from runtime import LIBRARIES, SELECTIONS, field


def selected(gomp=False, atomic=False):
    names = ['libgcc', 'libstdc++'] + (['libgomp'] if gomp else []) + (['libatomic'] if atomic else [])
    return ','.join(names), [LIBRARIES[name] for name in names]


def check_prior(work, selection, resume):
    inputs = (Path(work) / 'inputs.txt').read_text()
    claims = [line for line in inputs.splitlines(keepends=True) if line.startswith('runtime_libraries=')]
    require(len(claims) <= 1 and (not claims or claims[0].endswith('\n')), 'Duplicate or unterminated runtime library selection')
    prior = field(inputs, 'runtime_libraries') if claims else SELECTIONS[0]
    require(prior in SELECTIONS, 'Unsupported prior runtime library selection')
    extension = prior != selection
    if extension:
        require(resume == 'runtime' and set(prior.split(',')) < set(selection.split(',')), 'Runtime extension cannot remove an existing library; requires --resume-runtime')
    return extension


def verify_completed_stage(work):
    work = Path(work)
    for name in ('build-success', 'stage.sha256', 'stage.symlinks'):
        paths.regular_file(work / name)
    require((work / 'build-success').read_text() == 'runtime-only-bootstrap\n', 'Invalid completed runtime marker')
    tree = inventory.snapshot_tree(work / 'stage')
    checksums = ''.join(sorted(record['sha256'] + '  ./' + name + '\n' for name, record in tree.items() if record['kind'] == 'file'))
    links = ''.join('./' + name + '\t' + record['target'] + '\n' for name, record in tree.items() if record['kind'] == 'link')
    require(checksums and checksums == (work / 'stage.sha256').read_text() and links == (work / 'stage.symlinks').read_text(), 'Completed stage inventory or hashes changed')
