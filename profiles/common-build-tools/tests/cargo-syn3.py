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
    'tzif-provider': ('timezone_provider = {version="=0.2.6",features=["tzif"]}\ntzif = "=0.5.0"', '''
use timezone_provider::tzif::Tzif;
use tzif::data::time::Seconds;
#[test] fn transitions_and_invalid_input(){
 let raw=std::fs::read(std::env::var_os("EMBER_TZIF_FIXTURE").unwrap()).unwrap();
 let zone=Tzif::from_bytes(&raw).unwrap();
 for (time,expected) in [(1710064740,-28800),(1710064800,-25200),(1730624340,-25200),(1730624400,-28800)] {assert_eq!(zone.get(&Seconds(time)).unwrap().offset.0,expected,"timestamp {time}");}
 assert!(Tzif::from_bytes(b"not a TZif file").is_err());
}
'''),
    'zoneinfo64': ('zoneinfo64 = "=0.3.0"\nresb = "=0.2.0"\nserde = "1"', '''
use zoneinfo64::{ZoneInfo64,ZONEINFO64_RES_FOR_TESTING};
#[test] fn historical_and_dst_offsets(){
 let db=ZoneInfo64::try_from_u32s(ZONEINFO64_RES_FOR_TESTING).unwrap();
 let ny=db.get("America/New_York").unwrap();
 for (time,expected) in [(-2208988800,-18000),(1710053940,-18000),(1710054000,-14400),(1730613540,-14400),(1730613600,-18000),(2524608000,-18000),(2540246400,-14400)] {assert_eq!(ny.for_timestamp(time).offset.seconds(),expected,"timestamp {time}");}
 assert_eq!(db.get("UTC").unwrap().for_timestamp(0).offset.seconds(),0);
 assert_eq!(db.get("Asia/Kathmandu").unwrap().for_timestamp(1710054000).offset.seconds(),20700);
 assert!(db.get("Invalid/NoSuchZone").is_none());
}
#[test] fn signed_pairs_and_odd_length(){
 use resb::binary::helpers::{cast_u32_to_i32_pair_slice,I32Pair};
 let words=[u32::MAX,7,0,1];let pairs=cast_u32_to_i32_pair_slice::<serde::de::value::Error>(&words).unwrap();
 assert_eq!(pairs,[I32Pair(-1,7),I32Pair(0,1)]);assert!(pairs[0]<pairs[1]);
 assert!(cast_u32_to_i32_pair_slice::<serde::de::value::Error>(&words[..3]).is_err());
}
'''),
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
if 'tzif-provider' in a.case:
    fixture = vendor/'tzif-0.5.0/testdata/America/Los_Angeles'
    if not fixture.is_file(): raise ValueError('missing upstream TZif fixture')
    env['EMBER_TZIF_FIXTURE'] = str(fixture)
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
