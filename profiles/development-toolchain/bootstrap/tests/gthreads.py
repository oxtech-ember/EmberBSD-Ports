#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; actual failed GCC16 gthreads probe and repaired configure.
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import re
from types import SimpleNamespace
import shlex
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'runtime/recipe/files'))
import sdk_source
args=sdk_source.arguments(sys.argv[1:])
for path in (Path(__file__).resolve().parents[2],Path(__file__).resolve().parents[1]):sys.path.insert(0,str(path))
from emberbsd_sdk import elf,jsonio,process
from emberbsd_sdk.errors import CommandError
from host import environment,require,sha,logged
from libstdcxx import LibstdcxxRebuild


def main(args):
    require(len(args)==9,'Usage: gthreads.py TARGET NEW_PKGSRC OLD_PKGSRC ARCHIVE PREFIX SYSROOT OLD_WORK NEW_WORK PREPARED_FAILED_WORK --sdk-source SOURCE')
    builder=LibstdcxxRebuild(['--check']+args[:8]);builder.preflight()
    reference=Path(args[8]).resolve(strict=True);work=builder.work
    source=reference/'src';build=work/'build'/builder.triplet/'libstdc++-v3';build.mkdir(parents=True)
    logfile=reference/'build'/builder.triplet/'libstdc++-v3/config.log'
    log=logfile.read_text();require('checking for gthreads library' in log,'Actual gthreads probe absent')
    tail=log[log.index('checking for gthreads library'):]
    line=next((line for line in tail.splitlines() if re.match(r'^configure:[0-9]+: ',line) and 'conftest.cpp' in line),None)
    require(line and 'configure: failed program was:\n' in tail,'Expected failed baseline probe')
    failed=tail.split('configure: failed program was:\n',1)[1]
    probe=''
    for item in failed.splitlines(keepends=True):
        if not item.startswith('|'):break
        probe+=re.sub(r'^\| ?','',item)
    require('#include "gthr.h"' in probe and '__GTHREADS_CXX0X' in probe,'Unexpected probe source')
    (work/'probe.cpp').write_text(probe)
    command=shlex.split(re.sub(r' >&5\s*$','',re.sub(r'^configure:[0-9]+: ','',line)))
    compiler=builder.compiler_commands()['CXX'].split(' ')
    require(command[:len(compiler)]==compiler and command.count('-c')==1 and command.count('conftest.cpp')==1,'Probe compiler or mode differs')
    command=[str(work/'probe.cpp') if word=='conftest.cpp' else word.replace(str(reference/'build')+'/',str(work/'build')+'/',1) for word in command]
    configured=jsonio.read_json(reference/'commands.json')
    require(all(configured['environment'][key]==value for key,value in builder.compiler_commands().items()) and not any(re.search('gthread',key,re.I) for key in configured['environment']),'Compiler environment differs or cached gthreads answer supplied')
    records=[]
    def run(name,env,argv,directory,want):
        log = work / (name + '.log')
        status = 0
        try: logged(argv, log, env, directory)
        except CommandError as failure: status = failure.returncode
        result = SimpleNamespace(returncode=status, stdout=b'', stderr=log.read_bytes())
        (work/(name+'.stdout')).write_bytes(result.stdout);(work/(name+'.stderr')).write_bytes(result.stderr)
        records.append({'name':name,'argv':[str(value) for value in argv],'environment':env,'cwd':str(directory),'status':result.returncode})
        jsonio.write_json(work/'commands.json',records,exclusive=not (work/'commands.json').exists())
        require((result.returncode==0)==want,'Unexpected probe status: '+name)
        return result.stderr.decode()
    error=run('before',{},command+['-o',work/'before.o'],work,False)
    require('gthr-default.h: No such file or directory' in error and not (work/'before.o').exists(),'Wrong missing-header baseline failure')
    builder.prepare_gthreads(source)
    run('fixed',{},command+['-o',work/'fixed.o'],work,True)
    require(elf.read_elf_header(work/'fixed.o',machine=builder.machine,required_type=1) is not None,'Wrong target ELF')
    run('configure',configured['environment'],[source/'libstdc++-v3/configure']+configured['configure'],build,True)
    require('#define _GLIBCXX_HAS_GTHREADS 1' in (build/'config.h').read_text().splitlines(),'Actual configure did not enable threads')
    inputs=[logfile,reference/'commands.json',source/'config/gthr.m4',source/'libgcc/Makefile.in',source/'libgcc/gthr-posix.h',source/'libstdc++-v3/configure',work/'probe.cpp',work/'build'/builder.triplet/'libgcc/gthr-default.h',build/'config.h']
    jsonio.write_json(work/'result.json',{'scope':'Actual failed upstream probe, repaired target object and fresh configure; no library build or target execution','machine':builder.machine,'has_gthreads':1,'inputs':{str(path):sha(path.resolve(strict=True)) for path in inputs}})
    print('PASS: real gthreads probe rejects missing header, then compiles and enables C++ threads')

if __name__=='__main__':
    try:
        sdk_source.install_signal_handlers()
        main(args)
    except Exception as error:
        print(str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
