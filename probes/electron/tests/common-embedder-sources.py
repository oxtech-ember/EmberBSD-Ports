#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check selection and identity for common Node and Perfetto sources."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_electron', owner / 'electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
with tempfile.TemporaryDirectory(prefix='electron-common-sources-') as tmp:
    root = Path(tmp); ports = root / 'ports'; perfetto = root / 'perfetto-owner'; v8_owner = root / 'v8-owner'
    for path in (ports / 'scripts/source-inputs/node/source.py', perfetto / 'scripts/source-inputs/perfetto/source.py', v8_owner / 'scripts/source-inputs/v8/source.py'):
        path.parent.mkdir(parents=True); path.touch()
    options = SimpleNamespace(ports_source=ports, sdk_source=root/'sdk', git=Path('/usr/bin/git'),
        protobuf_source=root/'protobuf', node_source=root/'node', node_pkgsrc=root/'node-export',
        perfetto_source=root/'perfetto', perfetto_ports_source=perfetto,
        perfetto_archive=root/'perfetto.tar.gz', perfetto_patch=root/'patch',
        v8_source=root/'v8', v8_ports_source=v8_owner, v8_pkgsrc=root/'v8-export')
    state = {'node': 'first', 'perfetto': 'first', 'v8': 'first'}
    source_environments = []
    class Process:
        @staticmethod
        def capture(cmd, *, env):
            name = next(name for name in state if name + '/source.py' in ' '.join(cmd))
            source_environments.append(dict(env))
            return SimpleNamespace(stdout=json.dumps({'tree_sha256': state[name]}).encode())
    env = {}
    with patch.dict('os.environ') as clean_environment:
        clean_environment.pop('EMBER_PREPARED_SOURCE_CACHE', None)
        values = build.common_embedder_sources(options, {'process': Process()},
            SimpleNamespace(tool=lambda _: '/selected/python'), env)
    assert all('EMBER_PREPARED_SOURCE_CACHE' not in captured for captured in source_environments)
    with patch.dict('os.environ', {'EMBER_PREPARED_SOURCE_CACHE': '/cache/fixture'}):
        cached_env = {}
        cached_values = build.common_embedder_sources(options, {'process': Process()},
            SimpleNamespace(tool=lambda _: '/selected/python'), cached_env)
    assert all(captured['EMBER_PREPARED_SOURCE_CACHE'] == '/cache/fixture'
               for captured in source_environments[-3:])
    assert 'EMBER_PREPARED_SOURCE_CACHE' not in cached_env
    assert cached_values == values and cached_env == env
    assert values['node_path'] == '//third_party/electron_node' and values['node_shared_perfetto']
    assert values['node_config_gn_root_target'] == '//electron'
    assert values['node_config_gn_root_pattern'] == '//electron:electron_dist_zip'
    assert all(values['node_shared_' + name] for name in build.NODE_SHARED_FEATURES)
    assert values['node_use_ffi'] and values['node_simdutf_include_from_target'] and values['use_system_simdutf']
    before = env.copy(); state['node'] = 'changed'; after = {}
    build.common_embedder_sources(options, {'process': Process()}, SimpleNamespace(tool=lambda _: '/selected/python'), after)
    assert before['EMBERBSD_NODE_SOURCE_SHA256'] != after['EMBERBSD_NODE_SOURCE_SHA256']
    assert before['EMBERBSD_PERFETTO_SOURCE_SHA256'] == after['EMBERBSD_PERFETTO_SOURCE_SHA256']
    assert before['EMBERBSD_V8_SOURCE_SHA256'] == after['EMBERBSD_V8_SOURCE_SHA256']
    options.node_pkgsrc = None
    try: build.common_embedder_sources(options, {'process': Process()}, SimpleNamespace(tool=lambda _: '/selected/python'), {})
    except ValueError: pass
    else: raise AssertionError('incomplete common Node accepted')
print('common embedder source selection, changed identity and partial input controls PASS')
