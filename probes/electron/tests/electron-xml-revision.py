#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check the verified XML revision transition used by reconfigure."""
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
options = SimpleNamespace(shared_xml=True, host_prefix=host, sysroot=target)
old_env = {'EMBERBSD_XML_SOURCE_SHA256': 'a'*64}; env = {'EMBERBSD_XML_SOURCE_SHA256': 'b'*64}
def arguments(revision):
    result = {}
    for provider, package in (('xml', 'libxml2-2.15.4'), ('xslt', 'libxslt-1.1.45')):
        for role, prefix in (('host', str(host)), ('target', str(target/'usr/pkg'))):
            version = 0 if provider == 'xml' else revision
            suffix = ('nb'+str(version)) if version else ''
            stem = 'emberbsd_'+provider+'_'+role
            result[stem+'_library'] = prefix+'/lib/'+provider+'.so'
            result[stem+'_inputs'] = [prefix+'/include/'+provider+'.h', prefix+'/lib/'+provider+'.so',
                *[prefix+'/pkgdb/'+package+suffix+'/'+name for name in ('+BUILD_INFO','+BUILD_VERSION','+CONTENTS')]]
    return result
old = arguments(5); new = arguments(6)
expected = {k for k in old if k.endswith('_inputs')}
assert b.xml_activation_args(options, old_env, env, old, new) == expected
assert b.xml_activation_args(options, old_env, old_env, old, old) == set()
def reject(changed, previous=old, current_env=env):
    try: b.xml_activation_args(options, old_env, current_env, previous, changed)
    except (ValueError, TypeError): return
    raise AssertionError('accepted incompatible XML revision')
for key in ('emberbsd_xslt_host_library', 'emberbsd_xslt_target_library'):
    candidate=copy.deepcopy(new); candidate[key] += '.foreign'; reject(candidate)
for key in ('emberbsd_xslt_host_inputs', 'emberbsd_xslt_target_inputs'):
    candidate=copy.deepcopy(new); candidate[key].append('/foreign/header.h'); reject(candidate)
    candidate=copy.deepcopy(new); candidate[key].pop(); reject(candidate)
    candidate=copy.deepcopy(new); candidate[key][-1]=candidate[key][-1].replace('/pkgdb/', '/foreign/pkgdb/'); reject(candidate)
    candidate=copy.deepcopy(new); candidate[key]=[p.replace('1.1.45nb6','1.1.46nb6') for p in candidate[key]]; reject(candidate)
    candidate=copy.deepcopy(new); candidate[key]=[p.replace('1.1.45nb6','1.1.45nb4') for p in candidate[key]]; reject(candidate)
    candidate=copy.deepcopy(new); candidate[key]=[p.replace('1.1.45nb6','1.1.45nb7') for p in candidate[key]]; reject(candidate)
reject(old)  # a changed identity without a revision advance is not evidence
reject(new, current_env={'EMBERBSD_XML_SOURCE_SHA256':'bad'})
try: b.xml_activation_args(options, {'EMBERBSD_XML_SOURCE_SHA256':'bad'}, env, old, new)
except ValueError: pass
else: raise AssertionError('accepted invalid old identity')
candidate=copy.deepcopy(new); candidate['emberbsd_xslt_host_inputs'].append([]); reject(candidate)
candidate=copy.deepcopy(new); candidate['emberbsd_xslt_host_inputs'].append(candidate['emberbsd_xslt_host_inputs'][-1]); reject(candidate)
candidate=copy.deepcopy(new); candidate['emberbsd_xslt_host_inputs'].remove(str(host)+'/include/xslt.h'); reject(candidate)
print('PASS: verified XML revision update and incompatible input rejection')
