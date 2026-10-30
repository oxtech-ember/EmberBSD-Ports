#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Check Rollup source adaptation and notice preservation; no package compilation."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest

RECIPE=Path(__file__).resolve().parents[1]

def load(name):
    spec=importlib.util.spec_from_file_location(name,RECIPE/'files'/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

prepare=load('prepare.py')
notices=load('install-notices.py')


class InputsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rollup-inputs-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.source=self.root/'source'
        (self.source/'npm/package/dist').mkdir(parents=True);(self.source/'rust/bindings_napi').mkdir(parents=True)
        for name in ('package.json','npm/package/package.json'):
            (self.source/name).write_text(json.dumps({'name':'rollup','version':'4.65.1'}))
        (self.source/'rust/bindings_napi/Cargo.toml').write_text('[target.test.dependencies]\nmimalloc-safe={version="0.1.67",features=["v3"]}\n')
        library=self.root/'buildlink/lib';library.mkdir(parents=True);(library/'libmimalloc.so.3').touch();(library/'libmimalloc.so').symlink_to('libmimalloc.so.3')
        self.args=dict(source=self.source,version='4.65.1',rust_target='aarch64-apple-darwin',napi_base='darwin-arm64',mimalloc_libdir=library,output=self.root/'links.toml')

    def test_shared_override(self):
        prepare.prepare(**self.args)
        data=tomllib.loads(self.args['output'].read_text())
        self.assertEqual(data,{'mimalloc_sys2':{'rustc-link-lib':['dylib=mimalloc'],'rustc-link-search':[str(self.args['mimalloc_libdir'])]}})

    def test_wrong_source_version(self):
        (self.source/'npm/package/package.json').write_text('{"name":"rollup","version":"4.60.4"}')
        with self.assertRaisesRegex(ValueError,'versions'):
            prepare.prepare(**self.args)
        self.assertFalse(self.args['output'].exists())

    def test_missing_v3(self):
        (self.source/'rust/bindings_napi/Cargo.toml').write_text('[target.test.dependencies]\nmimalloc-safe={version="0.1.67"}\n')
        with self.assertRaisesRegex(ValueError,'v3 ABI'):
            prepare.prepare(**self.args)

    def test_prebuilt_binding_rejected(self):
        (self.source/'npm/package/dist/rollup.darwin-arm64.node').touch()
        with self.assertRaisesRegex(ValueError,'prebuilt'):
            prepare.prepare(**self.args)

    def test_missing_shared_library_rejected(self):
        (self.args['mimalloc_libdir']/'libmimalloc.so').unlink()
        with self.assertRaisesRegex(ValueError,'shared mimalloc'):
            prepare.prepare(**self.args)

    def test_metadata_requires_explicit_safe_values(self):
        for field,value in (('rust_target',''),('napi_base',''),('napi_base','../../module')):
            with self.subTest(field=field),self.assertRaises(ValueError):
                prepare.prepare(**dict(self.args,**{field:value}))


class NoticesTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rollup-notices-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.vendor=self.root/'vendor';self.crate=self.vendor/'example-1.0.0';self.crate.mkdir(parents=True)
        (self.crate/'Cargo.toml').write_text('[package]\nname="example"\nversion="1.0.0"\nlicense="MIT"\nauthors=["Original Author"]\nreadme="README.md"\n')
        (self.crate/'.cargo-checksum.json').write_text(json.dumps({'package':'a'*64,'files':{}}))
        self.lock=self.root/'Cargo.lock';self.lock.write_text('[[package]]\nname="example"\nversion="1.0.0"\nsource="registry+https://github.com/rust-lang/crates.io-index"\nchecksum="'+'a'*64+'"\n')
        self.licenses=self.root/'licenses';self.licenses.mkdir()
        for name in notices.STANDARD_LICENSES:(self.licenses/name).write_text('Fixture standard license '+name+'\n')
        self.output=self.root/'out'

    def install(self):
        return notices.install(self.lock,self.vendor,self.output,self.licenses)

    def test_preserve_notice_bytes_and_original_metadata(self):
        original=b'Copyright original owner\nFixture license notice\n'
        (self.crate/'LICENSE').write_bytes(original)
        self.assertEqual(self.install(),(1,1))
        self.assertEqual((self.output/'crates/example-1.0.0/LICENSE').read_bytes(),original)
        entry=json.loads((self.output/'index.json').read_text())['crates'][0]
        self.assertEqual(entry['authors'],['Original Author'])
        self.assertEqual(entry['license'],'MIT')
        self.assertEqual(entry['original_notices'],['LICENSE'])

    def test_absent_notice_is_recorded_not_invented(self):
        (self.crate/'README.md').write_text('Original project description')
        self.assertEqual(self.install(),(1,0))
        entry=json.loads((self.output/'index.json').read_text())['crates'][0]
        self.assertEqual(entry['original_notices'],[])
        self.assertFalse((self.output/'crates/example-1.0.0/LICENSE').exists())
        self.assertEqual((self.output/'crates/example-1.0.0/README.md').read_text(),'Original project description')

    def test_lock_mismatch_fails_before_output(self):
        (self.crate/'.cargo-checksum.json').write_text(json.dumps({'package':'b'*64,'files':{}}))
        with self.assertRaisesRegex(ValueError,'differs'):
            self.install()
        self.assertFalse(self.output.exists())

    def test_notice_symlink_cannot_leave_crate(self):
        outside=self.root/'foreign';outside.write_text('must not package')
        (self.crate/'LICENSE').symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'leaves'):
            self.install()
        self.assertFalse(self.output.exists())

    def extra_fixture(self,commit='a'*40):
        with (self.crate/'Cargo.toml').open('a') as stream:
            stream.write('repository="https://github.com/example/notice"\n')
        (self.crate/'.cargo_vcs_info.json').write_text(json.dumps({'git':{'sha1':'a'*40}}))
        path=self.root/'example.LICENSE';data=b'Original upstream license and copyright\n';path.write_bytes(data)
        origin={'crate':'example-1.0.0','file':path.name,'repository':'example/notice','commit':commit,
                'source_path':'LICENSE','git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()}
        manifest=self.root/'origins.json';manifest.write_text(json.dumps([origin]));return manifest,data

    def test_restore_exact_notice_from_crate_vcs_pin(self):
        manifest,data=self.extra_fixture()
        notices.install(self.lock,self.vendor,self.output,self.licenses,manifest)
        self.assertEqual((self.output/'crates/example-1.0.0/UPSTREAM-example.LICENSE').read_bytes(),data)
        entry=json.loads((self.output/'index.json').read_text())['crates'][0]
        self.assertEqual(entry['restored_notices'][0]['commit'],'a'*40)

    def test_refuse_notice_from_another_commit(self):
        manifest,data=self.extra_fixture(commit='b'*40)
        with self.assertRaisesRegex(ValueError,'VCS identity'):
            notices.install(self.lock,self.vendor,self.output,self.licenses,manifest)
        self.assertFalse(self.output.exists())


    def test_refuse_corrupted_restored_notice(self):
        manifest,data=self.extra_fixture()
        (self.root/'example.LICENSE').write_bytes(data+b'changed')
        with self.assertRaisesRegex(ValueError,'pinned upstream blob'):
            notices.install(self.lock,self.vendor,self.output,self.licenses,manifest)
        self.assertFalse(self.output.exists())


def actual_sources(distdir,patch,license_root,work):
    if work.exists():
        raise ValueError('actual source test requires a new work directory')
    work.mkdir(parents=True)
    pins={}
    for line in (RECIPE/'distinfo').read_text().splitlines():
        match=re.fullmatch(r'(BLAKE2s|SHA512|Size|SHA1) \(([^)]*)\) = (.*)',line)
        if match:pins.setdefault(match[2],{})[match[1]]=match[3]
    for name,hashes in pins.items():
        path=RECIPE/'patches'/name if name.startswith('patch-') else distdir/name
        data=path.read_bytes()
        if name.startswith('patch-'):
            filtered=b''.join(line for line in data.splitlines(keepends=True) if b'$NetBSD' not in line)
            assert hashlib.sha1(filtered).hexdigest()==hashes['SHA1'],name
        else:
            assert hashlib.blake2s(data).hexdigest()==hashes['BLAKE2s'],name
            assert hashlib.sha512(data).hexdigest()==hashes['SHA512'],name
            assert str(len(data))+' bytes'==hashes['Size'],name
    with tarfile.open(distdir/'rollup-7879c65994dd591d287b177b8d0b88d7d76c2a49.tar.gz') as archive:
        archive.extractall(work,filter='data')
    source=work/'rollup-7879c65994dd591d287b177b8d0b88d7d76c2a49'
    (source/'npm').mkdir(exist_ok=True)
    with tarfile.open(distdir/'rollup-4.65.1.tgz') as archive:archive.extractall(source/'npm',filter='data')
    before=tomllib.loads((source/'rust/bindings_napi/Cargo.toml').read_text())
    for path in sorted((RECIPE/'patches').glob('patch-*')):
        result=subprocess.run([str(patch),'-f','-N','-F0','-p0','-i',str(path)],cwd=source,text=True,capture_output=True)
        assert result.returncode==0 and 'offset' not in result.stdout.lower() and 'fuzz' not in result.stdout.lower(),(path,result.stdout,result.stderr)
    after=tomllib.loads((source/'rust/bindings_napi/Cargo.toml').read_text())
    for target,table in before['target'].items():
        dependency=table['dependencies'].get('mimalloc-safe')
        if dependency:
            actual=after['target'][target]['dependencies']['mimalloc-safe']
            assert set(actual['features'])==set(dependency.get('features',[]))|{'v3'}
    library=work/'fixture-buildlink/lib';library.mkdir(parents=True);(library/'libmimalloc.so.3').touch();(library/'libmimalloc.so').symlink_to('libmimalloc.so.3')
    prepare.prepare(source,'4.65.1','aarch64-apple-darwin','darwin-arm64',library,work/'links.toml')
    vendor=work/'vendor';vendor.mkdir()
    lock=tomllib.loads((source/'rust/Cargo.lock').read_text())
    for package in lock['package']:
        if 'source' not in package:continue
        key=package['name']+'-'+package['version'];path=distdir/(key+'.crate')
        checksum=hashlib.sha256(path.read_bytes()).hexdigest();assert checksum==package['checksum'],key
        with tarfile.open(path) as archive:archive.extractall(vendor,filter='data')
        (vendor/key/'.cargo-checksum.json').write_text(json.dumps({'package':checksum,'files':{}}))
    counts=notices.install(source/'rust/Cargo.lock',vendor,work/'notices',license_root,RECIPE/'files/licenses/origins.json')
    assert counts==(195,279),counts
    restored=json.loads((work/'notices/index.json').read_text())['crates']
    assert sum(len(entry['restored_notices']) for entry in restored)==9
    print(json.dumps({'distfiles':len([name for name in pins if not name.startswith('patch-')]),'zero_fuzz_patches':2,'crate_checksums':195,'original_notices':279,'restored_notices':9,'scope':'actual source/checksum/patch/notice inputs; mimalloc library is a fixture; no build/runtime'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distdir',type=Path)
    parser.add_argument('--patch',type=Path)
    parser.add_argument('--license-root',type=Path)
    parser.add_argument('--work',type=Path)
    args=parser.parse_args()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case) for case in (InputsTest,NoticesTest))
    if not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful():return 1
    if args.distdir:
        if not all((args.patch,args.license_root,args.work)):parser.error('actual source test requires --patch --license-root --work')
        actual_sources(args.distdir,args.patch,args.license_root,args.work)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
