#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Selected flatc ownership and native ELF runtime inputs come from SDK."""
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
    calls=[]
    def capture(command,env):
        return SimpleNamespace(stdout=(b'flatbuffers-25.12.19.1\n' if '-E' in command else b'flatc version 25.12.19\n'))
    def trace(*args, **kwargs):
        calls.append((args,kwargs)); return [str(tool),str(package/'+CONTENTS')]
    sdk={'process':SimpleNamespace(capture=capture),'host_prefix':SimpleNamespace(validate_host_executable=lambda *a,**k:None),
         'native_generator_runtime':SimpleNamespace(NATIVE_GENERATOR_RUNTIME_API=1,runtime_inputs=trace)}
    native=SimpleNamespace(host={'os':'NetBSD','cpu':'x86_64'},path=str(prefix/'bin'))
    options=SimpleNamespace(host_prefix=prefix,host_buildlink_pkgsrc=root/'export')
    selected=module.common_flatc(options,sdk,native,{})
    assert selected['emberbsd_flatc']==str(tool) and calls[0][0][3]==[str(package)]
    assert selected['emberbsd_flatc_inputs']==sorted([str(tool),str(package/'+CONTENTS'),str(header)])
    header.write_text('#define FLATBUFFERS_VERSION_MAJOR 24\n#define FLATBUFFERS_VERSION_MINOR 12\n#define FLATBUFFERS_VERSION_REVISION 19\n')
    try:
        module.common_flatc(options,sdk,native,{})
    except ValueError:
        pass
    else:
        raise AssertionError('flatc/header version mismatch accepted')
print('PASS: native flatc delegates ELF runtime ownership to selected SDK')
