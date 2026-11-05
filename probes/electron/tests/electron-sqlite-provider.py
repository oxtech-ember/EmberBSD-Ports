#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check SQLite selection binds source, generation policy without installed SQLite packages."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

files=Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files'
def load(name):
    spec=importlib.util.spec_from_file_location(name,files/(name+'.py'))
    obj=importlib.util.module_from_spec(spec); spec.loader.exec_module(obj); return obj
view, projection, provider=map(load,('protobuf-source-view','sqlite-source-view','sqlite-provider'))
# Take the upstream location from the explicit test argument on other hosts.
import sys
if len(sys.argv) != 2: sys.exit('usage: electron-sqlite-provider.py CHROMIUM_THIRD_PARTY_SQLITE')
source=Path(sys.argv[1]).resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='sqlite-provider-') as temp:
    root=Path(temp).resolve(); workspace=root/'workspace'; chrome=workspace/'src/third_party/sqlite'
    (chrome/'scripts').mkdir(parents=True)
    for f in ('sqlite_common_configuration_flags.gni','sqlite_chromium_configuration_flags.gni','sqlite_dev_configuration_flags.gni','scripts/extract_sqlite_api.py'):
        shutil.copy2(source/f,chrome/f)
    ports=root/'ports'; owner=ports/'scripts/source-inputs/sqlite'; owner.mkdir(parents=True)
    generator=Path(__file__).resolve().parents[3]/'scripts/source-inputs/sqlite/generate-chromium.py'
    shutil.copy2(generator,owner/'generate-chromium.py'); (owner/'source.py').write_text('fixture')
    src=root/'common'; (src/'test').mkdir(parents=True); archive=root/'archive.zip'; archive.write_text('archive')
    identity={'source':str(src),'tree':'a'*64}
    names={'common_gni_sha256':chrome/'sqlite_common_configuration_flags.gni',
           'chromium_gni_sha256':chrome/'sqlite_chromium_configuration_flags.gni',
           'dev_gni_sha256':chrome/'sqlite_dev_configuration_flags.gni',
           'extractor_sha256':chrome/'scripts/extract_sqlite_api.py',
           'generator_sha256':owner/'generate-chromium.py'}
    identity.update({k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in names.items()})
    flags=[]
    for key,var in (('common_gni_sha256','sqlite_common_configuration_flags'),('chromium_gni_sha256','sqlite_chromium_configuration_flags')):
        tree=ast.parse(names[key].read_text()); flags.extend(next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==var for t in n.targets)))
    identity['flags']=flags
    common_tree=ast.parse(names['common_gni_sha256'].read_text()); common=next(ast.literal_eval(n.value) for n in common_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sqlite_common_configuration_flags' for t in n.targets))
    dev_tree=ast.parse(names['dev_gni_sha256'].read_text()); dev=next(ast.literal_eval(n.value) for n in dev_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sqlite_dev_configuration_flags' for t in n.targets))
    identity['dev_flags']=common+dev
    def output(identity):
        stage=root/'stage'; (stage/'shell').mkdir(parents=True)
        for n in projection.FILES:
            (stage/n).parent.mkdir(parents=True,exist_ok=True); (stage/n).write_text(n)
        receipt={'format':'emberbsd-chromium-sqlite','version':1,'identity':identity,'files':{n:hashlib.sha256((stage/n).read_bytes()).hexdigest() for n in projection.FILES}}
        raw=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode(); (stage/'receipt.json').write_bytes(raw)
        dest=root/('amalgamation-'+hashlib.sha256(raw).hexdigest());stage.rename(dest);return dest
    (root/'patch').write_text('fixture')
    options=SimpleNamespace(sqlite_source=src,sqlite_archive=archive,sqlite_amalgamation=output(identity),sqlite_patch=root/'patch',ports_source=ports,sdk_source=root/'sdk',git=root/'git',workspace=workspace)
    controller=SimpleNamespace(require=view.require,validate_package_source=lambda *a,**k:None,git=str,source_environment=dict,view=view)
    sdk={'process':SimpleNamespace(capture=lambda *a,**k:SimpleNamespace(stdout=json.dumps({'package':'databases/sqlite3','tree_sha256':'a'*64}).encode()))}
    native=SimpleNamespace(tool=lambda _: '/selected/python'); env={}
    provider.select(controller,projection,options,sdk,native,env)
    try: provider.select(controller,projection,SimpleNamespace(sqlite_pkgsrc_export=root/'export'),sdk,native,{})
    except ValueError: pass
    else: raise AssertionError('partial SQLite selection accepted')
    assert 'EMBERBSD_SQLITE_SELECTION' in env
    bad = dict(identity, flags=flags[:-1])
    options.sqlite_amalgamation=output(bad)
    try: provider.select(controller,projection,options,sdk,native,{})
    except ValueError: pass
    else: raise AssertionError('changed Chromium policy accepted')
    options.sqlite_amalgamation=output(dict(identity, tree='b'*64))
    try: provider.select(controller,projection,options,sdk,native,{})
    except ValueError: pass
    else: raise AssertionError('unverified common source accepted')
    (options.sqlite_amalgamation/'sqlite3.c').write_text('tampered')
    try: provider.select(controller,projection,options,sdk,native,{})
    except ValueError: pass
    else: raise AssertionError('tampered amalgamation accepted')
print('PASS: SQLite source, Chromium policy and generated file integrity')
