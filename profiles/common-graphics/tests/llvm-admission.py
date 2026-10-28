#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Check semantic helper selection independently of historical receipts."""
import json
import importlib.util
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cross'))
import llvm_admission as a
REAL_CHECK_OUTPUT = subprocess.check_output

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        r = Path(self.tmp.name).resolve(); self.build = r / 'build'; self.root = r / 'target'; self.native = r / 'native'; self.prefix = self.root / 'usr/pkg'
        for p in (self.build / 'include/llvm/Config', self.build / 'tools/llvm-config', self.prefix / 'include/llvm/Config', self.prefix / 'lib', self.native / 'bin'): p.mkdir(parents=True)
        self.real = r / 'helper/bin/llvm-config.real'; self.real.parent.mkdir(parents=True); self.real.write_text('fixture'); self.real.chmod(0o755); self.native_triple = 'arm64-apple-darwin'
        (self.native / 'bin/llvm-config').touch()
        for name, data in (('llvm-config.h', '#define LLVM_VERSION_STRING "23.1.4"\n'), ('abi-breaking.h', 'abi\n')):
            (self.build / 'include/llvm/Config' / name).write_text(data); (self.prefix / 'include/llvm/Config' / name).write_text(data)
        (self.build / 'include/llvm/Config/config.h').write_text('#define PACKAGE_VERSION "23.1.4"\n')
        (self.build / 'tools/llvm-config/LibraryDependencies.inc').write_text('fixture')
        (self.build / 'tools/llvm-config/BuildVariables.inc').write_text('#define LLVM_OBJ_ROOT ' + json.dumps(str(self.build)) + '\n#define LLVM_CXXFLAGS "-std=c++17 -DABI=1"\n' + ''.join('#define ' + x + ' 1\n' for x in ('LLVM_ENABLE_DYLIB','LLVM_LINK_DYLIB','LLVM_HAS_RTTI')))
        self.cache = self.build / 'CMakeCache.txt'; self.cache.write_text(''.join(k+':STRING='+v+'\n' for k,v in {'CMAKE_SYSROOT':str(self.root),'CMAKE_INSTALL_PREFIX':'/usr/pkg','LLVM_ENABLE_ASSERTIONS':'OFF','LLVM_BUILD_LLVM_DYLIB':'ON','LLVM_LINK_LLVM_DYLIB':'ON','LLVM_ENABLE_RTTI':'ON'}.items()))
        self.lib = self.prefix / 'lib/libLLVM-23.so'; self.lib.write_bytes(b'fixture')
        self.answers = {'--version':'23.1.4','--prefix':str(self.prefix),'--includedir':str(self.prefix/'include'),'--libdir':str(self.prefix/'lib'),'--has-rtti':'YES','--assertion-mode':'OFF','--shared-mode':'shared','--host-target':'x86_64-unknown-netbsd','--cxxflags':'-I'+str(self.prefix/'include')+' -std=c++17 -DABI=1','--ldflags':'-L'+str(self.prefix/'lib'),'--libfiles':str(self.lib),'--libs':'-lLLVM'}
        def output(cmd, **kw):
            if cmd[0] == str(self.native/'bin/llvm-config'): return self.native_triple+'\n'
            if '--list' in cmd: return 'fixture loader list\n'
            return next(self.answers[x]+'\n' for x in cmd[1:] if x in self.answers)
        for obj, name, value in ((a.native,'platform','darwin'),(a.native,'darwin',''),(a.target,'validate_elf',True),(a.target,'validate',{'processor':'x86_64','backend':'x86','machine':62}),(a.subprocess,'check_output',None)):
            p=mock.patch.object(obj,name,side_effect=output) if name=='check_output' else mock.patch.object(obj,name,return_value=value); p.start(); self.addCleanup(p.stop)
    def check(self): return a.validate(str(self.real),str(self.build),str(self.root),str(self.native))
    def test_valid_and_unrelated_sdk_change(self):
        self.assertEqual(self.check(),[str(self.real)]); (self.root.parent/'unrelated-sdk.py').write_text('changed'); self.assertEqual(self.check(),[str(self.real)])
    def test_bad_metadata(self):
        for key,value in (('--version','24.0'),('--host-target','aarch64-unknown-netbsd'),('--cxxflags','-std=c++17 -DABI=0'),('--prefix','/other'),('--has-rtti','NO')):
            with self.subTest(key=key):
                old=self.answers[key]; self.answers[key]=value
                with self.assertRaises(ValueError): self.check()
                self.answers[key]=old
    def test_bad_header_or_nonexecutable(self):
        p=self.prefix/'include/llvm/Config/abi-breaking.h'; p.write_text('wrong')
        with self.assertRaises(ValueError): self.check()
        p.write_text('abi\n'); self.real.chmod(0o644)
        with self.assertRaises(ValueError): self.check()
    def test_retained_linux_loader_constructed_and_confined(self):
        self.native_triple = 'x86_64-unknown-linux-gnu'
        libs = self.real.parent.parent / 'native/lib'; libs.mkdir(parents=True)
        loader = libs / 'ld-linux-x86-64.so.2'; loader.touch()
        runtime = libs / 'libstdc++.so.6'; runtime.touch()
        with mock.patch.object(a.native, 'platform', return_value='linux-gnu'), mock.patch.object(a.native, 'machine', return_value=62), mock.patch.object(a.native, 'elf'), mock.patch.object(a.native, 'loaded', return_value={'runtime': str(runtime)}):
            command = self.check()
            self.assertEqual(command, [str(loader), '--inhibit-cache', '--library-path', str(libs), str(self.real)])
            with mock.patch.object(a.native, 'loaded', return_value={'runtime': str(self.real)}):
                with self.assertRaises(ValueError): self.check()

    def test_wrong_native_or_target_architecture(self):
        with mock.patch.object(a.native, 'darwin', side_effect=ValueError('wrong native architecture')):
            with self.assertRaises(ValueError): self.check()
        with mock.patch.object(a.target, 'validate_elf', side_effect=ValueError('wrong target architecture')):
            with self.assertRaises(ValueError): self.check()

    def test_adapter_launcher_clears_loader_environment(self):
        module_path = Path(__file__).resolve().parents[1] / 'cross/adapt-llvm-config.py'
        spec = importlib.util.spec_from_file_location('adapter', module_path)
        adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
        self.real.write_text('#!/bin/sh\nprintf "%s:%s" "${LD_TEST-unset}" "${DYLD_TEST-unset}"\n')
        output = self.root.parent / 'adapter'
        with mock.patch.object(adapter.llvm_admission, 'validate', return_value=[str(self.real)]):
            adapter.main(['--real', str(self.real), '--target-build', str(self.build), '--sysroot', str(self.root), '--native-build', str(self.native), '--output', str(output)])
        env = dict(os.environ, LD_TEST='bad', DYLD_TEST='bad')
        self.assertEqual(REAL_CHECK_OUTPUT([str(output)], env=env, text=True), 'unset:unset')

    def test_library_escape(self):
        self.lib.unlink(); self.lib.symlink_to(self.real)
        with self.assertRaises(ValueError): self.check()
if __name__ == '__main__': unittest.main()
