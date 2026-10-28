#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
"""Exercise migrated proc macros with real offline Cargo consumers."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib

CASES = {
    'tracing': ('tracing = "=0.1.44"', '''
#[tracing::instrument] pub fn add(x:i32)->i32 { x+1 }
#[tracing::instrument] pub unsafe fn value(x:i32)->i32 { x }
#[tracing::instrument] pub async fn asynchronous(x:i32)->i32 { x }
#[tracing::instrument] pub fn iterator()->impl Iterator<Item=i32> { 0..2 }
#[test] fn values(){assert_eq!(add(2),3);assert_eq!(unsafe{value(5)},5);assert_eq!(iterator().sum::<i32>(),1);}
'''),
    'is-macro': ('is-macro = "=0.3.8"', '''
use is_macro::Is;
#[derive(Debug,Is)] pub enum Choice<T> { A, B(T), Pair(i32,i64) }
#[test] fn values(){assert!(Choice::<()>::A.is_a());assert_eq!(Choice::B(7).b(),Some(7));assert_eq!(Choice::<()>::Pair(2,3).pair(),Some((2,3)));}
'''),
    'phf': ('phf = {version="=0.14.0",features=["macros"]}', '''
static MAP:phf::Map<&'static str,u32>=phf::phf_map!{"a"=>7,"b"=>9};
#[test] fn value(){assert_eq!(MAP.get("b"),Some(&9));}
'''),
    'zerocopy': ('zerocopy = {version="=0.8.63",features=["derive"]}', '''
use zerocopy::{FromBytes,IntoBytes,Immutable,KnownLayout};
#[repr(C)] #[derive(FromBytes,IntoBytes,Immutable,KnownLayout)] struct S{x:u32}
#[test] fn value(){assert_eq!(S{x:42}.as_bytes(),&42u32.to_ne_bytes());}
'''),
    'jiff': ('jiff = {version="=0.2.38",features=["static"]}', '''
static ZONE:jiff::tz::TimeZone=jiff::tz::get!("America/New_York");
#[test] fn zone(){assert_eq!(ZONE.iana_name(),Some("America/New_York"));}
'''),
}
p = argparse.ArgumentParser(description=__doc__)
for name in ('vendor', 'prefix', 'linker'):
    p.add_argument('--'+name, type=Path, required=True)
p.add_argument('--host-triple', required=True)
p.add_argument('--case', choices=CASES, action='append', required=True)
a = p.parse_args()
prefix = a.prefix.resolve(strict=True); vendor = a.vendor.resolve(strict=True)
cargo = (prefix/'bin/cargo').resolve(strict=True)
if not cargo.is_relative_to(prefix): raise ValueError('cargo must be inside host prefix')
rustc = (prefix/'bin/rustc').resolve(strict=True)
if not rustc.is_relative_to(prefix): raise ValueError('rustc must be inside host prefix')
linker = a.linker.resolve(strict=True)
if not linker.is_file(): raise ValueError('missing selected host linker')
env = os.environ.copy()
for key in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'DYLD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES', 'CARGO_TARGET_DIR', 'CARGO_BUILD_TARGET'):
    env.pop(key, None)
env['PATH'] = str(prefix/'bin') + os.pathsep + str(prefix/'sbin')
env['RUSTC'] = str(rustc)
env['CARGO_TARGET_'+a.host_triple.upper().replace('-', '_')+'_LINKER'] = str(linker)
with tempfile.TemporaryDirectory(prefix='cargo-syn3-test-') as tmp:
    root = Path(tmp); (root/'.cargo').mkdir(); (root/'src').mkdir()
    (root/'.cargo/config.toml').write_text('[source.crates-io]\nreplace-with="local"\n[source.local]\ndirectory='+json.dumps(str(vendor))+'\n[net]\noffline=true\n')
    env['CARGO_HOME'] = str(root/'home')
    for name in a.case:
        dep, source = CASES[name]
        (root/'Cargo.toml').write_text('[package]\nname="ember-cargo-syn3-test"\nversion="0.1.0"\nedition="2021"\n[dependencies]\n'+dep+'\n')
        (root/'src/lib.rs').write_text(source)
        subprocess.run([str(cargo), 'test', '--offline', '--target', a.host_triple, '--jobs', '4'], cwd=root, env=env, check=True)
        packages = tomllib.loads((root/'Cargo.lock').read_text())['package']
        assert {p['version'] for p in packages if p['name']=='syn'} == {'3.0.9'}, name
        print(name + ': PASS', flush=True)
