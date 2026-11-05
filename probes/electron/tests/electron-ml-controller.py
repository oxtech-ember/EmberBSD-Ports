#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise first and repeated common ML source/header activation ordering."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',owner); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); work=root/'work'; (work/'source-view').mkdir(parents=True)
    calls=[]
    def verify(*args, **kwargs): calls.append(('verify',tuple(kwargs.get('ml_names',())))); return work/'source-view/src'
    view=SimpleNamespace(verify=verify, _refresh_leaves=lambda *args: calls.append(('leaf-refresh',)) or work/'source-view/src')
    def ml_activate(*args, **kwargs):
        calls.append(('ml',kwargs['old_identities'])); args[7](); return work/'source-view/src'
    def header_activate(*args, **kwargs):
        calls.append(('headers',kwargs['old_identities'])); args[6](); return work/'source-view/src'
    ml=SimpleNamespace(NAMES=('litert','tflite'),activate=ml_activate,verify_view=lambda *args: calls.append(('ml-check',)))
    hdr=SimpleNamespace(NAMES=('eigen3','flatbuffers','fp16'),activate=header_activate,verify_view=lambda *args:calls.append(('header-check',)))
    modules={'electron_protobuf_source_view':view,'electron_ml_source_view':ml,'electron_header_source_view':hdr}
    o=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',
        ml_identities={'litert':'a'},ml_sources={},ml_sdk={'inventory':object(),'sourceprep':object()},
        ml_headers={name:{'identity':'a'} for name in hdr.NAMES},phase='reconfigure',activate_common_ml=True)
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert [x[0] for x in calls if x[0] in ('ml','headers')]==['ml','headers']
    assert ('verify',('litert','tflite')) in calls
    assert ('verify',('litert','tflite','eigen3','flatbuffers','fp16')) in calls
    calls.clear(); o.refresh_source_view=True
    o.old_ml_identities={'litert':'old'}; o.old_header_identities={name:'old' for name in hdr.NAMES}
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert [x[0] for x in calls].count('leaf-refresh') == 1
    assert [x[0] for x in calls].index('leaf-refresh') < [x[0] for x in calls].index('headers')
    # A resumed header transaction has already installed ML. Its owner
    # recovers the marker before requesting verification of that selection.
    calls.clear()
    marker = work / '.source-view.header-components-migration'
    marker.write_text('pending')
    def recovered_ml(*args, **kwargs):
        calls.append(('ml-recovered',))
    def recovered_headers(*args, **kwargs):
        marker.unlink()
        calls.append(('headers-recovered',))
        args[6]()
    ml.activate = recovered_ml; hdr.activate = recovered_headers
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert [x[0] for x in calls] == ['ml-recovered', 'headers-recovered', 'leaf-refresh', 'verify']
    ml.activate = ml_activate; hdr.activate = header_activate
    calls.clear(); o.activate_common_ml=False; o.old_ml_identities=o.ml_identities
    o.old_header_identities={name:'a' for name in hdr.NAMES}
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert calls == [('leaf-refresh',)]
print('PASS: ML and header transitions are ordered before view verification')
