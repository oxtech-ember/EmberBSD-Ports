#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check explicit relocated sysroot selection without modifying CMake metadata."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

cross = Path(__file__).resolve().parents[1] / 'cross'
sys.path.insert(0, str(cross))
spec = importlib.util.spec_from_file_location('llvm_config_builder', cross/'build-llvm-config.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve(); old=root/'old'; new=root/'new'; other=root/'other'; target=root/'target'
    for path in (old, new/'usr/pkg', other, target): path.mkdir(parents=True)
    cache={'CMAKE_SYSROOT':str(old)}
    assert builder.target_sysroot(cache, str(old), str(other), str(target), False) == str(old)
    try: builder.target_sysroot(cache, str(new), str(new/'usr/pkg'), str(target), False)
    except ValueError as error: assert 'supplied sysroot differs' in str(error)
    else: raise AssertionError('strict mode accepted a different sysroot')
    assert builder.target_sysroot(cache, str(new), str(new/'usr/pkg'), str(target), True) == str(old)
    try: builder.target_sysroot(cache, str(new), str(other), str(target), True)
    except ValueError as error: assert 'relocated mode requires' in str(error)
    else: raise AssertionError('relocation accepted another installed prefix')
    escape = root/'escape'; (escape/'usr').mkdir(parents=True); (escape/'usr/pkg').symlink_to(other, target_is_directory=True)
    try: builder.target_sysroot(cache, str(escape), str(other), str(target), True)
    except ValueError as error: assert 'relocated mode requires' in str(error)
    else: raise AssertionError('escaping prefix accepted')
    try: builder.target_sysroot(cache, str(new), str(new/'usr/pkg'), str(new/'usr/pkg'), True)
    except ValueError as error: assert 'relocated mode requires' in str(error)
    else: raise AssertionError('target build prefix accepted')
    flags = {name:json.dumps(value) for name,value in {
        'LLVM_CFLAGS':'-DABC', 'LLVM_CXXFLAGS':'-std=c++17',
        'LLVM_SYSTEM_LIBS':'-lpthread', 'LLVM_LDFLAGS':'-L/usr/pkg/lib -Wl,-R/usr/lib'}.items()}
    _, mapped = builder.target_flags(flags, '/source', str(target), '/native', str(new), str(old))
    assert '-L'+str(new)+'/usr/pkg/lib' in mapped
    for name, value in (('LLVM_CXXFLAGS', '-I'+str(old)+'/usr/include'),
                        ('LLVM_LDFLAGS', '-Wl,-rpath,'+str(old)),
                        ('LLVM_LDFLAGS', '-L'+str(new)+'/usr/pkg/lib')):
        broken = dict(flags); broken[name] = json.dumps(value)
        try: builder.target_flags(broken, '/source', str(target), '/native', str(new), str(old))
        except ValueError: pass
        else: raise AssertionError('host path leak accepted: '+name)
    assert cache == {'CMAKE_SYSROOT':str(old)}
print('PASS: explicit relocation, strict default and installed prefix')
