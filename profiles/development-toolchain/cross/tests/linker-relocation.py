#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; real installed Binutils relocation and secondary-emulation link.
import sys
sys.dont_write_bytecode = True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'runtime/recipe/files'))
import sdk_source
args=sdk_source.arguments(sys.argv[1:])
for directory in (Path(__file__).resolve().parents[2],Path(__file__).resolve().parents[1]):sys.path.insert(0,str(directory))
from emberbsd_sdk import jsonio
from host import *
from pipeline import relocate_binutils


def main(args):
    require(len(args)==3,'Usage: linker-relocation.py BINUTILS_PREFIX aarch64|amd64 NEW_RECEIPT --sdk-source SOURCE')
    tools,target,output=args
    require(target in TARGETS,'Unsupported target')
    tools,work=build_path(tools),new_path(output)
    triplet=TARGETS[target][0]
    emulation,assembly,flags=('elf_i386','.text\n.globl _start\n_start: nop\n',['--32']) if target=='amd64' else ('aarch64elf','.text\n.globl _start\n_start: ret\n',[])
    work.mkdir();prefix=work/'relocated';(prefix/'bin').mkdir(parents=True)
    relocate_binutils(tools,prefix,triplet,work)
    logged([prefix/'bin'/(triplet+'-ld'),'-m',emulation,'--verbose'],work/'default-script.log')
    originals=sorted((tools/triplet/'lib/ldscripts').iterdir())
    require(originals,'No source scripts')
    hashes={str(path):sha(path) for path in originals}
    for path in originals:require(sha(prefix/triplet/'lib/ldscripts'/path.name)==hashes[str(path)],'Changed linker script')
    (work/'start.s').write_text(assembly)
    logged([prefix/'bin'/(triplet+'-as')]+flags+['-o',work/'start.o',work/'start.s'],work/'assemble.log')
    logged([prefix/'bin'/(triplet+'-ld'),'-m',emulation,'-e','_start','-o',work/'standalone',work/'start.o'],work/'link.log')
    result=capture([prefix/'bin'/(triplet+'-readelf'),'-h','-l','-d',work/'standalone'])
    (work/'elf.log').write_text(result)
    require(not re.search(r'\b(?:INTERP|NEEDED|RPATH|RUNPATH)\b',result),'Unexpected target dependencies')
    jsonio.write_json(work/'receipt.json',{'target':target,'scope':'Real bootstrap relocation and standalone link; no target execution','source_sha256':sha(Path(__file__).resolve().parents[1]/'pipeline.py'),'scripts':hashes,'output_sha256':sha(work/'standalone')})
    print('PASS: '+str(len(hashes))+' unchanged linker scripts and real '+emulation+' standalone link')

if __name__=='__main__':
    try:
        sdk_source.install_signal_handlers()
        main(args)
    except Exception as error:
        print(str(error), file=sys.stderr)
        status = getattr(error, 'returncode', None)
        sys.exit((128 - status if status < 0 else status) if status else 2)
