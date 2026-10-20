#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Audit serialized scripts without execution.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import os
from package_set_fixture import Fixture, check, metadata


def main():
    f=Fixture(sys.argv[1:],optional_auditor=True)
    payload=f.work/'payload';payload.mkdir();(payload/'data').write_text('Target package payload\n')
    build=metadata('aarch64')+b'BUILD_HOST=/private/tmp/build-host\nCC=/Volumes/build/compiler/bin/cc\n'
    script_ran=f.work/'script-was-executed'
    header=b'''#!/bin/sh
SELF="$0"
PKGNAME="$1"
STAGE="$2"
shift 2
AWK="/usr/bin/awk"
SED="/usr/bin/sed"
SH="/bin/sh"
SORT="/usr/bin/sort"
LINKFARM="/usr/sbin/linkfarm"
PKG_ADMIN="/usr/sbin/pkg_admin"
PKG_INFO="/usr/pkg/sbin/pkg_info"
MKDIR="/bin/mkdir -p"
ECHO_N="echo -n"
TRUE="true"
GTAR=""
PREFIX="/usr/pkg"
PKG_SYSCONFDIR="/etc/example"
'''+f'printf unexpected > {script_ran}\n'.encode()
    def case(name,scripts,expected=None,prefix='/usr/pkg',archive_only=None):
        directory=f.work/name
        archive=f.package(directory,'pkgset-scripts-1.0',payload,['data'],prefix=prefix,build=build,scripts=scripts)
        if '+REQUIRE' in scripts:
            tree=directory/'require-tree';f.unpack(archive,tree)
            contents=tree/'+CONTENTS';contents.chmod(0o644)
            contents.write_bytes(contents.read_bytes()+b'@ignore\n+REQUIRE\n')
            (tree/'+REQUIRE').write_bytes(scripts['+REQUIRE']);f.pack(tree,archive)
        database=directory/'pkgdb';f.database(archive,database)
        if archive_only:
            tree=directory/'archive-tree';f.unpack(archive,tree)
            (tree/'+INSTALL').chmod(0o644);(tree/'+INSTALL').write_bytes(archive_only);f.pack(tree,archive)
        index=directory/'archives.txt';index.write_text(str(archive)+'\n')
        destination,log=directory/'set',directory/'copies.log'
        f.result(name,f.audit(database,index,destination,['pkgset-scripts-1.0'],copy_log=log),expected,destination,log=directory/'audit.log')
        if expected:
            check(not log.exists(),'Rejected archive was copied')
        else:
            check(len(log.read_text().splitlines())==1,'Archive copy was not observed')
            check(f.sha(destination/'packages'/archive.name)==f.sha(archive),'Archive bytes differ')
        check(not script_ran.exists(),'A package script executed')
    case('valid-target-scripts-and-build-history',{name:header for name in ('+INSTALL','+DEINSTALL','+REQUIRE')})
    case('valid-nondefault-prefix',{'+INSTALL':header+b"PERL5='/opt/device/bin/perl -w'\n"},prefix='/opt/device')
    case('valid-local-and-x11-prefixes',{'+INSTALL':header+b'PERL5=/usr/local/bin/perl\nMKFONTDIR=/usr/X11R7/bin/mkfontdir\n'})
    for name in ('+INSTALL','+DEINSTALL','+REQUIRE'):
        case('host-shebang-'+name[1:].lower(),{name:header.replace(b'#!/bin/sh',b'#!/private/tmp/native/bin/mksh')},'Host path in package script')
    for helper,path in {'AWK':'/private/tmp/native/bin/nawk','SED':'/Volumes/build/native/bin/nbsed','PKG_ADMIN':'/Users/builder/native/sbin/pkg_admin','LINKFARM':'/opt/homebrew/sbin/linkfarm','SORT':'/var/folders/build/native/bin/sort'}.items():
        case('host-helper-'+helper.lower(),{'+INSTALL':header+f'{helper}="{path}"\n'.encode()},'Host path in package script')
    for name,entry,extra,expected in [
        ('unquoted-host-helper','+DEINSTALL',b'SED=/tmp/native/bin/sed\n','Host path in package script'),
        ('single-quoted-host-helper','+REQUIRE',b"AWK='/private/tmp/native/bin/awk -F :'\n",'Host path in package script'),
        ('dot-component-host-helper','+INSTALL',b'SH=/usr/bin/../../private/tmp/native/bin/sh\n','Host path in package script'),
        ('non-target-helper-prefix','+INSTALL',b'PKG_INFO=/build/native/sbin/pkg_info\n','Non-target executable in package script'),
        ('embedded-helper-shebang','+INSTALL',b"cat <<'HELPER'\n#!/private/tmp/native/bin/mksh\nHELPER\n",'Host path in package script'),
        ('embedded-helper-assignment','+INSTALL',b"cat <<'HELPER'\n#!/bin/sh\nAWK=/Volumes/build/native/bin/awk\nHELPER\n",'Host path in package script'),
        ('env-wrapped-host-helper','+INSTALL',b"SH='/usr/bin/env /private/tmp/native/bin/sh'\n",'Host path in package script'),
        ('target-prefix-boundary','+INSTALL',b'SH=/usr/pkg-host/bin/sh\n','Non-target executable in package script')]:
        case(name,{entry:header+extra},expected)
    case('archive-metadata-change-before-copy',{'+INSTALL':header},'Archive metadata mismatch +INSTALL',archive_only=header.replace(b'#!/bin/sh',b'#!/private/tmp/native/bin/mksh'))
    for variable,name,expected in [('PYTHON_PACKAGE_SCRIPT','actual-python315-serialized-script','Host path in package script'),('TARGET_PACKAGE_SCRIPT','actual-repaired-serialized-script',None)]:
        if variable in os.environ:
            path=Path(os.environ[variable]);(f.work/(name+'.sha256')).write_text(f.sha(path)+'\n')
            case(name,{'+INSTALL':path.read_bytes()},expected)
    print(f'PASS: {f.count} actual package-script audit cases; no scripts executed')


if __name__ == '__main__':
    main()
