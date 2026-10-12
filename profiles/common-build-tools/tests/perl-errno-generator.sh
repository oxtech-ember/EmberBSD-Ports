#!/bin/sh
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), exercise the unchanged upstream subroutine.
set -eu
[ "$#" = 5 ] || {
    echo 'Usage: PERL=host-perl sh perl-errno-generator.sh PERL_SOURCE CROSS_CC SYSROOT NEW_WORK HEADER' >&2
    exit 2
}
source=$1 cc=$2 sysroot=$3 work=$4 header=$5
: "${PERL:?Select the native Perl 5.44 executable}"
for path in "$source" "$cc" "$sysroot" "$work" "$header" "$PERL"; do
    case "$path" in /*) ;; *) exit 2 ;; esac
    case "$path" in *[!a-zA-Z0-9_./+-]*) exit 2 ;; esac
done
mkdir "$work"
cat > "$work/check.pl" <<'PL'
use strict;
use warnings;
my ($source, $compiler, $sysroot, $header, $failure) = @ARGV;
open my $fh, '<', "$source/ext/Errno/Errno_pm.PL" or die $!;
my $text = do { local $/; <$fh> };
my ($routine) = $text =~ /(sub process_file \{.*?\n\})\n\nmy \$cppstdin;/s;
defined $routine or die "Missing upstream routine\n";
our %Config = (gccversion => '16.2.0', cc => $compiler,
    cppflags => "--sysroot=$sysroot");
our %err;
our $IsMSWin32 = 0;
local $^O = 'netbsd';
eval $routine;
die $@ if $@;
my $ok = eval { process_file($header); 1 };
if ($failure) {
    die "Failed preprocessor was accepted\n" if $ok;
    die $@ unless $@ =~ /Failed to read errno definitions/;
    print "PASS: compiler failure rejects partial definitions\n";
} else {
    die $@ unless $ok;
    die "Missing public errno constants\n" unless exists $err{ENOENT} && exists $err{EIO};
    print "PASS: nested target cdefs header has public errno prerequisites\n";
}
PL
cat > "$work/broken-cc" <<'CC'
#!/bin/sh
printf '#define EIO 5\n'
exit 3
CC
chmod +x "$work/broken-cc"
"$PERL" "$work/check.pl" "$source" "$cc" "$sysroot" "$header" 0
"$PERL" "$work/check.pl" "$source" "$work/broken-cc" "$sysroot" "$header" 1
