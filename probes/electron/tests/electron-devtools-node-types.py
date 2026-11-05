#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""DevTools GN inputs follow installed Node declaration files."""
import importlib.util
import json
from pathlib import Path
import tempfile

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('providers', owner / '../../pkgsrc/devel/electron44/files/node-providers.py')
providers = importlib.util.module_from_spec(spec); spec.loader.exec_module(providers)
with tempfile.TemporaryDirectory() as temporary:
    prefix = Path(temporary).resolve(); modules = prefix / 'lib/node_modules'
    for name in ('@types/node', 'undici-types'):
        root = modules / name; root.mkdir(parents=True)
        (root / 'package.json').write_text(json.dumps({'name': name, 'version': '1'}))
        (root / 'index.d.ts').write_text('export {}')
    old = providers.selected_node_type_inputs(modules, prefix)
    added = modules / '@types/node/new.d.ts'; added.write_text('export {}')
    new = providers.selected_node_type_inputs(modules, prefix)
    assert str(added) in new and len(new) == len(old) + 1
    added.unlink(); (modules / '@types/node/index.d.ts').unlink()
    try:
        providers.selected_node_type_inputs(modules, prefix)
        raise AssertionError('empty declarations accepted')
    except ValueError:
        pass
print('PASS: Node declaration inputs track selected provider files')
