#!/usr/bin/env perl
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed native metadata after a cross build.
use strict;
use warnings;
use File::Basename qw(dirname);
use File::Compare qw(compare);
use File::Copy qw(copy);
use File::Path qw(make_path);
use File::Temp qw(tempdir);

@ARGV == 3 or die "Usage: $0 SOURCE SYSROOT OUTPUT\n";
my ($source, $sysroot, $output) = @ARGV;
for (@ARGV) {
    m{\A/[A-Za-z0-9_./+-]+\z} or die "Absolute, shell-safe paths required\n";
}
# The installed metadata names the target Clang package; the sysroot need
# not contain a compiler to describe it.
-f "$source/config.sh" && -d "$sysroot/usr/include" or die "Missing cross inputs\n";
(-e $output || -l $output) && (-l $output || !-d $output)
    and die "Output is not a directory\n";
my $parent = dirname($output);
-d $parent or die "Missing output parent directory\n";
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
my ($rm_args) = $original =~ /^rm_try='[^ ]+( .*)'$/m;
defined $rm_args or die "Missing rm_try command arguments\n";
my $text = $original;
my %replace = (
    cc => '/usr/pkg/bin/clang', ld => '/usr/pkg/bin/clang',
    ar => '/usr/bin/ar', full_ar => '/usr/bin/ar',
    nm => '/usr/bin/nm', ranlib => '/usr/bin/ranlib',
    cppstdin => '/usr/pkg/bin/clang -E',
    cpprun => '/usr/pkg/bin/clang -E',
    sh => '/bin/sh', sed => 'sed', full_sed => '/usr/bin/sed',
    aphostname => '/bin/hostname', lns => '/bin/ln -s',
    rm_try => '/bin/rm' . $rm_args,
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
my $stage = tempdir(".target-config.XXXXXXXX", DIR => $parent, CLEANUP => 1);
make_path("$stage/lib");
open my $fh, '>', "$stage/config.sh" or die $!;
print {$fh} $text;
close $fh or die $!;
copy("$source/myconfig.SH", "$stage/myconfig.SH") or die $!;
copy("$source/lib/Config_git.pl", "$stage/lib/Config_git.pl") or die $!;
system($^X, "-I$stage", "$source/configpm", "--chdir=$stage", '--no-glossary') == 0
    or die "Target Config module generation failed\n";
# Preserve the exact configured ABI header, including cross-build provenance.
# Only installed tool names and personal build-host comments are replaced.
my $header = $original_header;
for my $pair ([LOC_SED => 'full_sed'], [CPPSTDIN => 'cppstdin'], [CPPRUN => 'cpprun'],
              [PHOSTNAME => 'aphostname']) {
    my ($macro, $key) = @$pair;
    ($header =~ s/^(#define\s+\Q$macro\E\s+)"[^"]*"/$1"$replace{$key}"/m) == 1
        or die "Missing header macro: $macro\n";
}
$header =~ s/^( \* Configured by\s*:).*$/$1 EmberBSD-Ports/m;
$header =~ s/^( \* Target system\s*:).*$/$1 EmberBSD $arch (cross-built)/m;
open my $header_fh, '>', "$stage/config.h" or die $!;
print {$header_fh} $header;
close $header_fh or die $!;
read_file("$source/config.sh") eq $original &&
    read_file("$source/config.h") eq $original_header
    or die "Build configuration changed during stage generation\n";
my @outputs = qw(config.h config.sh myconfig.SH lib/Config.pm
    lib/Config.pod lib/Config_git.pl lib/Config_heavy.pl);
for my $name (@outputs) {
    my $staged = "$stage/$name";
    -f $staged && !-l $staged or die "Missing generated output: $name\n";
}
if (-e $output) {
    -d $output && !-l $output or die "Output is not a directory\n";
    my $lib = "$output/lib";
    (-e $lib || -l $lib) && (!-d $lib || -l $lib)
        and die "Output lib is not a directory\n";
    for my $name (@outputs) {
        my $dest = "$output/$name";
        (-e $dest || -l $dest) && (!-f $dest || -l $dest)
            and die "Output is not a regular file: $dest\n";
    }
}
if (!-e $output) {
    mkdir $output or die "Create output directory $output: $!\n";
}
make_path("$output/lib");
for my $name (@outputs) {
    my $staged = "$stage/$name";
    my $dest = "$output/$name";
    if (-e $dest || -l $dest) {
        next if compare($staged, $dest) == 0;
    }
    rename($staged, $dest) or die "Replace $dest: $!\n";
}
print "Generated installed target metadata in $output\n";
