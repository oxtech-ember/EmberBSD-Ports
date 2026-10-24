#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD; AI-assisted explicit exporter integration.
"""Export the tracked LXQt overlay inside its admitted source controller."""

import importlib.util
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True


def exporter_module(root):
    spec = importlib.util.spec_from_file_location('ports_exporter', root / 'scripts/prepare-pkgsrc.py')
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    return exporter


def export_lxqt(root, destination, *, selection, runner, scratch):
    """Reuse one SDK selection, expected-command runner and caller-owned work."""
    root, destination = Path(root), Path(destination)
    source = root / 'probes/lxqt/recipes'
    tracked = set(runner([*selection.command('git'), '-C', str(root), 'ls-files',
                          '--', 'probes/lxqt/recipes']).decode().splitlines())
    files = sorted(p for p in source.rglob('*') if p.is_file())
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('The LXQt overlay must not contain symbolic links')
    if any(p.relative_to(root).as_posix() not in tracked for p in files):
        raise ValueError('Commit every LXQt recipe file before export')
    exporter_module(root).export_pkgsrc(root, destination, selection=selection,
                                       runner=runner, scratch=scratch)
    for path in files:
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    receipt = {
        'ports': runner([*selection.command('git'), '-C', str(root), 'rev-parse', 'HEAD']).decode().strip(),
        'overlay': [p.relative_to(source).as_posix() for p in files],
    }
    (destination / 'EMBERBSD-LXQT-RECIPES.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    # The common CLI refuses until SDK owns an exact source-export stage.
    # An accepted metadata, grep or relocation plan cannot admit this overlay.
    sys.exit(exporter_module(Path(__file__).resolve().parents[2]).main())
