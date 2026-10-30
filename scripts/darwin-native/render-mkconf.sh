#!/bin/bash
# Render a Darwin bootstrap mk.conf whose every tool comes from the native SDK prefix
# (SDK LLVM, g* coreutils, nbsed, nawk, bsdinstall, Ports curl). No host /usr or /bin tools.
B=${EMBERBSD_ROOT:?set EMBERBSD_ROOT}; P=${EMBERBSD_SDK_PREFIX:-$B/sdk-native/llvm}; W=${EMBERBSD_WORK:-$B/work/bootstrap-work}
S=${DARWIN_SDKROOT:?set DARWIN_SDKROOT}
PY=$P/bin/python3.15; [ -x $PY ] || { echo "missing SDK python $PY" >&2; exit 1; }
a=(--tool cc=$P/bin/clang --tool cxx=$P/bin/clang++ --tool cpp=$P/bin/clang-cpp --tool as=$P/bin/clang
 --tool ld=$P/bin/ld64.lld --tool dsymutil=$P/bin/dsymutil --tool ar=$P/bin/llvm-ar --tool ranlib=$P/bin/llvm-ranlib
 --tool nm=$P/bin/llvm-nm --tool strip=$P/bin/llvm-strip --tool lipo=$P/bin/llvm-lipo --tool otool=$P/bin/llvm-otool
 --tool make=$P/bin/bmake --tool gmake=$P/bin/gmake --tool sh=$P/bin/mksh --tool digest=$P/bin/digest --tool fetch=$P/bin/curl --source-tool bash --tool patch=$P/bin/nbpatch --source-tool gtar --source-tool nroff --source-tool perl --source-tool pkg-config --source-tool xzcat --source-tool install-info --source-tool autoconf --source-tool bison --source-tool cmake --source-tool gm4 --source-tool itstool --source-tool makeinfo --source-tool msgfmt --source-tool openssl --source-tool xz --source-tool flex --source-tool gs --source-tool automake --source-tool bison-yacc --source-tool yacc --source-tool cpack --source-tool msgmerge --source-tool xgettext --source-tool autoreconf --source-tool autoheader --source-tool aclocal --source-tool gettext
 --tool pkg_info=$P/sbin/pkg_info --tool pkg_admin=$P/sbin/pkg_admin --tool pkg_add=$P/sbin/pkg_add --tool pkg_create=$P/sbin/pkg_create)
for t in awk basename cat cut date dirname env expr grep head id pwd sed sort tail tr uname uniq wc chgrp chmod chown cp ln mkdir mv rm rmdir touch test echo true false find xargs ls printf sleep tee diff cmp install file tar bzip2 xz hostname mktemp nice tsort comm csplit egrep fgrep join od paste split strings tic unzip bsdtar pax bzcat ident ksh bash patch m4 lex flex yacc bison perl readlink realpath shlock printenv logname whoami du df stat gunzip; do
  case $t in xz|gunzip|patch|m4|lex|flex|yacc|bison|perl|bash|ksh|ident) continue;; esac
  # SDK prefix only: no host utilities.
  case $t in sed) c=nbsed;; awk) c=nawk;; hostname) c=ghostname;; pax) c=nbpax;; strings) c=llvm-strings;; tar) c=gtar;; install) c=bsdinstall;; unzip|bsdtar|bzip2|bzcat|xz|file|shlock|tic) c=$t;; *) c=g$t;; esac
  [ -x $P/bin/$c ] || [ -x $P/sbin/$c ] || { echo "missing SDK tool $c for $t" >&2; exit 1; }
  p=$P/bin/$c; [ -x $p ] || p=$P/sbin/$c; a+=(--tool $t=$p); done
for c in cc cxx cpp; do a+=(--$c-arg=-isysroot --$c-arg $S --$c-arg=-mmacosx-version-min=15.0); done
for c in cc cxx; do a+=(--$c-arg=--start-no-unused-arguments --$c-arg=--ld-path=$P/bin/ld64.lld --$c-arg=--end-no-unused-arguments); done
$PY -B $B/sources/EmberBSD-SDK/scripts/prepare-darwin-bootstrap.py --sdk-source $B/sources/EmberBSD-SDK  --tool-root $P  --pkgsrc $B/work/ports-export-26518bb3/pkgsrc --makefiles $W/bound-mk --macos-sdk $S --deployment 15.0  --prefix $P --pkgdb $P/pkgdb --work-root $W --distfiles $B/distfiles --packages $B/packages/native  --output $W/mk.conf --utility-bin $W/tools --jobs 16 --cpu-budget 16  --link-python $PY --lock-root $B/work/coord/locks --heavy-link-context $B/work/coord/heavy-link "${a[@]}"
rc=$?; [ $rc = 0 ] || exit $rc
# Always emit the Darwin archive/TAPI/install_name tools (SDK prefix only).
lt() { for d in $P/bin; do [ -x $d/$1 ] && { echo $d/$1; return; }; done; echo "missing $1" >&2; exit 1; }
{ echo "EMBERBSD_DARWIN_LIBTOOL=	$(lt llvm-libtool-darwin)"; echo "EMBERBSD_DARWIN_TAPI_KIND=	llvm-readtapi"; echo "EMBERBSD_DARWIN_TAPI=	$(lt llvm-readtapi)"; echo "EMBERBSD_DARWIN_INSTALL_NAME_TOOL=	$(lt llvm-install-name-tool)"; } >> $W/mk.conf
# The fetch role is SDK curl; pkgsrc's fetch(1) args lack --location, so
# redirecting sites (files.pythonhosted.org) yield 0 bytes. Drive curl natively.
cat >> $W/mk.conf <<MK
FETCH_USING=		custom
FETCH_CMD=		$P/bin/curl
FETCH_BEFORE_ARGS=	--fail --location --remote-time --connect-timeout 60 --speed-limit 1024 --speed-time 60 --retry 3
FETCH_RESUME_ARGS=	-C -
FETCH_OUTPUT_ARGS=	-o
MK
