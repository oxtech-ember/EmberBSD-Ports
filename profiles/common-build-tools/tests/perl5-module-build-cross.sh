#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
#
# Usage: BMAKE=bmake perl5-module-build-cross.sh PKGSRC MAKECONF TARGET_CC NEW_WORK
#
# Cross builds of Module::Build and Module::Install distributions stopped with
# "Cross Perl modules currently support MakeMaker only". Module::Build read
# the host Config and picked the host platform, so an XS module became a
# host Mach-O bundle. Require that the cross recipes accept these module
# types and depend on the patched native Module::Build, then run Build.PL,
# Build and Build install with the host Perl and the target build context
# and require a target ELF module in the target vendor architecture tree.
set -eu
[ "$#" -eq 4 ] || { echo "Usage: $0 PKGSRC MAKECONF TARGET_CC NEW_WORK" >&2; exit 2; }
pkgsrc=$1 makeconf=$2 cc=$3
case "$4" in /*) ;; *) echo "$0: NEW_WORK must be absolute" >&2; exit 2;; esac
mkdir "$4"
work=$4
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bm() { dir=$1; shift; MAKECONF=$makeconf "${BMAKE:-bmake}" -C "$pkgsrc/$dir" MAKECONF="$makeconf" "$@"; }
[ "$(bm devel/p5-Params-Classify -V '${USE_CROSS_COMPILE:Uno:tl}')" = yes ] ||
	{ echo "$0: select a MAKECONF for a cross build" >&2; exit 2; }
status=0
for pkg in devel/p5-Params-Classify devel/p5-Module-Build devel/p5-File-ShareDir; do
	case "$(bm $pkg -V PKG_FAIL_REASON)" in
	*"MakeMaker only"*) echo "FAIL: $pkg is refused as a cross Perl module"; status=1;;
	esac
done
need=$(bm devel/p5-Module-Build -V '${PKGNAME}')
case " $(bm devel/p5-Params-Classify -V TOOL_DEPENDS) " in
*" p5-Module-Build>=${need#p5-Module-Build-}:"*) ;;
*) echo "FAIL: cross Module::Build packages do not need native $need"; status=1;;
esac
host=$(bm devel/p5-Params-Classify -V '${EMBERBSD_CROSS_BUILD_PERL}')
python=$(bm devel/p5-Params-Classify -V '${EMBERBSD_CROSS_BUILD_PYTHON}')
target=$(bm devel/p5-Params-Classify -V '${EMBERBSD_PERL_TARGET_CONFIG}')
sysroot=$(bm devel/p5-Params-Classify -V '${EMBERBSD_CROSS_SYSROOT}')
distfile=$(bm devel/p5-Module-Build -V '${DISTDIR}')/$(bm devel/p5-Module-Build -V '${DISTNAME}').tar.gz
mkdir "$work/mb"
tar -xzf "$distfile" -C "$work/mb"
mb=$(echo "$work"/mb/Module-Build-*)
for p in "$pkgsrc"/devel/p5-Module-Build/patches/patch-*; do
	[ -f "$p" ] && (cd "$mb" && patch -s -p0 < "$p")
done
"$python" -B "$pkgsrc/lang/perl5/files/prepare-build-config.py" --host-perl "$host" \
	--target-config "$target" --sysroot "$sysroot" --cc "$cc" --ld "$cc" \
	--ar "${cc%clang}ar" --ranlib "${cc%clang}ranlib" --cflags=-O2 --ldflags= \
	--output "$work/config.json"
mkdir "$work/probe" "$work/probe/lib"
cp "$here/perl-xs/EmberProbe.xs" "$work/probe/lib/"
cp "$here/perl-xs/EmberProbe.pm" "$work/probe/lib/"
cat > "$work/probe/Build.PL" <<'PL'
use strict;
use warnings;
use Module::Build;
Module::Build->new(module_name => 'EmberProbe', dist_version => '0.01',
    license => 'bsd')->create_build_script;
PL
(
	cd "$work/probe"
	unset PERL5OPT
	PERL5LIB=$mb/lib EMBERBSD_PERL_BUILD_CONFIG=$work/config.json
	export PERL5LIB EMBERBSD_PERL_BUILD_CONFIG
	"$host" Build.PL --installdirs=vendor > build.log 2>&1 &&
	"$host" Build >> build.log 2>&1 &&
	"$host" Build install --destdir "$work/dest" >> build.log 2>&1 &&
	"$host" -MModule::Build -e 'print Module::Build->os_type, " ",
	    join(",", sort grep m{/Platform/}, keys %INC), "\n"' > platform.txt
) || { echo "FAIL: Build.PL route stopped; see $work/probe/build.log"; exit 1; }
case "$(cat "$work/probe/platform.txt")" in
"Unix Module/Build/Platform/Unix.pm") ;;
*) echo "FAIL: Module::Build selected $(cat "$work/probe/platform.txt")"; status=1;;
esac
arch=$(EMBERBSD_PERL_BUILD_CONFIG=$work/config.json "$host" -e '
	use JSON::PP; local $/; open my $f, "<", $ENV{EMBERBSD_PERL_BUILD_CONFIG} or die;
	print decode_json(<$f>)->{installvendorarch}')
so=$work/dest$arch/auto/EmberProbe/EmberProbe.so
if [ -f "$so" ]; then
	"$host" -e 'open my $f, "<:raw", $ARGV[0] or die; read $f, my $h, 20;
		my ($m, $c, $d) = unpack "a4 C C", $h; my $e = unpack "v", substr($h, 18, 2);
		exit !($m eq "\x7fELF" && $c == 2 && $d == 1 && $e == 183)' "$so" ||
		{ echo "FAIL: $so is not an aarch64 ELF module"; status=1; }
else
	echo "FAIL: no EmberProbe.so in the target vendor architecture tree"; status=1
fi
[ "$status" -eq 0 ] || exit 1
echo "PASS: cross Module::Build builds a target XS module with the target Config"
