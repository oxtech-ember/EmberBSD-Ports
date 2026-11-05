#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Only a complete first selection of verified provider identities is allowed."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', owner / '../../pkgsrc/devel/electron44/files/build-electron.py')
build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
opts = SimpleNamespace(activate_common_providers=True, shared_abseil=True, shared_icu=True,
                       shared_re2=True, shared_undici=True, protobuf_source=Path('/common'), work=Path('/work'))
env = {'EMBERBSD_PROTOBUF_SOURCE_SHA256': 'verified'}
for provider in ('ABSEIL', 'ICU', 'RE2'):
    for suffix in ('VERSION', 'SOURCE_SHA256'):
        env['EMBERBSD_SHARED_' + provider + '_' + suffix] = 'verified'
args = {name: 'selected' for name in ('emberbsd_abseil_host_headers', 'emberbsd_abseil_host_inputs',
    'emberbsd_abseil_target_headers', 'emberbsd_abseil_target_inputs', 'emberbsd_protobuf_native_prefix',
    'emberbsd_protobuf_target_prefix', 'emberbsd_protoc', 'emberbsd_protoc_runtime_inputs',
    'node_shared_undici_path', 'node_shared_undici_input',
    'emberbsd_icuuc_host_library', 'emberbsd_icuuc_target_library',
    'emberbsd_icui18n_host_library', 'emberbsd_icui18n_target_library',
    'emberbsd_re2_host_library', 'emberbsd_re2_target_library')}
args.update(emberbsd_common_protobuf=True, icu_use_data_file=False, v8_enable_temporal_systemicu=True)
env_allowed, args_allowed = build.common_activation_allowlist(opts, {}, env, {}, args)
assert env_allowed == set(env) and args_allowed == set(args)
assert build.common_activation_allowlist(opts, env, env, args, args) == (set(), set())
old_args = dict(args, emberbsd_protoc_runtime_inputs=['/selected/protoc'])
new_args = dict(args, emberbsd_protoc_runtime_inputs=['/selected/protoc', '/work/protoc-selection.json'])
assert build.common_activation_allowlist(opts, env, env, old_args, new_args) == (set(), set())
try:
    build.common_activation_allowlist(opts, env, env, old_args,
        dict(new_args, emberbsd_protoc_runtime_inputs=new_args['emberbsd_protoc_runtime_inputs'] + ['/foreign']))
except ValueError:
    pass
else:
    raise AssertionError('unrelated protoc input accepted on retry')
changed_env = dict(env, EMBERBSD_SHARED_RE2_VERSION='foreign')
try:
    build.common_activation_allowlist(opts, env, changed_env, args, args)
    raise AssertionError('changed retry identity accepted')
except ValueError:
    pass
for old_env, old_args, changed_opts in (({'EMBERBSD_SHARED_ABSEIL_VERSION':'foreign'}, {}, opts),
                                         ({}, {'emberbsd_protoc':'foreign'}, opts),
                                         ({}, {}, SimpleNamespace(**{**vars(opts), 'shared_re2':False})),
                                         ({'UNRELATED':'old'}, {}, opts),
                                         ({}, {'unrelated_gn':'old'}, opts)):
    try:
        build.common_activation_allowlist(changed_opts, old_env, env, old_args, args)
        raise AssertionError('incompatible activation accepted')
    except ValueError:
        pass
print('PASS: only complete first activation may change exact provider identities')
