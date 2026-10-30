#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check common RE2 shim masks without changing the upstream source."""
import importlib.util
from pathlib import Path
import tempfile
owner=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('source_view',owner/'electron44/files/protobuf-source-view.py')
view=importlib.util.module_from_spec(spec);spec.loader.exec_module(view)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); source=root/'source'; unbundle=source/'build/linux/unbundle';unbundle.mkdir(parents=True)
    (source/'.gn').touch();(unbundle/'replace_gn_files.py').write_text("REPLACEMENTS = {'re2': 'third_party/re2/BUILD.gn'}\n");(unbundle/'re2.gn').write_text('shim_headers("re2_shim") { root_path = "src" headers = [ "re2/re2.h" ] }\n')
    original=source/'third_party/re2';(original/'src/re2').mkdir(parents=True)
    (original/'BUILD.gn').write_text('bundled');(original/'src/re2/re2.h').write_text('original')
    normal=view.create(source,None,root/'normal');assert (normal/'third_party/re2').is_symlink();view.verify(source,None,root/'normal')
    selected=view.create(source,None,root/'selected',system_re2=True);view.verify(source,None,root/'selected',system_re2=True)
    masked=selected/'third_party/re2/src/re2/re2.h';assert not masked.exists()
    assert (original/'src/re2/re2.h').read_text()=='original'
    masked.write_text('wrong')
    try:view.verify(source,None,root/'selected',system_re2=True)
    except ValueError:pass
    else:raise AssertionError('masked header accepted')
print('PASS: common RE2 view masks preserve original source')
