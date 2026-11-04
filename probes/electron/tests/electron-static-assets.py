#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Electron GN's actual default app asset list must exist in the selected prefix."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); workspace = root / 'workspace'; prefix = root / 'prefix'
    gn = workspace / 'src/electron/filenames.gni'; gn.parent.mkdir(parents=True)
    gn.write_text('filenames = {\n  default_app_octicon_sources = [\n    "node_modules/@primer/octicons/build/a.svg",\n  ]\n}\n')
    modules = prefix / 'lib/node_modules'; modules.mkdir(parents=True)
    options = SimpleNamespace(workspace=workspace, host_prefix=prefix)
    for existing in (False, True):
        asset = modules / '@primer/octicons/build/a.svg'
        if existing:
            asset.parent.mkdir(parents=True); asset.write_text('asset')
            build.require_electron_static_assets(options)
        else:
            try:
                build.require_electron_static_assets(options)
            except ValueError:
                pass
            else:
                raise AssertionError('missing provider accepted')
    asset.unlink()
    try:
        build.require_electron_static_assets(options)
    except ValueError:
        pass
    else:
        raise AssertionError('missing asset accepted')
print('PASS: selected provider and GN-listed assets are required')
