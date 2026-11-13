#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Revision-only updates must preserve each verified codec binding."""
import copy
import importlib.util
import tempfile
from pathlib import Path
from types import SimpleNamespace

source = Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron_build', source)
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
temp = tempfile.TemporaryDirectory(); root = Path(temp.name).resolve()
host = root/'native'; target = root/'target'; host.mkdir(); (target/'usr/pkg').mkdir(parents=True)
o = SimpleNamespace(shared_codecs=True, host_prefix=host, sysroot=target)
old_env = {'EMBERBSD_CODEC_SOURCE_SHA256': 'a'*64}; env = {'EMBERBSD_CODEC_SOURCE_SHA256': 'b'*64}
providers = (('dav1d','dav1d','1.5.4'), ('aom','libaom','3.15.2'), ('vpx','libvpx','1.17.0'), ('opus','libopus','1.6.1'), ('flac','flac','1.5.0'))
def arguments(vpx_revision, selected='vpx'):
    result = {'emberbsd_common_codecs': True}
    for provider, package, version in providers:
        for role, prefix in (('host', str(host)), ('target', str(target/'usr/pkg'))):
            stem='emberbsd_'+provider+'_'+role
            revision = 'nb'+str(vpx_revision) if provider == selected and vpx_revision else ''
            result[stem+'_libraries']=[prefix+'/lib/'+provider+'.so']
            result[stem+'_inputs']=[prefix+'/include/'+provider+'.h', prefix+'/lib/'+provider+'.so',
                *[prefix+'/pkgdb/'+package+'-'+version+revision+'/'+n for n in ('+BUILD_INFO','+BUILD_VERSION','+CONTENTS')]]
    return result
old=arguments(0); new=arguments(1)
assert b.codec_activation_args(o,old_env,env,old,new) == {'emberbsd_vpx_host_inputs','emberbsd_vpx_target_inputs'}
for provider, _, _ in providers:
    candidate = arguments(1, provider)
    assert b.codec_activation_args(o,old_env,env,old,candidate) == {
        'emberbsd_'+provider+'_host_inputs', 'emberbsd_'+provider+'_target_inputs'}
assert b.codec_activation_args(o,old_env,old_env,old,new) == set() # GN identity guard rejects changed inputs
assert b.codec_activation_args(o,old_env,old_env,old,old) == set()
def reject(candidate, previous=old, current_env=env, previous_env=old_env):
    try: b.codec_activation_args(o,previous_env,current_env,previous,candidate)
    except (ValueError, TypeError): return
    raise AssertionError('accepted incompatible codec revision')
for provider, package, version in providers:
    for role in ('host','target'):
        stem='emberbsd_'+provider+'_'+role
        for mode in ('header','library','foreign','partial','base','version','role','invalid','duplicate'):
            candidate=copy.deepcopy(new)
            key=stem+'_inputs'
            if mode == 'header': candidate[key].append('/foreign/header.h')
            if mode == 'library': candidate[stem+'_libraries'][0] += '.foreign'
            if mode == 'foreign': candidate[key][-1]=candidate[key][-1].replace('/pkgdb/','/foreign/pkgdb/')
            if mode == 'partial': candidate[key].pop()
            if mode == 'base': candidate[key]=[x.replace('/'+package+'-', '/foreign-') for x in candidate[key]]
            if mode == 'version': candidate[key]=[x.replace(package+'-'+version,package+'-9.9.9') for x in candidate[key]]
            if mode == 'role':
                old_dir=package+'-'+version+('nb1' if provider == 'vpx' else '')
                candidate[key]=[x.replace('/'+old_dir+'/', '/'+package+'-'+version+'nb9/') for x in candidate[key]]
            if mode == 'invalid': candidate[key].append([])
            if mode == 'duplicate': candidate[key].append(candidate[key][-1])
            reject(candidate)
reject(old)
reject(new, current_env={'EMBERBSD_CODEC_SOURCE_SHA256':'bad'})
reject(new, previous_env={'EMBERBSD_CODEC_SOURCE_SHA256':'bad'})
reject(arguments(0), previous=arguments(1))
print('PASS: verified codec revision update and incompatible bindings rejected')
