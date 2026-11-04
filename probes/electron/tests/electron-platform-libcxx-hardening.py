#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check selected Darwin native binding and reject incompatible libc++ headers."""
import importlib.util,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(sys.argv[1]) / 'src'))
from emberbsd_sdk import process
p=Path(__file__).resolve().parents[3] / 'pkgsrc/devel/electron44/files/build-electron.py'
s=importlib.util.spec_from_file_location('build',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
bound=sys.argv[2]
o=SimpleNamespace(macos_sdk=sys.argv[3],macos_minimum=sys.argv[4])
env=process.sanitized_environment();env['PATH']=str(Path(bound).parent)
assert m.platform_libcxx_hardening(o,{'process':process},{'cxx':bound},env)
with tempfile.TemporaryDirectory() as d:
    class Bad:
        @staticmethod
        def capture(argv,**kw): return process.capture(argv[:1]+['-I',d]+argv[1:],**kw)
    for ns,mode in [('__bad','16'),('__1','2')]:
        Path(d,'__config').write_text(f'#define _LIBCPP_VERSION 1\n#define _LIBCPP_ABI_NAMESPACE {ns}\n#undef _LIBCPP_HARDENING_MODE\n#define _LIBCPP_HARDENING_MODE {mode}\n#define _LIBCPP_HARDENING_MODE_EXTENSIVE 16\n')
        try: m.platform_libcxx_hardening(o,{'process':Bad},{'cxx':bound},env)
        except Exception: pass
        else: raise AssertionError((ns,mode))
    Path(d,'__config').write_text('#define _LIBCPP_VERSION 1\n#define _LIBCPP_ABI_NAMESPACE __1\n')
    try: m.platform_libcxx_hardening(o,{'process':Bad},{'cxx':bound},env)
    except Exception: pass
    else: raise AssertionError('missing hardening support')
print('PASS: selected binding platform headers; wrong ABI, wrong mode and old headers rejected')
