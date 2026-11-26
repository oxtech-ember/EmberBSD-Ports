#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
"""Exercise pkgsrc +BUILD_INFO generation with private build inputs."""
import argparse
from pathlib import Path
import os
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--pkgsrc', type=Path, required=True)
p.add_argument('--bmake', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
a.work.mkdir(parents=True, exist_ok=False)

pkgsrc = a.pkgsrc.resolve(strict=True)
bmake = a.bmake.resolve(strict=True)
work = a.work.resolve()
tool = work / 'uname'
tool.write_text('#!/bin/sh\ncase "$*" in\n  -sm) echo "Darwin arm64" ;;\n  -a) echo "Darwin private-builder.local 27.2.0 Darwin Kernel Version private" ;;\n  *) exit 2 ;;\nesac\n')
tool.chmod(0o755)
(work / 'plist').write_text('')
makefile = work / 'Makefile'
target = work / '.pkgdb/+BUILD_INFO'
makefile.write_text(f'''PKGSRCDIR= {pkgsrc}
WRKDIR= {work}
EMBERBSD_CROSS_SYSROOT= /private/test-sysroot
DESTDIR= {work}/destdir
PREFIX= /usr/pkg
UNAME= {tool}
ECHO= /bin/echo
DATE= /bin/date
SH= /bin/sh
TEST= /bin/test
MKDIR= /bin/mkdir
TRUE= /usr/bin/true
_PLIST_NOKEYWORDS= {work}/plist
_BUILD_DEFS= PKGNAME CONFIGURE_ENV CONFIGURE_ARGS CMAKE_CONFIGURE_ARGS OPSYS OS_VERSION MACHINE_ARCH MACHINE_GNU_ARCH ABI OBJECT_FMT LICENSE DEPENDS PKG_OPTIONS BUILTIN_PKGS PYTHON_VERSION_DEFAULT CFLAGS CPPFLAGS LDFLAGS CXXFLAGS SHLIB_LDFLAGS
_BUILD_DEFS+= EMBERBSD_SDK_SOURCE EMBERBSD_UNDICI_HOST_PREFIX EMBERBSD_RUST_COMPILER_PREFIX EMBERBSD_RUST_TARGET_SYSROOT EMBERBSD_RUST_CROSS_TOOLS OSX_SDK_PATH EMBERBSD_UNDICI_RUNTIME_PREFIX MACOSX_DEPLOYMENT_TARGET
EMBERBSD_SDK_SOURCE= {work}/sdk
EMBERBSD_UNDICI_HOST_PREFIX= {work}/host
EMBERBSD_RUST_COMPILER_PREFIX= {work}/compiler
EMBERBSD_RUST_TARGET_SYSROOT= {work}/sysroot
EMBERBSD_RUST_CROSS_TOOLS= {work}/cross
OSX_SDK_PATH= {work}/platform-sdk
EMBERBSD_UNDICI_RUNTIME_PREFIX= /usr/pkg
MACOSX_DEPLOYMENT_TARGET= 14.0
PKGNAME= graphene-1.10.8nb5
CONFIGURE_ENV= CC=/private/path/bin/clang SDKROOT=/private/path/sdk
CONFIGURE_ARGS= --cc=/private/path/bin/clang --prefix=/usr/pkg
CMAKE_CONFIGURE_ARGS= -DCMAKE_TOOLCHAIN_FILE=/private/path/toolchain.cmake
OPSYS= NetBSD
OS_VERSION= 11.0
MACHINE_ARCH= aarch64
MACHINE_GNU_ARCH= aarch64
ABI= NetBSD-11.0-aarch64
OBJECT_FMT= ELF
LICENSE= mit
DEPENDS= glib2>=2.0
PKG_OPTIONS= graphviz
BUILTIN_PKGS= zlib-1.4
PYTHON_VERSION_DEFAULT= 315
CFLAGS= -O2 -I/usr/pkg/include
CPPFLAGS= -DGRAPHENE=1
LDFLAGS= -L/usr/pkg/lib
CXXFLAGS= -I{work}/generated
SHLIB_LDFLAGS= -Wl,-rpath-link,${{EMBERBSD_CROSS_SYSROOT}}/usr/pkg/qt6/lib
INIT_SYSTEM= none
USE_LANGUAGES= c
CC_VERSION= clang 23.1.6
PKGTOOLS_VERSION_REQD= 20250422
HOMEPAGE= https://example.invalid/graphene
CATEGORIES= graphics
MAINTAINER= ports@example.invalid
CHECK_SHLIBS_SUPPORTED= no
.include "${{PKGSRCDIR}}/mk/pkgformat/pkg/metadata.mk"
''')
env = dict(os.environ, LC_ALL='C')
result = subprocess.run([str(bmake), '-r', '-f', str(makefile), str(target)],
                        cwd=work, env=env, capture_output=True, text=True)
if result.returncode:
    raise SystemExit(result.stderr or result.stdout)
metadata = target.read_text()
for private_field in ('CONFIGURE_ENV=', 'CONFIGURE_ARGS=', 'CMAKE_CONFIGURE_ARGS=',
                      'CXXFLAGS=', 'SHLIB_LDFLAGS=', 'EMBERBSD_SDK_SOURCE=', 'OSX_SDK_PATH=',
                      'EMBERBSD_UNDICI_HOST_PREFIX=', 'EMBERBSD_RUST_COMPILER_PREFIX=',
                      'EMBERBSD_RUST_TARGET_SYSROOT=', 'EMBERBSD_RUST_CROSS_TOOLS='):
    assert private_field not in metadata, (private_field, metadata)
assert 'private-builder.local' not in metadata, metadata
assert 'BUILD_HOST=Darwin arm64' in metadata, metadata
for field in ('PKGNAME=graphene-1.10.8nb5', 'OPSYS=NetBSD',
              'OS_VERSION=11.0', 'MACHINE_ARCH=aarch64',
              'MACHINE_GNU_ARCH=aarch64', 'ABI=NetBSD-11.0-aarch64',
              'OBJECT_FMT=ELF', 'LICENSE=mit', 'DEPENDS=glib2>=2.0',
              'PKG_OPTIONS=graphviz', 'BUILTIN_PKGS=zlib-1.4',
              'PYTHON_VERSION_DEFAULT=315', 'CFLAGS=-O2 -I/usr/pkg/include',
              'CPPFLAGS=-DGRAPHENE=1', 'LDFLAGS=-L/usr/pkg/lib',
              'EMBERBSD_UNDICI_RUNTIME_PREFIX=/usr/pkg', 'MACOSX_DEPLOYMENT_TARGET=14.0'):
    assert field in metadata, (field, metadata)
print('generated +BUILD_INFO omits private configure data and retains package identity')
