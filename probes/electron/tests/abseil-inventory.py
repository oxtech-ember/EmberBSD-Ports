#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check selected per-toolchain Abseil package inventories."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

owner=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('controller',owner/'electron44/files/build-electron.py')
controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
with TemporaryDirectory() as temporary:
    root=Path(temporary).resolve(); host=root/'host'; sysroot=root/'sysroot'; work=root/'selection'; ports=root/'ports'; export=root/'export'
    host_pkg=root/'host-db/abseil'; target_pkg=sysroot/'usr/pkg/pkgdb/abseil'; host_pkg.mkdir(parents=True);target_pkg.mkdir(parents=True);work.mkdir()
    for p in (host_pkg,target_pkg):
        (p/'+BUILD_INFO').write_text('PKGPATH=devel/abseil\n');(p/'+BUILD_VERSION').write_text('selected source');(p/'+CONTENTS').write_text('selected contents')
    for prefix,name in ((host,'absl/strings/host.inc'),(sysroot/'usr/pkg','absl/strings/target.h')):
        p=prefix/'include'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('header')
    (work/'selection.json').write_text(json.dumps({'identity':{'inputs':[str(host_pkg/'+BUILD_INFO')]}}))
    class Native:
        def tool(self,name):return name
    class Process:
        def capture(self,args,env):
            if args[0]=='pkg-config':return SimpleNamespace(stdout=b'20260817.0\n')
            assert args[0]==str(root/'tools/sbin/pkg_info'),args[0]
            pkg=Path(args[args.index('-K')+1]);name='host.inc' if pkg==host_pkg.parent else 'target.h'
            return SimpleNamespace(stdout=('/prefix/include/absl/strings/'+name+'\n').encode())
    controller.protobuf_package_source=lambda *args,**kwargs:None
    options=SimpleNamespace(shared_abseil=True,host_prefix=root/'tools',sysroot=sysroot,ports_source=ports,host_buildlink_pkgsrc=export)
    env={'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(work)}
    result=controller.common_abseil(options,{'process':Process()},Native(),env,host)
    assert result['emberbsd_abseil_host_headers']==['absl/strings/host.inc']
    assert result['emberbsd_abseil_target_headers']==['absl/strings/target.h']
    assert str((host/'include/absl/strings/host.inc').resolve()) in result['emberbsd_abseil_host_inputs']
    (sysroot/'usr/pkg/include/absl/strings/target.h').unlink()
    try:controller.common_abseil(options,{'process':Process()},Native(),env,host)
    except (ValueError,FileNotFoundError):pass
    else:raise AssertionError('missing selected package header accepted')
print('PASS: independent selected host/target Abseil inventories')
