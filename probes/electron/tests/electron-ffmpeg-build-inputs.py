#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Only the bundled provider prepares Chromium's legacy FFmpeg config."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('electron',owner)
e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
o=SimpleNamespace(workspace=Path('/workspace'),host_prefix=Path('/prefix'),target='amd64')
with patch.object(e,'ensure_lastchange'), patch.object(e,'ensure_host_dsymutil'), \
     patch.object(e,'require_rust_std'), patch.object(e,'ensure_ffmpeg_netbsd_config') as legacy:
    o.shared_ffmpeg=True; e.prepare_build_inputs(o,None,{},None); legacy.assert_not_called()
    o.shared_ffmpeg=False; e.prepare_build_inputs(o,None,{},None); legacy.assert_called_once_with(o.workspace)
print('PASS: shared FFmpeg skips bundled NetBSD config preparation')
