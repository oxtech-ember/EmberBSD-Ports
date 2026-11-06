#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the real reconfigure candidate-to-source-view registry handoff."""
import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--owner', type=Path, default=Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py')
owner = parser.parse_args().owner
spec = importlib.util.spec_from_file_location('electron', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class ReachedSourceView(Exception): pass
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); work = root / 'work'; (work / 'out').mkdir(parents=True)
    (work / 'out/build.ninja').write_text('')
    (work / 'out/args.gn').write_text('')
    registry = root / 'verified-native-registry'; registry.mkdir()
    binding = root / 'binding'; binding.mkdir(); (binding / 'commands.json').write_text('{}')
    args = {'v8_prepared_source_receipt': '//v8/emberbsd-prepared-source.json',
            'v8_version_hash_salt_files': [], 'v8_version_hash_salt': ''}
    env = {'EMBERBSD_PROTOC_SELECTION_SHA256': 'a'*64, 'EMBERBSD_V8_SOURCE_SHA256': 'b'*64,
           'EMBERBSD_CONTROL_GIT': '/git', 'PATH': '/native',
           'GOCACHE': str(work / 'go-cache'), 'GOPATH': str(work / 'go-path')}
    (work / 'configuration.json').write_text(json.dumps({'source': str(root), 'sdk': str(root),
        'host_prefix': str(root), 'target': 'amd64', 'arguments': args, 'environment': env}))
    o = SimpleNamespace(work=work, workspace=root, sdk_source=root, ports_source=root, host_prefix=root,
        target='amd64', compiler_family='clang', git=Path('/git'), shared_vulkan=True,
        activate_common_ml=True, activate_common_providers=False, jobs=1, v8_source=root)
    native = SimpleNamespace(path='/native', tool=lambda name:'/native/'+name)
    sdk = {'sourceprep': SimpleNamespace(PREPARED_TREE_RECEIPT='receipt')}
    def inputs(candidate, sdk):
        candidate.vulkan_registry = registry
        candidate.protoc_selection = {}
        candidate.ml_identities = {'litert':'a'}; candidate.ml_sources = {}
        candidate.ml_headers = {}; candidate.media_header_selections = {}
        candidate.boringssl_identity = 'b'; candidate.boringssl_selected = {}
        candidate.compression_identity = 'c'
        return native, dict(env), dict(args)
    def source_view(options):
        assert getattr(options, 'vulkan_registry', None) == registry, 'verified Vulkan registry is missing'
        raise ReachedSourceView()
    noops = ('keep_going_limit','require_common_v8','require_common_node','require_common_perfetto',
             'require_common_dependencies','verify_source')
    returns = ('minizip_activation_args','xml_activation_args','ots_activation_args','codec_activation_args',
        'pdfium_activation_args','pffft_activation_args','expat_activation_args','cpuinfo_activation_args',
        'vulkan_activation_args','woff2_activation_args','openh264_activation_args','image_activation_args',
        'font_activation_args','additive_host_buildlink_relocation','additive_protoc_runtime_view',
        'additive_protoc_selection')
    patches = [patch.object(m, name, lambda *a,**k:None) for name in noops]
    patches += [patch.object(m, name, lambda *a,**k:set()) for name in returns]
    patches += [patch.object(m,'load_sdk',return_value=sdk),patch.object(m,'producer_inputs',side_effect=inputs),
        patch.object(m,'saved_binding_directory',return_value=binding),patch.object(m,'binding_identity',return_value={}),
        patch.object(m,'gn_arguments',return_value=''),patch.object(m,'common_activation_allowlist',return_value=(set(),set())),
        patch.object(m,'verified_swiftshader_disable',return_value=set()),patch.object(m,'verified_host_deployment_change',return_value=False),
        patch.object(m,'verified_node_source_refresh',return_value=False),patch.object(m,'selected_control_git',return_value='/git'),
        patch.object(m,'verified_node_configure_v8_path_change',return_value=False),
        patch.object(m,'bind_versioned',return_value={'cc':'/cc','cxx':'/cxx'}),patch.object(m,'gn_source',side_effect=source_view)]
    from contextlib import ExitStack
    with ExitStack() as stack:
        for item in patches: stack.enter_context(item)
        try: m.reconfigure(o)
        except ReachedSourceView: pass
        else: raise AssertionError('reconfigure did not reach source-view')
print('PASS: verified Vulkan registry propagated from candidate into reconfigure source-view')
