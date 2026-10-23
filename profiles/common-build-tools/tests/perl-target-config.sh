#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), test installed metadata from a real cross build.
set -eu
[ "$#" = 4 ] || { echo "Usage: $0 SOURCE SYSROOT HOST_PERL NEW_WORK" >&2; exit 2; }
source=$1 sysroot=$2 perl=$3 work=$4
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
helper=$root/../../pkgsrc/lang/perl5/files/target-config.pl
mkdir "$work"
shasum -a 256 "$source/config.sh" "$source/config.h" \
    "$source/lib/Config.pm" "$source/lib/Config_heavy.pl" > "$work/before.sha256"
"$perl" "$helper" "$source" "$sysroot" "$work/native" > "$work/generate.log" 2>&1
shasum -a 256 "$source/config.sh" "$source/config.h" \
    "$source/lib/Config.pm" "$source/lib/Config_heavy.pl" > "$work/after.sha256"
cmp "$work/before.sha256" "$work/after.sha256"
archname=$(sed -n "s/^archname='\([^']*\)'$/\1/p" "$source/config.sh")
case "$archname" in aarch64-netbsd-thread-multi|x86_64-netbsd-thread-multi) ;; *) exit 1;; esac
EMBER_TEST_PERL_ARCHNAME=$archname "$perl" -I"$work/native/lib" -MConfig -e '
    die "architecture\n" unless $Config{archname} eq $ENV{EMBER_TEST_PERL_ARCHNAME};
    die "ABI\n" unless $Config{ptrsize} == 8 && $Config{ivsize} == 8;
    die "features\n" unless $Config{usedl} eq "define" && $Config{useshrplib} eq "true";
    die "compiler\n" unless $Config{cc} eq "/usr/pkg/gcc16/bin/gcc";
    die "cross transport\n" if $Config{sysroot} || $Config{run} || $Config{hostperl};
    die "shell\n" unless $Config{sh} eq "/bin/sh";
    print "Target Config API: PASS\n";
' > "$work/api.log"
for item in before after; do
    case "$item" in before) header=$source/config.h ;; after) header=$work/native/config.h ;; esac
    sed -n '/^#define\|^#undef/p' "$header" |
        sed '/^#define LOC_SED[[:space:]]/d; /^#define CPPSTDIN[[:space:]]/d; /^#define CPPRUN[[:space:]]/d' \
        > "$work/$item-abi.txt"
done
cmp "$work/before-abi.txt" "$work/after-abi.txt"
if "$perl" "$helper" "$source" "$sysroot" "$work/native" > "$work/existing.log" 2>&1; then
    echo 'Existing output was accepted' >&2; exit 1
fi
grep -q 'Output exists' "$work/existing.log"
mkdir "$work/bad"
cp "$source/config.sh" "$source/config.h" "$work/bad/"
printf "unexpected_host_tool='/Volumes/forbidden/build-tool'\n" >> "$work/bad/config.sh"
if "$perl" "$helper" "$work/bad" "$sysroot" "$work/rejected" > "$work/leak.log" 2>&1; then
    echo 'Host path was accepted' >&2; exit 1
fi
grep -q 'Untranslated build-host path' "$work/leak.log"
echo 'PASS: target metadata, unchanged source and ABI, existing output and host-path rejection'
