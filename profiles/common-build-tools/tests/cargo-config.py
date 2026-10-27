#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""CLI/tool-routing fixtures; these do not qualify a Rust/C/C++ compiler."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

HELPER = Path(__file__).resolve().parents[1] / 'cargo-config.py'
spec = importlib.util.spec_from_file_location('cargo_config', HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HOST = 'aarch64-apple-darwin'
TARGET = 'x86_64-unknown-netbsd'


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='cargo-routing-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.vendor = self.root / 'vendor'
        self.vendor.mkdir()
        self.source = self.root / 'source'
        self.source.mkdir()
        self.rustc = self.executable('rustc', f'print("host: {HOST}")\n')
        self.cc = self.executable('clang', 'import json,sys\nprint(json.dumps(sys.argv[1:]))\n')
        self.cxx = self.executable('clang++', 'import json,sys\nprint(json.dumps(sys.argv[1:]))\n')
        self.ar = self.executable('llvm-ar', 'import json,sys\nprint(json.dumps(sys.argv[1:]))\n')
        self.cargo = self.executable('cargo', 'import json,os,sys\nprint(json.dumps({"argv":sys.argv[1:],"env":dict(os.environ),"cwd":os.getcwd()}))\nsys.exit(int(os.getenv("TEST_CARGO_EXIT", "0")))\n')
        self.config = self.root / '.cargo' / 'ember-config.toml'
        self.args = dict(config=self.config, vendor=self.vendor, output=self.root/'target',
                         rustc=self.rustc, shell=Path('/bin/sh'), tool_path=str(self.bin), mode='native',
                         target='', host_cc='clang', host_cxx='clang++', host_ar='llvm-ar',
                         target_cc='', target_cxx='', target_ar='')
        self.clean = patch.dict(os.environ, {}, clear=True)
        self.clean.start()
        self.addCleanup(self.clean.stop)

    def executable(self, name, source):
        path = self.bin / name
        path.write_text('#!' + sys.executable + '\n' + source)
        path.chmod(0o755)
        return path

    def configure(self, **changes):
        args = dict(self.args, **changes)
        module.configure(**args)
        return tomllib.loads(self.config.read_text())

    def cross(self, **changes):
        return self.configure(**dict(mode='cross', target=TARGET, target_cc='clang --target=x86_64--netbsd',
                                     target_cxx='clang++ --target=x86_64--netbsd', target_ar='llvm-ar', **changes))

    def invoke_wrapper(self, config, variable, *arguments):
        return json.loads(subprocess.check_output([config['env'][variable]['value'], *arguments], text=True))

    def test_native_explicit_target_and_offline_vendor(self):
        c = self.configure(rustflags='-C opt-level=2')
        self.assertEqual(c['build']['target'], HOST)
        self.assertEqual(c['build']['rustc'], str(self.rustc))
        self.assertEqual(c['source']['vendored-sources']['directory'], str(self.vendor))
        self.assertEqual(c['target'][HOST]['rustflags'], ['-C', 'opt-level=2'])
        self.assertEqual(self.invoke_wrapper(c, 'CC', '-c', 'input.c'), ['-c', 'input.c'])

    def test_cross_flags_and_commands_stay_separate(self):
        c = self.cross(host_cc='clang -arch arm64', host_cflags='-DHOST_ONLY', target_cflags='-DTARGET_ONLY',
                       host_cppflags='-I/host', target_cppflags='--sysroot=/target',
                       host_ldflags='-L/host', target_ldflags='--sysroot=/target -L/target', rustflags='-C panic=abort')
        self.assertEqual(self.invoke_wrapper(c, 'HOST_CC', '-c'), ['-arch', 'arm64', '-I/host', '-c'])
        self.assertEqual(self.invoke_wrapper(c, 'CC_'+TARGET, '-c'), ['--target=x86_64--netbsd', '--sysroot=/target', '-c'])
        self.assertNotIn('rustflags', c['target'][HOST])
        self.assertEqual(c['env']['CFLAGS']['value'], '-DHOST_ONLY')
        self.assertEqual(c['env']['CFLAGS_'+TARGET]['value'], '-DTARGET_ONLY')
        self.assertEqual(c['env']['CPPFLAGS_'+HOST]['value'], '')
        self.assertEqual(c['env']['CPPFLAGS_'+TARGET]['value'], '')
        for triple, expected in ((HOST, ['-arch','arm64','-L/host','output']), (TARGET, ['--target=x86_64--netbsd','--sysroot=/target','-L/target','output'])):
            actual=json.loads(subprocess.check_output([c['target'][triple]['linker'],'output'],text=True))
            self.assertEqual(actual,expected)

    def test_cc_crate_aliases_force_selected_inputs(self):
        c=self.cross()
        for triple in (HOST,TARGET):
            for role in ('CC','CXX','AR','CFLAGS','CXXFLAGS','CPPFLAGS'):
                exact=c['env'][role+'_'+triple]
                self.assertTrue(exact['force'])
                self.assertEqual(exact,c['env'][role+'_'+triple.replace('-','_')])
        self.assertEqual(c['env']['CC_SHELL_ESCAPED_FLAGS']['value'],'1')

    def test_command_quote_preservation_no_shell_evaluation(self):
        payload='$(touch forbidden) `echo unsafe` a b'
        c=self.configure(host_cc='clang '+shlex.quote(payload))
        self.assertEqual(self.invoke_wrapper(c,'HOST_CC','c d'),[payload,'c d'])
        self.assertFalse((self.root/'forbidden').exists())

    def test_explicit_gcc_alternative_no_family_fallback(self):
        self.executable('gcc', 'import json,sys\nprint(json.dumps(["selected-gcc"]+sys.argv[1:]))\n')
        c=self.configure(host_cc='gcc -m64')
        self.assertEqual(self.invoke_wrapper(c,'CC','file.c'),['selected-gcc','-m64','file.c'])

    def test_distinct_linker_launcher_preserves_argv_and_status(self):
        payload='$(touch forbidden) quote with spaces'
        launcher=self.executable('launcher', 'import json,subprocess,sys\nprint(json.dumps(sys.argv[1:]),flush=True)\nraise SystemExit(subprocess.run(sys.argv[3:]).returncode)\n')
        c=self.cross(host_linker_launcher=shlex.join([str(launcher),payload,'--']),
                     host_ldflags='-L/host',target_ldflags='-L/target')
        self.assertEqual(self.invoke_wrapper(c,'HOST_CC','-c'),['-c'])
        output=subprocess.check_output([c['target'][HOST]['linker'],'object with spaces'],text=True).splitlines()
        self.assertEqual(json.loads(output[0]),[payload,'--',str(self.cc),'-L/host','object with spaces'])
        self.assertEqual(json.loads(output[1]),['-L/host','object with spaces'])
        target=json.loads(subprocess.check_output([c['target'][TARGET]['linker'],'object'],text=True))
        self.assertEqual(target,['--target=x86_64--netbsd','-L/target','object'])
        self.assertFalse((self.root/'forbidden').exists())
        c=self.cross(host_linker_launcher=shlex.join([str(launcher),'host-prefix','--']),
                     target_linker_launcher=shlex.join([str(launcher),'target-prefix with spaces','--']),
                     host_ldflags='-L/host',target_ldflags='-L/target')
        for triple,marker,flags in ((HOST,'host-prefix',['-L/host']),
                                    (TARGET,'target-prefix with spaces',['--target=x86_64--netbsd','-L/target'])):
            output=subprocess.check_output([c['target'][triple]['linker'],'object'],text=True).splitlines()
            self.assertEqual(json.loads(output[0]),[marker,'--',str(self.cc),*flags,'object'])
            self.assertEqual(json.loads(output[1]),[*flags,'object'])
        failure=self.executable('failed-launcher','raise SystemExit(31)\n')
        c=self.configure(host_linker_launcher=str(failure))
        result=subprocess.run([c['target'][HOST]['linker'],'object'],capture_output=True)
        self.assertEqual(result.returncode,31)
        self.assertEqual(result.stdout,b'')

    def test_missing_linker_launcher_rejected_before_outputs(self):
        with self.assertRaisesRegex(ValueError,'selected command is missing'):
            self.configure(host_linker_launcher='/unselected/linker-launcher')
        self.assertFalse(self.config.parent.exists())

    def test_native_rejects_independent_target_launcher(self):
        with self.assertRaisesRegex(ValueError,'native mode'):
            self.configure(target_linker_launcher=str(self.cc))
        self.assertFalse(self.config.parent.exists())

    def test_missing_tool_rejected_before_outputs(self):
        with self.assertRaisesRegex(ValueError,'missing'):
            self.configure(host_cc='missing-clang')
        self.assertFalse(self.config.parent.exists())

    def test_native_rejects_foreign_target(self):
        with self.assertRaisesRegex(ValueError,'native package target differs'):
            self.configure(target=TARGET)

    def test_native_rejects_target_tool_override(self):
        with self.assertRaisesRegex(ValueError,'native mode'):
            self.configure(target_cc='clang')

    def test_cross_requires_different_explicit_target(self):
        for target in ('',HOST,'../../bad'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.configure(mode='cross',target=target)

    def test_ambiguous_rust_host_rejected(self):
        self.rustc.write_text('#!'+sys.executable+'\nprint("host: '+HOST+'\\nhost: '+TARGET+'")\n')
        with self.assertRaisesRegex(ValueError,'unique'):
            self.configure()

    def test_inherited_rust_wrapper_rejected(self):
        os.environ['RUSTC_WRAPPER']='unselected-wrapper'
        with self.assertRaisesRegex(ValueError,'undeclared'):
            self.configure()
        self.assertFalse(self.config.parent.exists())

    def test_relative_path_component_rejected(self):
        with self.assertRaisesRegex(ValueError,'absolute directories'):
            self.configure(tool_path=str(self.bin)+':.')

    def test_standard_build_script_override_keeps_target_only(self):
        override=self.root/'links.toml'
        override.write_text('[mimalloc_sys2]\nrustc-link-lib=["dylib=mimalloc"]\nrustc-link-search=["/target/lib"]\n[another.rustc-env]\nSELECTED="value"\n')
        c=self.cross(build_script_overrides=override)
        self.assertEqual(c['target'][TARGET]['mimalloc_sys2']['rustc-link-lib'],['dylib=mimalloc'])
        self.assertEqual(c['target'][TARGET]['another']['rustc-env'],{'SELECTED':'value'})
        self.assertNotIn('mimalloc_sys2',c['target'][HOST])

    def test_invalid_override_rejected_before_outputs(self):
        override=self.root/'bad.toml';override.write_text('outside="bad"\n')
        with self.assertRaisesRegex(ValueError,'tables keyed'):
            self.configure(build_script_overrides=override)
        self.assertFalse(self.config.parent.exists())

    def test_output_symlink_refused(self):
        self.config.parent.mkdir()
        victim=self.root/'victim';victim.write_text('retain')
        self.config.symlink_to(victim)
        with self.assertRaisesRegex(ValueError,'symlink'):
            self.configure()
        self.assertEqual(victim.read_text(),'retain')

    def run_cli(self, *arguments, **env):
        return subprocess.run([sys.executable,'-B','-I','-S',str(HELPER),*arguments],text=True,capture_output=True,env=dict(os.environ,**env))

    def test_run_cli_preserves_status_argv_and_explicit_rustc(self):
        self.configure(rustflags='-C opt-level=2')
        r=self.run_cli('run','--cargo',str(self.cargo),'--config',str(self.config),'--source',str(self.source),'--','build','--offline','--locked',TEST_CARGO_EXIT='19',RUSTFLAGS='-C unwanted',CARGO_ENCODED_RUSTFLAGS='unwanted',RUSTC='/unselected/rustc')
        self.assertEqual(r.returncode,19,r.stderr)
        data=json.loads(r.stdout)
        self.assertEqual(data['argv'],['--config',str(self.config),'build','--offline','--locked'])
        self.assertEqual(Path(data['cwd']),self.source.resolve())
        self.assertEqual(data['env']['RUSTC'],str(self.rustc))
        self.assertNotIn('RUSTFLAGS',data['env'])
        self.assertNotIn('CARGO_ENCODED_RUSTFLAGS',data['env'])
        self.assertEqual(data['env']['CARGO_NET_OFFLINE'],'true')

    def test_install_gets_explicit_configured_target(self):
        self.cross()
        r=self.run_cli('run','--cargo',str(self.cargo),'--config',str(self.config),'--source',str(self.source),'--','install','--path','.')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['argv'][-5:],['install','--target',TARGET,'--path','.'])

    def test_install_rejects_conflicting_target(self):
        self.cross()
        r=self.run_cli('run','--cargo',str(self.cargo),'--config',str(self.config),'--source',str(self.source),'--','install','--target='+HOST)
        self.assertNotEqual(r.returncode,0)
        self.assertIn('target is selected',r.stderr)

    def test_run_rejects_other_cargo_provider(self):
        self.configure()
        other=self.root/'other';other.mkdir()
        cargo=other/'cargo';cargo.symlink_to(self.cargo)
        r=self.run_cli('run','--cargo',str(cargo),'--config',str(self.config),'--source',str(self.source),'--','build')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('same selected native tool directory',r.stderr)

    def test_configure_cli(self):
        args=['configure']
        for key,value in self.args.items():
            args.extend(['--'+key.replace('_','-'),str(value)])
        r=self.run_cli(*args)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(tomllib.loads(self.config.read_text())['build']['target'],HOST)


if __name__=='__main__':
    unittest.main()
