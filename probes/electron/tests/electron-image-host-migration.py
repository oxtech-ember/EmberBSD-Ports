#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check saved host buildlink identity is replaced, never refreshed in place."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile

owner = Path(__file__).resolve().parents[3]/'pkgsrc/devel/electron44/files/build-electron.py'
spec = importlib.util.spec_from_file_location('electron', owner)
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
class CommandError(Exception):
    def __init__(self, returncode): self.returncode = returncode
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve(); previous=root/'host-buildlink-0'; previous.mkdir()
    saved={'invocation': {'pkgsrc_root':'/export', 'work':str(previous)},
           'identity':{'inputs':{'/prefix/lib/pkgconfig/libzstd.pc':'old'}}}
    (previous/'selection.json').write_text(json.dumps(saved))
    (root/'configuration.json').write_text(json.dumps({'environment':
        {'EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK':str(previous)}}))
    calls=[]
    def capture(command, env):
        calls.append(command)
        work=Path(command[command.index('--work')+1])
        if '--check' in command:
            record=json.loads((work/'selection.json').read_text())
            actual=record['invocation'].get('shared_image') == 'yes'
            if actual != ('--shared-image' in command): raise CommandError(3)
        else:
            work.mkdir()
            (work/'selection.json').write_text(json.dumps({'invocation':
                {'work':str(work),'shared_image':'yes'}, 'identity':{'inputs':{'image':'new'}}}))
        return SimpleNamespace(stdout=str(work/'view').encode())
    sdk={'process':SimpleNamespace(capture=capture,CommandError=CommandError)}
    native=SimpleNamespace(tool=lambda role:'/selected/'+role)
    o=SimpleNamespace(work=root, sdk_source=Path('/sdk'),host_prefix=Path('/prefix'),
        host_buildlink_pkgsrc=Path('/export'),host_buildlink_stage_root=None,
        host_buildlink_base_makeconf=Path('/makeconf'),host_buildlink_bmake_mk=Path('/mk'),
        lock_root=Path('/lock'),shared_image=True,phase='reconfigure')
    env={}; selected=e.host_buildlink(o,sdk,native,env,{'cxx':'/binding/cxx'})
    assert selected == str(root/'host-buildlink-1/view')
    assert env['EMBERBSD_ELECTRON_HOST_BUILDLINK_WORK'] == str(root/'host-buildlink-1')
    assert json.loads((previous/'selection.json').read_text()) == saved
    assert len(calls)==2 and '--check' in calls[0] and '--shared-image' in calls[0] and '--check' not in calls[1]
    o.phase='build'
    try: e.host_buildlink(o,sdk,native,{}, {'cxx':'/binding/cxx'})
    except ValueError as error: assert 'reconfigure' in str(error)
    else: raise AssertionError('build accepted a changed host selection')
print('PASS: saved host selection requires a fresh versioned image buildlink')
