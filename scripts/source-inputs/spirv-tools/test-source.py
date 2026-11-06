#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise the common archive owner and reject changed archive/patch inputs."""
import argparse, importlib.util, shutil, tempfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('sdk-source','archive','patch','git'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();here=Path(__file__).resolve().parent;ports=here.parents[2]
spec=importlib.util.spec_from_file_location('spirv_owner',here/'source.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
owner=m.Owner();owner.load_sdk(['--sdk-source',str(a.sdk_source.resolve(strict=True))])
# Fixture identities isolate uncommitted owner review; production uses Git identities.
owner.source_identity=lambda git:{'owner_sha256':owner.owner_digest(),'fixture':'review'}
owner.git_effective_identity=lambda git:{'fixture':'review'}
with tempfile.TemporaryDirectory(prefix='spirv-owner-test-') as td:
 root=Path(td);pkgroot=root/'pkgsrc';recipe=pkgroot/'parallel/spirv-tools';recipe.parent.mkdir(parents=True)
 shutil.copytree(ports/'pkgsrc/parallel/spirv-tools',recipe)
 archive=root/'SPIRV-Tools-2026.4.tar.gz';shutil.copyfile(a.archive,archive)
 out=root/'source';record=owner.prepare(str(archive),str(out),str(a.patch),str(a.git),True,exported=str(pkgroot))
 assert record['package']=='parallel/spirv-tools'
 assert (out/'source/opt/build_module.h').is_file() and (out/'utils/ggt.py').is_file()
 archive.write_bytes(b'wrong archive')
 try:owner.prepare(str(archive),str(root/'bad-archive'),str(a.patch),str(a.git),True,exported=str(pkgroot))
 except (ValueError,owner.SDKError):pass
 else:raise AssertionError('incorrect archive accepted')
 archive.unlink();shutil.copyfile(a.archive,archive)
 with (recipe/'patches/patch-source_val_scalar-matrix-extent').open('ab') as f:f.write(b'foreign')
 try:owner.prepare(str(archive),str(root/'bad-patch'),str(a.patch),str(a.git),True,exported=str(pkgroot))
 except (ValueError,owner.SDKError):pass
 else:raise AssertionError('incorrect patch accepted')
print('PASS: SPIRV-Tools owner verifies archive, complete patch set and prepared source')
