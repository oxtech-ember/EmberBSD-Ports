#!/usr/bin/env perl
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed native metadata after a cross build.
use strict;
use warnings;
use File::Copy qw(copy);
use File::Path qw(make_path);

@ARGV == 3 or die "Usage: $0 SOURCE SYSROOT NEW_OUTPUT\n";
my ($source, $sysroot, $output) = @ARGV;
for (@ARGV) {
    m{\A/[A-Za-z0-9_./+-]+\z} or die "Absolute, shell-safe paths required\n";
}
# The installed metadata names the target Clang package; the sysroot need
# not contain a compiler to describe it.
-f "$source/config.sh" && -d "$sysroot/usr/include" or die "Missing cross inputs\n";
! -e $output && ! -l $output or die "Output exists\n";
sub read_file {
    my ($name) = @_;
    open my $fh, '<', $name or die "$name: $!\n";
    local $/;
    return <$fh>;
}
my $original = read_file("$source/config.sh");
my $original_header = read_file("$source/config.h");
my ($arch) = $original =~ /^archname='(aarch64|x86_64)-netbsd-thread-multi'$/m;
defined $arch or die "Unsupported configured Perl target architecture\n";
my $text = $original;
my %replace = (
    cc => '/usr/pkg/bin/clang', ld => '/usr/pkg/bin/clang',
    ar => '/usr/bin/ar', full_ar => '/usr/bin/ar',
    nm => '/usr/bin/nm', ranlib => '/usr/bin/ranlib',
    cppstdin => '/usr/pkg/bin/clang -E',
    cpprun => '/usr/pkg/bin/clang -E',
    sh => '/bin/sh', sed => 'sed', full_sed => '/usr/bin/sed',
    make => 'make', make_set_make => '#', firstmakefile => 'makefile',
    usecrosscompile => 'undef',
    cf_by => 'EmberBSD-Ports', cf_email => '', perladmin => '',
    myhostname => '', mydomain => '', myuname => "EmberBSD $arch (cross-built)",
    config_args => '',
);
# These only describe transport and host generators. Installed ExtUtils builds
# extensions locally; the original configuration stays in the build receipt.
$replace{$_} = '' for qw(from to run sysroot hostperl hostgenerate targetdir
    targethost targetmkdir targetport targetenv);
for my $key (sort keys %replace) {
    my $count = ($text =~ s/^\Q$key\E='.*'$/$key='$replace{$key}'/mg);
    $count == 1 or die "Expected one $key field, got $count\n";
}
$text =~ s/^config_arg[0-9]+='.*'\n//mg;
$text =~ s/^config_argc=[0-9]+$/config_argc=0/m
    or die "Missing configure argument count\n";
$text =~ s{--sysroot=\Q$sysroot\E\b}{}g;
$text =~ s{\Q$sysroot\E(?=/)}{}g;
$text =~ s/^# Target system\s*:.*$/# Target system: EmberBSD $arch (cross-built)/m;
$text =~ m{/Volumes/|/private/|/Users/|(?:aarch64|x86_64)--netbsd-(?:gcc|clang|ar|nm)|/gcc16/|Cross/(?:run|to|from)}
    and die "Untranslated build-host path or tool in installed metadata\n";
# Every feature answer must remain unchanged. Metadata corrections
# are not permission to invent target probe results.
my %before = $original =~ /^((?:d_|i_|use)[A-Za-z0-9_]+)='([^']*)'$/mg;
my %after = $text =~ /^((?:d_|i_|use)[A-Za-z0-9_]+)='([^']*)'$/mg;
for my $key (keys %before) {
    next if $key eq 'usecrosscompile';
    exists $after{$key} && $after{$key} eq $before{$key}
        or die "Changed feature answer: $key\n";
}
make_path("$output/lib");
open my $fh, '>', "$output/config.sh" or die $!;
print {$fh} $text;
close $fh or die $!;
copy("$source/myconfig.SH", "$output/myconfig.SH") or die $!;
copy("$source/lib/Config_git.pl", "$output/lib/Config_git.pl") or die $!;
system($^X, "-I$output", "$source/configpm", "--chdir=$output", '--no-glossary') == 0
    or die "Target Config module generation failed\n";
# Preserve the exact configured ABI header, including cross-build provenance.
# Only installed tool names and personal build-host comments are replaced.
my $header = $original_header;
for my $pair ([LOC_SED => 'full_sed'], [CPPSTDIN => 'cppstdin'], [CPPRUN => 'cpprun']) {
    my ($macro, $key) = @$pair;
    ($header =~ s/^(#define\s+\Q$macro\E\s+)"[^"]*"/$1"$replace{$key}"/m) == 1
        or die "Missing header macro: $macro\n";
}
$header =~ s/^( \* Configured by\s*:).*$/$1 EmberBSD-Ports/m;
$header =~ s/^( \* Target system\s*:).*$/$1 EmberBSD $arch (cross-built)/m;
open my $header_fh, '>', "$output/config.h" or die $!;
print {$header_fh} $header;
close $header_fh or die $!;
read_file("$source/config.sh") eq $original &&
    read_file("$source/config.h") eq $original_header
    or die "Build configuration changed during stage generation\n";
print "Generated installed target metadata in $output\n";
