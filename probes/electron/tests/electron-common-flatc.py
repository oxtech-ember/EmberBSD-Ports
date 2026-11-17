#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Selected flatc ownership and its package inputs."""
import hashlib
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec=importlib.util.spec_from_file_location('controller',owner); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
with TemporaryDirectory() as temporary:
    root=Path(temporary).resolve(); prefix=root/'prefix'; db=prefix/'pkgdb'; package=db/'flatbuffers-25.12.19.1'; package.mkdir(parents=True)
    tool=prefix/'bin/flatc'; tool.parent.mkdir(); tool.write_text('tool'); tool.chmod(0o755)
    (package/'+CONTENTS').write_text('bin/flatc\ninclude/flatbuffers/base.h\n');
    header=prefix/'include/flatbuffers/base.h'; header.parent.mkdir(parents=True)
    header.write_text('#define FLATBUFFERS_VERSION_MAJOR 25\n#define FLATBUFFERS_VERSION_MINOR 12\n#define FLATBUFFERS_VERSION_REVISION 19\n'); (package/'+BUILD_INFO').write_text('PKGPATH=devel/flatbuffers\n')
    recipe=root/'export/devel/flatbuffers'; recipe.mkdir(parents=True); (recipe/'distinfo').write_text('source')
    digest=hashlib.sha256((recipe/'distinfo').read_bytes()).hexdigest()
    (package/'+BUILD_VERSION').write_text('devel/flatbuffers/distinfo: '+digest+'\n')
    def capture(command,env):
        owner = '-E' in command or '-Fe' in command
        return SimpleNamespace(stdout=(b'flatbuffers-25.12.19.1\n' if owner else b'flatc version 25.12.19\n'))
    sdk={'process':SimpleNamespace(capture=capture,CommandError=RuntimeError),'host_prefix':SimpleNamespace(validate_host_executable=lambda *a,**k:None)}
    native=SimpleNamespace(host={'os':'NetBSD','cpu':'x86_64'},path=str(prefix/'bin'))
    options=SimpleNamespace(host_prefix=prefix,host_buildlink_pkgsrc=root/'export')
    selected=module.common_flatc(options,sdk,native,{})
    assert selected['emberbsd_flatc']==str(tool)
    assert selected['emberbsd_flatc_inputs']==sorted([str(tool),str(header)]+
        [str(package/name) for name in ('+CONTENTS','+BUILD_INFO','+BUILD_VERSION')])
    header.write_text('#define FLATBUFFERS_VERSION_MAJOR 24\n#define FLATBUFFERS_VERSION_MINOR 12\n#define FLATBUFFERS_VERSION_REVISION 19\n')
    try:
        module.common_flatc(options,sdk,native,{})
    except ValueError:
        pass
    else:
        raise AssertionError('flatc/header version mismatch accepted')
print('PASS: native flatc inputs are its package metadata and version header')
