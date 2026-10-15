#!/usr/bin/env perl
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Select an audited Qtbase staging partition.
use strict;
use warnings;
use File::Find;
use File::Spec;

@ARGV == 6 or die "usage: $0 runtime|devel STAGE FULL_PLIST RUNTIME_PLIST DEVEL_PLIST SELECTED_PLIST\n";
my ($part, $stage, @lists) = @ARGV;
$part eq 'runtime' || $part eq 'devel' or die "unknown Qtbase package part\n";
File::Spec->file_name_is_absolute($stage) && $stage ne '/' && -d $stage && !-l $stage
    or die "absolute regular staging directory required\n";
$stage =~ s{/$}{};

sub manifest {
    my ($path) = @_;
    -f $path && !-l $path or die "regular manifest required: $path\n";
    open my $in, '<', $path or die "$path: $!\n";
    my %files;
    while (my $name = <$in>) {
        chomp $name;
        next if $name eq '' || $name =~ /^\@comment(?: |$)/;
        $name !~ /[\x00-\x20\x7f]/ && $name !~ m{^/|/$|\$\{|^\@}
            && !grep { $_ eq '' || $_ eq '.' || $_ eq '..' } split m{/}, $name
            or die "unsafe manifest entry: $name\n";
        !$files{$name}++ or die "duplicate manifest entry: $name\n";
    }
    close $in or die "$path: $!\n";
    keys %files or die "empty Qtbase partition\n";
    return \%files;
}

my ($full, $runtime, $devel, $selected) = map { manifest($_) } @lists;
for my $name (keys %$runtime) {
    !$devel->{$name} or die "Qtbase partitions overlap: $name\n";
}
my %union = (%$runtime, %$devel);
keys(%union) == keys(%$full) && !grep { !$union{$_} } keys %$full
    or die "Qtbase partition union differs from the complete PLIST\n";
my $wanted = $part eq 'runtime' ? $runtime : $devel;
keys(%$wanted) == keys(%$selected) && !grep { !$wanted->{$_} } keys %$selected
    or die "selected package PLIST differs from its declared partition\n";

# Walk without following symlinks. Validate the complete normalized staging
# tree before deleting any unselected path. A new or missing upstream file is
# a package error, not permission to prune it silently.
my (%actual, @directories);
find({no_chdir => 1, bydepth => 1, wanted => sub {
    my $path = $File::Find::name;
    return if $path eq $stage;
    my $name = substr($path, length($stage) + 1);
    if (-l $path || -f $path) {
        $full->{$name} or die "unlisted staged file: $name\n";
        $actual{$name} = 1;
    } elsif (-d $path) {
        push @directories, $path;
    } else {
        die "unsupported staged file type: $name\n";
    }
}}, $stage);
for my $name (keys %$full) {
    $actual{$name} or die "missing complete-stage file: $name\n";
}
for my $name (sort keys %actual) {
    next if $wanted->{$name};
    unlink "$stage/$name" or die "cannot select staging partition: $name: $!\n";
}
for my $directory (@directories) {
    # Empty directories have no package owner in these static manifests.
    opendir my $dir, $directory or die "$directory: $!\n";
    my @entries = grep { $_ ne '.' && $_ ne '..' } readdir $dir;
    closedir $dir or die "$directory: $!\n";
    rmdir $directory or die "$directory: $!\n" if !@entries;
}
print "PASS: complete Qtbase stage has an exhaustive, disjoint $part partition\n";
