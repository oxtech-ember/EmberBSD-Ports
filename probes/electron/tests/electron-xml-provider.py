#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Test role-specific XML provider validation using isolated package fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import argparse, sys
parser = argparse.ArgumentParser(); parser.add_argument('--sdk-source', type=Path, required=True)
args = parser.parse_args(); sys.path.insert(0, str(args.sdk_source.resolve() / 'src'))
from emberbsd_sdk import paths
import importlib.util as _iu
_sp = _iu.spec_from_file_location('stable_fixture', Path(__file__).with_name('stable-read-fixture.py'))
fixture = _iu.module_from_spec(_sp); _sp.loader.exec_module(fixture)
from types import SimpleNamespace
from unittest.mock import patch
owner=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,owner/file)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
controller=load('electron','build-electron.py'); xml=load('xml','xml-provider.py')
with tempfile.TemporaryDirectory(prefix='electron-xml-provider-') as tmp:
    root=Path(tmp).resolve(); host=root/'host'; target=root/'sysroot/usr/pkg'; view=root/'buildlink'
    dbs={'host':{},'target':{}}; inputs={}
    for role,prefix,suffix in (('host',host,'.dylib'),('target',target,'.so')):
        for path,package,lib,pc,header in (
                ('textproc/libxml2','libxml2-2.15.4nb5','libxml2','libxml-2.0','include/libxml2/libxml/tree.h'),
                ('textproc/libxslt','libxslt-1.1.45nb3','libxslt','libxslt','include/libxslt/xslt.h')):
            pkg=prefix/'pkgdb'/package; pkg.mkdir(parents=True); dbs[role][path]=[pkg]
            entries=['lib/pkgconfig/'+pc+'.pc','lib/'+lib+suffix,header]
            for entry in entries:
                file=prefix/entry; file.parent.mkdir(parents=True,exist_ok=True); file.write_text('owned')
            digest=hashlib.md5(b'owned',usedforsecurity=False).hexdigest()
            (pkg/'+CONTENTS').write_text('\n'.join([entries[0], '@comment MD5:'+digest, entries[1], '@comment MD5:'+digest, entries[2], '@comment MD5:'+digest]))
            for name in ('+BUILD_INFO','+BUILD_VERSION'): (pkg/name).write_text('owned')
            if role=='host':
                inputs[str(prefix/entries[0])]={}; file=view/entries[0]; file.parent.mkdir(parents=True,exist_ok=True); file.write_text('selected')
    metadata=root/'metadata'; metadata.mkdir()
    (metadata/'selection.json').write_text(json.dumps({'identity':{'inputs':inputs}}))
    opt=SimpleNamespace(shared_xml=True,host_prefix=host,sysroot=root/'sysroot',host_buildlink_pkgsrc=root/'pkgsrc',
        _common_native_packages=dbs['host'],_common_target_packages=dbs['target'],
        _compression_catalog={'recipes':{path:{} for path in xml.PROVIDERS.values() for path in [path[0]]}})
    native=SimpleNamespace(host={'os':'Darwin'},tool=lambda name:'/selected/'+name)
    sdk={'paths':paths,'process':SimpleNamespace(capture=lambda command,env:SimpleNamespace(stdout=b'1.0\n'))}
    env={'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(metadata)}
    with patch.object(controller,'validate_package_source') as validate:
        observed=target/'include/libxslt/xslt.h'; fixture.age(observed)
        selected=xml.select(controller,opt,sdk,native,env,view)
        assert validate.call_count==4 and len(selected)==8 and len(env['EMBERBSD_XML_SOURCE_SHA256'])==64
        fixture.race(paths, observed, lambda: xml.select(controller,opt,sdk,native,env,view))
        library=target/'lib/libxslt.so'; fixture.age(library)
        xml.select(controller,opt,sdk,native,env,view)
        fixture.race(paths, library, lambda: xml.select(controller,opt,sdk,native,env,view))
        assert selected['emberbsd_xml_host_library'].endswith('.dylib')
        assert selected['emberbsd_xml_target_library'].endswith('.so')
        assert any(p.endswith('/libxml/tree.h') for p in selected['emberbsd_xml_target_inputs'])
        old=opt._common_target_packages['textproc/libxml2']; opt._common_target_packages['textproc/libxml2']=[]
        try: xml.select(controller,opt,sdk,native,env,view)
        except ValueError as error: assert 'missing or mismatched' in str(error)
        else: raise AssertionError('missing target accepted')
        opt._common_target_packages['textproc/libxml2']=old
        (target/'lib/libxslt.so').write_text('modified')
        try: xml.select(controller,opt,sdk,native,env,view)
        except ValueError as error: assert 'library differs' in str(error)
        else: raise AssertionError('modified library accepted')
        (target/'lib/libxslt.so').write_text('owned')
        (target/'include/libxslt/xslt.h').write_text('modified')
        try: xml.select(controller,opt,sdk,native,env,view)
        except ValueError as error: assert 'differs' in str(error)
        else: raise AssertionError('modified header accepted')
    oldpkg=host/'pkgdb/libxml2-2.15.4nb4'; oldpkg.mkdir()
    opt._common_native_packages['textproc/libxml2']=[oldpkg]
    opt._common_target_packages['textproc/libxml2']=[oldpkg]
    try: xml.select(controller,opt,sdk,native,env,view)
    except ValueError as error: assert 'too old' in str(error)
    else: raise AssertionError('nb4 accepted')
print('PASS: XML role ownership, checksums, missing and obsolete package rejection')
