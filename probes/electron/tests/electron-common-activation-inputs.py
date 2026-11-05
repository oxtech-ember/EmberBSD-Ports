#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Legacy provider activation must not record uninstalled projections."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

native = SimpleNamespace(tool=lambda name: '/selected/' + name, host={'os':'NetBSD','cpu':'x86_64'})
sdk = {'process':SimpleNamespace(capture=lambda *a, **k:SimpleNamespace(stdout=b'one\ntwo\nthree\n'))}
opts = SimpleNamespace(work=Path('/work'), sdk_source=Path('/sdk'), lock_root=Path('/lock'),
    link_context=Path('/context'), compiler_family='gcc', host_compiler_family='gcc',
    sysroot=Path('/sysroot'), host_prefix=Path('/prefix'), workspace=Path('/workspace'),
    activate_common_providers=True)
empty = lambda *a, **k: {}
def comp(options, sdk, native, environment, buildlink):
    environment['EMBERBSD_COMPRESSION_SOURCE_SHA256']='compression'
    return {'emberbsd_brotli_native_tool':'/selected/brotli'}
def boring(options, sdk, native, environment):
    environment['EMBERBSD_BORINGSSL_SOURCE_SHA256']='boring'
patches = dict(_native_inputs=lambda *a:(native,{'EMBERBSD_HOST_NODE':'/selected/node','EMBERBSD_HOST_TYPESCRIPT':'/selected/tsc','EMBERBSD_HOST_ROLLUP':'/selected/rollup'},{}), devtools_provider_identity=lambda *a:'devtools',
    target_inputs=lambda *a:{k:'/selected/'+k for k in ('cc','cxx','ar','nm','readelf')},
    native_runtime_binding=lambda *a:None, arguments=empty, host_buildlink=lambda *a:'/selected',
    common_abseil=empty, common_icu=empty, common_re2=empty, common_media_libraries=empty,
    common_compression=comp, common_protobuf=empty, protoc_selection=lambda *a:None,
    common_undici=empty, common_embedder_sources=empty, common_ml_sources=empty,
    common_boringssl_source=boring, common_v8_metagen=empty, clang_resource_version=lambda *a:'1',
    common_node_configure=empty,
    local_module=lambda *a:SimpleNamespace(apply=lambda env, version:(env,{})))
with patch.multiple(m, **patches):
    _, env, args = m.producer_inputs(opts, sdk)
    assert 'EMBERBSD_COMPRESSION_SOURCE_SHA256' not in env
    assert 'EMBERBSD_BORINGSSL_SOURCE_SHA256' not in env
    assert 'emberbsd_brotli_native_tool' not in args
    opts.ml_ruy_source=Path('/prepared/ml')
    _, env, args = m.producer_inputs(opts, sdk)
    assert 'EMBERBSD_COMPRESSION_SOURCE_SHA256' not in env
    assert 'EMBERBSD_BORINGSSL_SOURCE_SHA256' not in env
    assert 'emberbsd_brotli_native_tool' not in args
    opts.activate_common_providers=False
    _, env, args = m.producer_inputs(opts, sdk)
    assert env['EMBERBSD_COMPRESSION_SOURCE_SHA256']=='compression'
    assert env['EMBERBSD_BORINGSSL_SOURCE_SHA256']=='boring'
    assert args['emberbsd_brotli_native_tool']=='/selected/brotli'
# The whole reconfigure entry must reject the mixed stage before loading or
# mutating the saved configuration; no AttributeError from skipped selections.
opts.activate_common_providers=True
with patch.object(m, 'keep_going_limit'), patch.object(m, 'load_sdk', side_effect=AssertionError('unexpected SDK access')):
    try: m.reconfigure(opts)
    except ValueError as error: assert 'separate stage' in str(error)
    else: raise AssertionError('mixed legacy and ML stages accepted')
print('PASS: legacy activation defers identities until normal provider selection')
