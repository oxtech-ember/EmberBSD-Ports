#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check common ICU shim masks without changing the upstream source."""
import importlib.util
from pathlib import Path
import tempfile
owner=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source_view',owner/'electron44/files/protobuf-source-view.py')
view=importlib.util.module_from_spec(spec);spec.loader.exec_module(view)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); source=root/'source'; unbundle=source/'build/linux/unbundle';unbundle.mkdir(parents=True)
    (source/'.gn').touch();(unbundle/'replace_gn_files.py').write_text("REPLACEMENTS = {'icu': 'third_party/icu/BUILD.gn'}\n");(unbundle/'icu.gn').write_text('shim_headers("icu") { root_path = "source/common" headers = [ "unicode/data.h" ] }\n')
    original=source/'third_party/icu';(original/'source/common/unicode').mkdir(parents=True)
    (original/'BUILD.gn').write_text('bundled');(original/'source/common/unicode/data.h').write_text('original')
    normal=view.create(source,None,root/'normal');assert (normal/'third_party/icu').is_symlink();view.verify(source,None,root/'normal')
    selected=view.create(source,None,root/'selected',system_icu=True);view.verify(source,None,root/'selected',system_icu=True)
    masked=selected/'third_party/icu/source/common/unicode/data.h';assert not masked.exists()
    assert (original/'source/common/unicode/data.h').read_text()=='original'
    masked.write_text('wrong')
    try:view.verify(source,None,root/'selected',system_icu=True)
    except ValueError:pass
    else:raise AssertionError('masked header accepted')
print('PASS: common ICU view masks preserve original source')
