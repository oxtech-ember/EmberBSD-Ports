#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Build one common libiio configuration with explicitly selected tools."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
source, work = map(Path, sys.argv[1:3])
mode = sys.argv[3]
recipe = Path(__file__).resolve().parents[3]/'pkgsrc/devel/libiio'
if mode not in ('native','target') or not source.is_absolute() or not work.is_absolute() or work.exists():
    raise SystemExit('Use SOURCE NEW_WORK native|target with absolute paths')
for name in ('sources.tsv','distinfo'):
    owner = recipe/('files' if name=='sources.tsv' else '')/name
    if (source/'.ember'/name).read_bytes() != owner.read_bytes():
        raise SystemExit('Prepared source does not match the common recipe: '+name)
tools={name:Path(os.environ[name]) for name in ('CC','CMAKE','NINJA','PKG_CONFIG')}
for name,path in tools.items():
    if not path.is_absolute() or not os.access(path,os.X_OK): raise SystemExit('Select absolute '+name)
if not subprocess.check_output([str(tools['CC']),'-dumpfullversion'],text=True).startswith('16.'):
    raise SystemExit('GCC16 is required')
triplet=subprocess.check_output([str(tools['CC']),'-dumpmachine'],text=True).strip()
if mode=='target' and triplet not in ('x86_64--netbsd','aarch64--netbsd'):
    raise SystemExit('Select an EmberBSD target compiler')
work.mkdir(parents=True)
prefix = Path('/usr/pkg') if mode=='target' else work/'install'
cmd=[str(tools['CMAKE']),'-S',str(source),'-B',str(work/'build'),'-G','Ninja',
     '-C',str(recipe/'files/receiver.cmake'),'-DCMAKE_C_COMPILER='+str(tools['CC']),
     '-DCMAKE_MAKE_PROGRAM='+str(tools['NINJA']),'-DPKG_CONFIG_EXECUTABLE='+str(tools['PKG_CONFIG']),
     '-DCMAKE_INSTALL_PREFIX='+str(prefix),'-DCMAKE_INSTALL_LIBDIR=lib',
     '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON']
if mode=='target':
    config=Path(os.environ['CMAKE_TOOLCHAIN_FILE'])
    if not config.is_absolute() or not config.is_file(): raise SystemExit('Select target CMAKE_TOOLCHAIN_FILE')
    cmd+=['-DCMAKE_TOOLCHAIN_FILE='+str(config),'-DCMAKE_INSTALL_RPATH=/usr/pkg/lib;/usr/pkg/gcc16/lib']
else:
    cmd+=['-DCMAKE_INSTALL_RPATH='+str(prefix/'lib'),'-DCMAKE_PREFIX_PATH='+os.environ['LIBIIO_DEPENDENCY_PREFIX']]
    if 'SDKROOT' in os.environ: cmd+=['-DCMAKE_OSX_SYSROOT='+os.environ['SDKROOT']]
commands=[cmd,[str(tools['CMAKE']),'--build',str(work/'build'),'--parallel',os.environ.get('JOBS','2')],
          [str(tools['CMAKE']),'--install',str(work/'build')]]
record={'environment':{key:os.environ.get(key,'') for key in ('CFLAGS','LDFLAGS','SDKROOT','PKG_CONFIG_SYSROOT_DIR','PKG_CONFIG_LIBDIR','PKG_CONFIG_PATH','LIBIIO_DEPENDENCY_PREFIX')},'source_files':{str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()},'mode':mode,'triplet':triplet,'commands':commands,'tools':{k:{'path':str(v.resolve()),'sha256':hashlib.sha256(v.read_bytes()).hexdigest()} for k,v in tools.items()}}
if mode=='target': record['toolchain_file']={'path':str(config),'sha256':hashlib.sha256(config.read_bytes()).hexdigest()}
(work/'build-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
env=dict(os.environ)
if mode=='target': env['DESTDIR']=str(work/'stage')
for label,command in zip(('configure','build','install'),commands):
    with (work/(label+'.log')).open('wb') as log:
        subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
installed=work/'stage/usr/pkg' if mode=='target' else prefix
(installed/'include/iio-compat-0').mkdir()
shutil.copy2(source/'.ember/iio.h',installed/'include/iio-compat-0/iio.h')
doc=installed/'share/doc/libiio';doc.mkdir(parents=True)
for name in ('COPYING.txt','COPYING_MIT.txt','COPYING_GPL.txt'): shutil.copy2(source/name,doc/name)
shutil.copy2(work/'build/iio-config.h',doc/'iio-config.h')
cache=(work/'build/CMakeCache.txt').read_text()
for option in ('WITH_USB_BACKEND','LIBIIO_COMPAT','WITH_NETWORK_BACKEND'):
    if option+':BOOL=ON' not in cache: raise SystemExit('Missing required '+option)
if not (installed/'include/iio/iio.h').is_file(): raise SystemExit('Primary ABI1 header missing')
(work/'installed.json').write_text(json.dumps({'prefix':str(installed),'files':{str(p.relative_to(installed)):hashlib.sha256(p.read_bytes()).hexdigest() for p in installed.rglob('*') if p.is_file()}},indent=2)+'\n')
print('Staged '+mode+' common libiio: '+str(installed))
