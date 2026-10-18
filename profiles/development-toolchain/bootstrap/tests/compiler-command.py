#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; real GCC16 under Autoconf compiler word expansion.
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import re
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'runtime/recipe/files'))
import sdk_source
args=sdk_source.arguments(sys.argv[1:])
for path in (Path(__file__).resolve().parents[2],Path(__file__).resolve().parents[1]):sys.path.insert(0,str(path))
from emberbsd_sdk import elf,jsonio,process
from emberbsd_sdk.errors import CommandError
from host import environment,require,logged
from libstdcxx import LibstdcxxRebuild


def main(args):
    require(len(args)==8,'Usage: compiler-command.py TARGET NEW_PKGSRC OLD_PKGSRC ARCHIVE PREFIX SYSROOT OLD_WORK NEW_WORK --sdk-source SOURCE')
    builder=LibstdcxxRebuild(['--check']+args);builder.preflight()
    work=builder.work;work.mkdir();records=[]
    def run(name,command,arguments,want):
        script='$COMPILER -x "$1" -c "$2" -o "$3"' if len(arguments)==3 else '$COMPILER "-print-file-name=$1"'
        argv=['sh','-eu','-c',script,'contract']+[str(value) for value in arguments]
        if len(arguments) == 3:
            log = work / (name + '.log')
            status = 0
            try: logged(argv, log, {'COMPILER': command})
            except CommandError as failure: status = failure.returncode
            result = SimpleNamespace(returncode=status, stdout=b'', stderr=log.read_bytes())
        else:
            try:result=process.capture(argv,env=environment({'COMPILER':command}))
            except CommandError as failure:result=failure
        (work/(name+'.stdout')).write_bytes(result.stdout);(work/(name+'.stderr')).write_bytes(result.stderr)
        records.append({'name':name,'command':command,'shell':script,'argv':argv,'status':result.returncode})
        jsonio.write_json(work/'result.json',records,exclusive=not (work/'result.json').exists())
        require((result.returncode==0)==want,'Unexpected command status: '+name)
        return result.stdout.decode(),result.stderr.decode()
    source=work/'input.c';source.write_text('#include <stddef.h>\nint value(void) { return (int)sizeof(ptrdiff_t); }\n')
    commands=builder.compiler_commands();commands['GXX']=commands['CXX'].replace('-gcc ','-g++ ',1)
    for name,fixed in commands.items():
        words=fixed.split(' ');require(len([word for word in words if word.startswith('-B')])==2,'Both support directories required')
        language='c' if name=='CC' else 'c++'
        baseline=' '.join(re.sub(r'[^A-Za-z0-9_\-.,:+/@]',lambda match:'\\'+match[0],word) for word in words)
        before=work/(name+'-before.o')
        _,error=run(name+'-before',baseline,[language,source,before],False)
        require('unrecognized command-line option' in error and '--sysroot\\=' in error and not before.exists(),'Wrong escaped-command baseline failure')
        output=work/(name+'.o');run(name+'-fixed',fixed,[language,source,output],True)
        require(elf.read_elf_header(output,machine=builder.machine,required_type=1) is not None,'Wrong target object')
        for file in ('crtbegin.o','libgcc_s.so'):
            out,_=run(name+'-'+file,fixed,[file],True)
            require(Path(out.strip()).resolve(strict=True).is_relative_to(builder.sysroot/'usr/pkg/gcc16'),'Compiler selected base support')
    print('PASS: real CC, raw CXX and g++ reject escaped sysroot, compile target ELF and retain support paths; no target execution')

if __name__=='__main__':
    try:
        sdk_source.install_signal_handlers()
        main(args)
    except Exception as error:
        print(str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
