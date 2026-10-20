#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real archives and header-only target fixtures.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contextlib
import io
import os
import shutil
from package_set_fixture import Fixture, check, elf, metadata


def main():
    f = Fixture(sys.argv[1:])
    w = f.work
    def fixture(name, arch, payloads, database_arch=None, archive_arch=None):
        directory = w / name
        payload, database, archives = directory/'payload', directory/'pkgdb', directory/'archives'
        (payload/'share').mkdir(parents=True)
        for slot, package in enumerate(('target-leaf-1.0','target-root-1.0')):
            (payload/'share'/package).write_bytes(payloads[slot])
            archive = f.package(archives,package,payload,['share/'+package],
                                arch=(archive_arch or {}).get(package,arch),
                                dependencies='target-leaf>=1.0' if slot else None)
            f.database(archive,database)
        for package, wrong in (database_arch or {}).items():
            (database/package/'+BUILD_INFO').write_bytes(metadata(wrong))
        index = directory/'archives.txt'
        index.write_text(''.join(str(p)+'\n' for p in sorted(archives.glob('*.tgz'))))
        return directory,database,index
    def audit(name, arch, payloads, target, expected=None, database_arch=None):
        directory,database,index=fixture(name,arch,payloads,database_arch)
        destination=directory/'set'
        f.result(name,f.audit(database,index,destination,['target-root-1.0'],target=target),expected,destination,log=directory/'audit.log')
        if expected is None:
            check((destination/'target.txt').read_bytes()==metadata(arch),'Target receipt differs')
            args=['--target',target] if target else []
            result=f.status(['sh',f.installer,*args,'--verify-only',destination])
            (directory/'verify.log').write_bytes(result.stdout+result.stderr)
            check(result.returncode==0,f'Host verification failed: {result.stdout!r}{result.stderr!r}')
        return destination
    aarch,amd=elf(183),elf(62)
    arm_set=audit('aarch64-default','aarch64',[aarch,aarch],None)
    audit('aarch64-explicit','aarch64',[aarch,aarch],'aarch64')
    amd_set=audit('amd64-explicit','x86_64',[amd,amd],'amd64')
    audit('amd64-data-package','x86_64',[b'data only\n',amd],'amd64')
    audit('amd64-wrong-root-elf','x86_64',[amd,aarch],'amd64','Wrong ELF machine')
    audit('amd64-wrong-dependency-elf','x86_64',[aarch,amd],'amd64','Wrong ELF machine')
    audit('aarch64-wrong-elf','aarch64',[amd,aarch],None,'Wrong ELF machine')
    audit('amd64-wrong-class','x86_64',[elf(62,1),amd],'amd64','Unsupported ELF class')
    audit('amd64-wrong-endian','x86_64',[elf(62,2,2),amd],'amd64','Unsupported ELF byte order')
    audit('amd64-truncated-elf','x86_64',[b'\x7fELF',amd],'amd64','Truncated ELF header')
    for role in ('root','leaf'):
        audit('amd64-wrong-'+('dependency' if role=='leaf' else role)+'-metadata','x86_64',[amd,amd],'amd64','Wrong target MACHINE_ARCH',{'target-'+role+'-1.0':'aarch64'})
    for name,options in [('unknown',['--target','riscv64']),('missing',['--target']),
                         ('empty',['--target','']),('repeated',['--target','amd64','--target','aarch64'])]:
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=f.module.main(['--sdk-source',f.sdk,*options])
        check(code!=0,f'Accepted {name} target')
        check(f.status(['sh',f.installer,*options]).returncode!=0,f'Installer accepted {name} target')
        f.count+=2
    for arguments in (['--target','amd64',arm_set],['--target','aarch64',amd_set],[amd_set]):
        result=f.status(['sh',f.installer,*arguments])
        check(result.returncode!=0 and b'Target receipt mismatch' in result.stdout+result.stderr,'Mismatched target receipt accepted')
        f.count+=1
    host_bin=w/'host-bin';host_bin.mkdir()
    (host_bin/'uname').write_text('#!/bin/sh\ncase "$1" in -s) echo NetBSD;; -p) echo "$FIXTURE_ARCH";; *) exit 1;; esac\n')
    (host_bin/'uname').chmod(0o755)
    # All install-mode cases must refuse before creating a log or invoking pkg_add.
    sentinel=w/'pkg-add-was-called'
    (host_bin/'pkg_add').write_text('#!/bin/sh\necho called > "'+str(sentinel)+'"\nexit 97\n')
    (host_bin/'pkg_add').chmod(0o755)
    cases=[(arm_set,None,'x86_64','Installation requires aarch64'),
           (arm_set,'amd64','x86_64','Target receipt mismatch'),
           (amd_set,'amd64','aarch64','Installation requires x86_64')]
    for slot,(bundle,target,arch,expected) in enumerate(cases):
        options=['--target',target] if target else []
        log=w/f'wrong-host-{slot}-install.log'
        env=dict(f.env,PATH=str(host_bin)+os.pathsep+os.environ['PATH'],FIXTURE_ARCH=arch,PKG_ADD=str(host_bin/'pkg_add'))
        result=f.status(['sh',f.installer,*options,'--install',bundle,log],env=env)
        check(result.returncode!=0 and expected.encode() in result.stdout+result.stderr,'Wrong-host install was not rejected')
        check(not log.exists() and not sentinel.exists(),'Install side effect before refusal')
        f.count+=1
    directory,_,_=fixture('installer-mixed-archive','x86_64',[amd,amd],archive_arch={'target-leaf-1.0':'aarch64'})
    mixed=directory/'set';mixed.mkdir();shutil.copytree(directory/'archives',mixed/'packages')
    # Only archives belong in a prepared package set.
    for path in (mixed/'packages').iterdir():
        if path.suffix!='.tgz':path.unlink()
    (mixed/'target.txt').write_bytes(metadata('x86_64'))
    (mixed/'install-order.txt').write_text('target-leaf-1.0.tgz\ntarget-root-1.0.tgz\n')
    (mixed/'roots.txt').write_text('target-root-1.0\n')
    (mixed/'packages.sha256').write_text(''.join(f'{f.sha(p)}  packages/{p.name}\n' for p in sorted((mixed/'packages').glob('*.tgz'))))
    result=f.status(['sh',f.installer,'--target','amd64',mixed])
    check(result.returncode!=0 and b'Package is not the prepared EmberBSD ABI' in result.stdout+result.stderr,'Foreign archive metadata accepted')
    f.count+=1
    (amd_set/'target.txt').write_bytes(metadata('x86_64')+b'MACHINE_ARCH=x86_64\n')
    result=f.status(['sh',f.installer,'--target','amd64',amd_set])
    check(result.returncode!=0 and b'Target receipt mismatch' in result.stdout+result.stderr,'Duplicate receipt fields accepted')
    f.count+=1
    print(f'PASS: {f.count} target selection, real pkgtools closure, ELF header and host verification checks; no target execution')


if __name__ == '__main__':
    main()
