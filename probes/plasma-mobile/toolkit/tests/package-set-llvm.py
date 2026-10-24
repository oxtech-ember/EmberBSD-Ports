#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real pkgtools archives; labelled text payloads.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_set_fixture import Fixture


def main():
    f=Fixture(sys.argv[1:],llvm=True)
    runtime='''lib/libLLVM.so.23.1 lib/libLLVM-23.so lib/libLLVM.so lib/libLTO.so.23.1
        lib/libLTO.so lib/libRemarks.so.23.1 lib/libRemarks.so include/llvm/Support/LICENSE.TXT'''.split()
    cases=[
        ('runtime-amd64','llvm-23.1.4nb1',runtime,'amd64',None,False),
        ('runtime-aarch64','llvm-23.1.4nb1',runtime,'aarch64',None,False),
        ('old-monolith','llvm-23.1.4',runtime+['bin/llvm-config'],'amd64','LLVM runtime',False),
        ('dependency-sdk','llvm-devel-23.1.4nb1',['bin/llvm-config'],'amd64','LLVM SDK',True),
        ('dependency-runtime','llvm-23.1.4nb1',runtime,'amd64',None,True),
        ('sdk','llvm-devel-23.1.4nb1',['bin/llvm-config'],'amd64','LLVM SDK',False),
        ('revised-monolith','llvm-23.1.4nb1',runtime+['bin/llvm-config'],'amd64','LLVM runtime',False),
        ('header-leak','llvm-23.1.4nb1',runtime+['include/llvm/IR/Module.h'],'amd64','LLVM runtime',False),
        ('missing-dso','llvm-23.1.4nb1',[p for p in runtime if p!='lib/libLTO.so.23.1'],'amd64','LLVM runtime',False),
        ('missing-license','llvm-23.1.4nb1',[p for p in runtime if p!='include/llvm/Support/LICENSE.TXT'],'amd64','LLVM runtime',False),
        ('legacy-provider','libLLVM-13.0.1nb4',['lib/libLLVM/libLLVM.so.13'],'amd64','LLVM legacy',False),
        ('unrelated','llvm-helper-1.0',['share/fixture'],'amd64',None,False)]
    for label,package,files,target,rejected,dependency in cases:
        directory=f.work/label;payload=directory/'payload';database=directory/'pkgdb'
        for name in files:
            path=payload/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(f'Text package policy fixture: {name}\n')
        arch='x86_64' if target=='amd64' else 'aarch64'
        archive=f.package(directory,package,payload,files,arch=arch)
        f.database(archive,database)
        archives=[archive]
        if dependency:
            root_payload=directory/'root-payload';(root_payload/'share').mkdir(parents=True)
            (root_payload/'share/consumer').write_text('runtime consumer fixture')
            root='desktop-fixture-1.0'
            root_archive=f.package(directory,root,root_payload,['share/consumer'],arch=arch,dependencies=package)
            f.database(root_archive,database);archives.append(root_archive);package=root
        index=directory/'archives';index.write_text(''.join(str(p)+'\n' for p in archives))
        destination=directory/'set'
        f.result(label,f.audit(database,index,destination,[package],target=target),rejected,destination,log=directory/'audit.log')
    print('SCOPE: twelve archive/policy fixtures; no LLVM build, target execution or shared pkgdb changes')


if __name__ == '__main__':
    main()
