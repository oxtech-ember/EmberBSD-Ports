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
    media=SimpleNamespace(NAMES=('libyuv','libsrtp'), identity=lambda data,name:'a', verify_view=lambda *args:None)
    compression=SimpleNamespace(NAMES=('brotli','zstd'), verify_view=lambda *args:None)
    boring=SimpleNamespace(NAME='boringssl', verify_view=lambda *args:None)
    modules={'electron_boringssl_source_view':boring,'electron_compression_source_view':compression,'electron_protobuf_source_view':view,'electron_ml_source_view':ml,'electron_header_source_view':hdr, 'electron_media_header_view':media}
    o=SimpleNamespace(workspace=root/'workspace',work=work,protobuf_source=root/'protobuf',host_prefix=root/'host',
        ml_identities={'litert':'a'},ml_sources={},ml_sdk={'inventory':object(),'sourceprep':object()},
        ml_headers={name:{'identity':'a'} for name in hdr.NAMES}, media_header_selections={},
        old_media_header_identities={'libyuv':'a','libsrtp':'a'}, compression_identity='x', old_compression_identity='x', boringssl_identity='b', old_boringssl_identity='b', phase='reconfigure',activate_common_ml=True)
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert [x[0] for x in calls if x[0] in ('ml','headers')]==['ml','headers']
    assert ('verify',('litert','tflite','libyuv','libsrtp','boringssl','brotli','zstd')) in calls
    assert ('verify',('litert','tflite','eigen3','flatbuffers','fp16','libyuv','libsrtp','boringssl','brotli','zstd')) in calls
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
    # Ordinary build receives the already checked saved media identities.
    calls.clear(); o.phase='build'; o.refresh_source_view=False
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert calls == [('verify',('litert','tflite','eigen3','flatbuffers','fp16','libyuv','libsrtp','boringssl','brotli','zstd'))]
    # Initial configure retry may complete the additive media transaction.
    calls.clear(); o.phase='configure'; o.retry_configure=True
    o.old_media_header_identities=None
    def media_activate(*args, **kwargs):
        calls.append(('media',)); args[6](); return work/'source-view/src'
    media.activate=media_activate
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert ('media',) in calls
    # Compression activation follows the already-validated ML and media views.
    calls.clear(); o.phase='reconfigure'; o.retry_configure=False
    o.old_media_header_identities={'libyuv':'a','libsrtp':'a'}
    o.old_compression_identity=None
    def compression_activate(*args, **kwargs):
        calls.append(('compression',)); args[3](); return work/'source-view/src'
    compression.activate=compression_activate
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert ('compression',) in calls
    assert calls[-1] == ('verify',('litert','tflite','eigen3','flatbuffers','fp16','libyuv','libsrtp','boringssl','brotli','zstd'))
    # A configure retry may follow a completed projection before config save.
    calls.clear(); o.phase='configure'; o.retry_configure=True
    for name in compression.NAMES: (work/'source-view/src/third_party'/name).mkdir(parents=True)
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert not any(call[0]=='compression' for call in calls)
    assert calls[-1] == ('leaf-refresh',)
    # A pending compression marker is recovered by its owner before whole-view validation.
    calls.clear(); marker=work/'.source-view.compression-components-migration'; marker.write_text('pending')
    def recover_compression(*args, **kwargs):
        marker.unlink(); calls.append(('compression-recovered',)); args[3](); return work/'source-view/src'
    compression.activate=recover_compression
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert calls[0][0]=='compression-recovered' and not marker.exists()
    # Add FFmpeg to the saved two-component selection without touching it.
    calls.clear(); o.phase='reconfigure'; o.retry_configure=False; o.refresh_source_view=False
    o.old_compression_identity='x'; o.shared_ffmpeg=True; o.old_ffmpeg_identity=None
    def activate_ffmpeg(*args, **kwargs):
        assert args[4:] == (('ffmpeg',), 'ffmpeg-components')
        calls.append(('ffmpeg',)); args[3]()
    compression.activate=activate_ffmpeg
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert [call[0] for call in calls].count('ffmpeg') == 1
    assert any(call[0] == 'verify' and 'ffmpeg' in call[1] for call in calls)
    # Interrupted transaction is recovered before any whole-view check.
    calls.clear(); marker=work/'.source-view.ffmpeg-components-migration'; marker.write_text('pending')
    def recover_ffmpeg(*args, **kwargs):
        marker.unlink(); calls.append(('ffmpeg-recovered',))
    compression.activate=recover_ffmpeg
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert calls[0] == ('ffmpeg-recovered',) and 'ffmpeg' in calls[-1][1]
    # Completed FFmpeg projection is adopted only after strict verification
    # when GN failed before the configuration receipt was written.
    calls.clear(); ffmpeg=work/'source-view/src/third_party/ffmpeg'; ffmpeg.mkdir()
    (ffmpeg/'valid').write_text('verified wrapper')
    def verify_component(*args):
        if len(args) == 4 and args[3] == ('ffmpeg',):
            assert (ffmpeg/'valid').read_text() == 'verified wrapper', 'foreign FFmpeg view'
    compression.verify_view=verify_component
    compression.activate=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('projection rebuilt'))
    with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
        m.gn_source(o)
    assert any(call[0] == 'verify' and 'ffmpeg' in call[1] for call in calls)
    (ffmpeg/'valid').write_text('foreign')
    try:
        with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
            m.gn_source(o)
    except AssertionError as error:
        assert 'foreign FFmpeg view' in str(error)
    else:
        raise AssertionError('foreign completed projection accepted')
    # The saved old selection does not authorize adoption in build mode.
    (ffmpeg/'valid').write_text('verified wrapper'); o.phase='build'
    try:
        with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
            m.gn_source(o)
    except ValueError as error:
        assert 'requires reconfigure' in str(error)
    else:
        raise AssertionError('build adopted an unsaved projection')
    # Both initial configure retries can adopt the same strictly verified view.
    view._refresh_leaves=lambda *args: calls.append(('verify', tuple(args[3].get('ml_names',()))))
    view.complete_initial=lambda *args, **kwargs: calls.append(('verify', tuple(kwargs.get('ml_names',()))))
    for flag in ('retry_configure', 'resume_configure'):
        o.phase='configure'; o.retry_configure=False; o.resume_configure=False
        setattr(o, flag, True); calls.clear()
        with patch.object(m,'local_module',side_effect=lambda name,path:modules[name]):
            m.gn_source(o)
        assert any(call[0] == 'verify' and 'ffmpeg' in call[1] for call in calls)
print('PASS: ML and header transitions are ordered before view verification')
