#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Exercise Qt host input migration without touching a producer work tree."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from types import SimpleNamespace

owner = Path(__file__).resolve().parents[1] / 'cross/host-resume-inputs.py'
spec = importlib.util.spec_from_file_location('host_resume_inputs', owner)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def require_failure(action, expected):
    try:
        action()
    except ValueError as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError('invalid transition accepted: ' + expected)

with tempfile.TemporaryDirectory(prefix='qt-host-resume-') as temp:
    root = Path(temp).resolve(); toolkit = root/'probes/plasma-mobile/toolkit'; cross = toolkit/'cross'; cross.mkdir(parents=True)
    script=cross/'build-host-tools.sh'; script.write_text('producer')
    old=root/'view-old'; new=root/'view-new'; old.mkdir(); new.mkdir()
    prefix=root/'prefix'; (prefix/'lib').mkdir(parents=True); (prefix/'bin').mkdir()
    otool=prefix/'bin/llvm-otool'; otool.write_text('fixture')
    native=root/'native'; (native/'lib').mkdir(parents=True)
    work=root/'work'; (work/'qtbase/lib').mkdir(parents=True)
    image=work/'qtbase/lib/QtCore.dylib'; image.write_bytes(b'Qt image')
    for name, data in (('a.dylib',b'a'),('b.dylib',b'b')):
        (old/name).write_bytes(data); (new/name).write_bytes(data)
    provider=prefix/'lib/new.dylib'; provider.write_bytes(b'additional'); (new/'new.dylib').symlink_to(provider)
    load=str(native/'lib/new.dylib')
    def inspect(_otool, path):
        if path == new/'new.dylib' or path == image:
            return (load, []) if path == new/'new.dylib' else (None, [load])
        return (None, [])
    def block(view=old, producer=None, aggregate=None):
        rows=[f'{m.digest(p)}  {p}' for p in sorted(view.iterdir())]
        identity=hashlib.sha256((''.join(row+'\n' for row in rows)).encode()).hexdigest()
        return '\n'.join([f'{producer or m.PREDECESSOR}  {script}', *rows,
                         'profile=full',f'host_package_prefix={prefix}',f'host_runtime_view={view}',
                         'host_runtime_view_identity='+ (aggregate or identity), 'host_deployment_target=26.0'])+'\n'
    inputs=root/'inputs.txt';inputs.write_text(block())
    args=(inputs,str(script),str(new),'full',str(prefix),'26.0',str(work),str(native),str(otool))
    with patch.object(m,'inspect_loads',side_effect=inspect):
        assert m.check(*args)==(m.PREDECESSOR,1)
        (new/'a.dylib').write_bytes(b'changed');require_failure(lambda:m.check(*args),'previous runtime entry changed')
        (new/'a.dylib').write_bytes(b'a');(new/'b.dylib').unlink();require_failure(lambda:m.check(*args),'previous runtime entry changed')
        (new/'b.dylib').write_bytes(b'b');inputs.write_text(block(aggregate='0'*64));require_failure(lambda:m.check(*args),'previous runtime identity')
        inputs.write_text(block(producer=m.PREDECESSOR_CMAKE));assert m.check(*args)[0]==m.PREDECESSOR_CMAKE
        cwd=os.getcwd()
        try:
            os.chdir(root)
            inputs.write_text(block().replace(str(script), 'probes/plasma-mobile/toolkit/cross/build-host-tools.sh'))
            assert m.check(*args)[0]==m.PREDECESSOR
        finally:
            os.chdir(cwd)
        inputs.write_text(block(producer='f'*64));require_failure(lambda:m.check(*args),'unsupported previous producer')
        inputs.write_text(block());require_failure(lambda:m.check(inputs,str(script)+'-other',*args[2:]),'producer path changed')
        require_failure(lambda:m.check(inputs,str(script),str(new),'full','/other',*args[5:]),'configuration differs')
        (native/'lib/new.dylib').write_bytes(b'other');require_failure(lambda:m.check(*args),'shadows existing provider')
        (native/'lib/new.dylib').unlink()
        inputs.write_text(block() + block(view=new,producer=m.digest(script)))
        (new/'new.dylib').unlink();require_failure(lambda:m.check(*args),'previous runtime entry changed')
        (new/'new.dylib').symlink_to(provider);assert m.check(*args)[1]>1
    # Explicit incremental reconfiguration can select changed providers or new
    # dependencies before their future Qt module has been built.
    inputs.write_text(block(producer='f'*64))
    (new/'a.dylib').unlink()
    changed = prefix/'lib/a.dylib'; changed.write_bytes(b'new version')
    (new/'a.dylib').symlink_to(changed)
    def inspect_incremental(_otool, path):
        if path in (new/'a.dylib', new/'new.dylib'):
            return (str(native/'lib'/path.name), [])
        return (None, [])
    with patch.object(m, 'inspect_loads', side_effect=inspect_incremental):
        assert m.check(*args, '1')[0] == 'f'*64
        require_failure(lambda:m.check(*args), 'unsupported previous producer')
        (new/'b.dylib').unlink()
        require_failure(lambda:m.check(*args, '1'), 'previous runtime entry changed')
        (new/'b.dylib').write_bytes(b'b')
    def inspect_system(_otool, path):
        if path in (new/'a.dylib', new/'new.dylib'):
            return (str(native/'lib'/path.name), [])
        if path == image:
            return (None, ['/usr/lib/a.dylib'])
        return (None, [])
    with patch.object(m, 'inspect_loads', side_effect=inspect_system):
        require_failure(lambda:m.check(*args, '1'), 'install name differs')
    (new/'a.dylib').unlink(); (new/'a.dylib').write_bytes(b'a')
    inputs.write_text(block())
    with patch.object(m,'inspect_loads',side_effect=lambda _o,p: (load, []) if p in (new/'new.dylib', new/'a.dylib') else (None, [])):
        require_failure(lambda:m.check(*args),'lacks previous static Qt dependency')
    with patch.object(m,'inspect_loads',side_effect=lambda _o,p: (None, [load]) if p==new/'new.dylib' else (None, [])):
        require_failure(lambda:m.check(*args),'not the expected Mach-O provider')
    with patch.object(m,'inspect_loads',return_value=('/usr/lib/new.dylib', ['/usr/lib/new.dylib'])):
        require_failure(lambda:m.check(*args),'shadows system dependency')
    with patch.object(m,'inspect_loads',return_value=('@rpath/new.dylib', ['@rpath/new.dylib'])):
        require_failure(lambda:m.check(*args),'ambiguous previous dependency')
    with patch.object(m,'inspect_loads',side_effect=lambda _o,p: (load, []) if p==new/'new.dylib' else (None, [])):
        require_failure(lambda:m.check(*args),'lacks previous static Qt dependency')
print('PASS: additive migration, old identity, paths, changed/removed entries and provider-shadow refusals')

output = """/tmp/example:
Load command 0
          cmd LC_ID_DYLIB
      cmdsize 56
         name /tmp/with space/lib.dylib (offset 24)
Load command 1
          cmd LC_LOAD_DYLIB
      cmdsize 56
         name /tmp/another path/lib.dylib (offset 24)
"""
with patch.object(m.platform, 'machine', return_value='arm64'), patch.object(m.subprocess, 'run', return_value=SimpleNamespace(stdout=output, stderr='')):
    assert m.inspect_loads('/selected/llvm-otool', '/tmp/example') == ('/tmp/with space/lib.dylib', ['/tmp/another path/lib.dylib'])
print('PASS: distinct LC_ID, LC_LOAD and paths containing spaces')
