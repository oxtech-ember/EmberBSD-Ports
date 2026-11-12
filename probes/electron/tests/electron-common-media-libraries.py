#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check owned, role-specific common media libraries without pkg-config."""
import importlib.util
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile, argparse, sys
parser=argparse.ArgumentParser();parser.add_argument('--sdk-source',type=Path,required=True);args=parser.parse_args();sys.path.insert(0,str(args.sdk_source.resolve()/'src'))
from emberbsd_sdk import paths as sdkpaths
spec_fixture=importlib.util.spec_from_file_location('stable_fixture',Path(__file__).with_name('stable-read-fixture.py'))
fixture=importlib.util.module_from_spec(spec_fixture);spec_fixture.loader.exec_module(fixture)

owner = Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); host = root/'host'; target = root/'sysroot/usr/pkg'; work = root/'context'
    work.mkdir(); paths = []
    for prefix, suffix in ((host, '.dylib'), (target, '.so')):
        for name, (pkgpath, lib, headers) in m.COMMON_MEDIA_LIBRARIES.items():
            package = prefix/'pkgdb'/(name+'-1.0'); package.mkdir(parents=True)
            (package/'+BUILD_INFO').write_text('PKGPATH='+pkgpath+'\n')
            (package/'+BUILD_VERSION').write_text('fixture\n')
            header = next(x for x in headers if x.endswith('/'))+'test.h'
            if name == 'libyuv': header = 'include/libyuv.h'
            libpath='lib/'+lib+suffix
            for entry in (header,libpath):
                path=prefix/entry; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('fixture')
            (package/'+CONTENTS').write_text(header+'\n@comment MD5:'+hashlib.md5(b'fixture').hexdigest()+'\n'+libpath+'\n')
            exported=root/'export'/pkgpath; exported.mkdir(parents=True,exist_ok=True); (exported/'distinfo').write_text('fixture')
            if prefix == host: paths.append(str(package/'+BUILD_INFO'))
    (work/'selection.json').write_text(json.dumps({'identity':{'inputs':paths}}))
    options=SimpleNamespace(sysroot=root/'sysroot',host_prefix=host,ports_source=root,host_buildlink_pkgsrc=root/'export')
    native=SimpleNamespace(host={'os':'Darwin'}); env={'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(work)}
    with patch.object(m,'protobuf_package_source') as metadata:
        observed=target/'include/libyuv.h';fixture.age(observed)
        values=m.common_media_libraries(options,native,env,host)
        fixture.race(sdkpaths,observed,lambda:m.common_media_libraries(options,native,env,host))
        assert metadata.call_count>=6
        for name in m.COMMON_MEDIA_LIBRARIES:
            for role,prefix in (('host',host),('target',target)):
                key='emberbsd_'+name+'_'+role
                assert values[key+'_headers']==str(prefix/'include')
                assert Path(values[key+'_library']).is_relative_to(prefix)
                assert any(x.endswith('/+BUILD_VERSION') for x in values[key+'_inputs'])
        duplicate=target/'pkgdb/duplicate'; duplicate.mkdir(); (duplicate/'+BUILD_INFO').write_text('PKGPATH=devel/crc32c\n')
        try: m.common_media_libraries(options,native,env,host)
        except ValueError as error: assert 'ambiguous common media package' in str(error)
        else: raise AssertionError('duplicate provider accepted')
        (duplicate/'+BUILD_INFO').unlink(); duplicate.rmdir()
        changed=target/'include/libyuv.h'; changed.write_text('foreign')
        try: m.common_media_libraries(options,native,env,host)
        except ValueError as error: assert 'differs from installed package' in str(error)
        else: raise AssertionError('modified selected header accepted')
        changed.write_text('fixture')
        lib=target/'lib/libcrc32c.so'; lib.unlink()
        try: m.common_media_libraries(options,native,env,host)
        except (ValueError, FileNotFoundError): pass
        else: raise AssertionError('missing selected library accepted')
print('PASS: common media role selection and missing provider refusal')
