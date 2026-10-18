#!/usr/bin/env perl
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Select an audited protobuf staging partition.
use strict;
use warnings;
use File::Find;
use File::Spec;

@ARGV == 6 or die "usage: $0 runtime|devel STAGE FULL_PLIST RUNTIME_PLIST DEVEL_PLIST SELECTED_PLIST\n";
my ($part, $stage, @lists) = @ARGV;
$part eq 'runtime' || $part eq 'devel' or die "unknown protobuf package part\n";
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
    keys %files or die "empty protobuf partition\n";
    return \%files;
}

my ($full, $runtime, $devel, $selected) = map { manifest($_) } @lists;
for my $name (keys %$runtime) {
    !$devel->{$name} or die "protobuf partitions overlap: $name\n";
}
my %union = (%$runtime, %$devel);
keys(%union) == keys(%$full) && !grep { !$union{$_} } keys %$full
    or die "protobuf partition union differs from the complete PLIST\n";
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
# Resolve links component by component before pruning. A lexical ../ collapse
# must not bypass a directory symlink. Runtime links must survive without SDK;
# SDK links may use runtime files through the exact package dependency.
for my $name (sort keys %actual) {
    next if !-l "$stage/$name";
    my @todo = split m{/}, $name;
    my (@resolved, $hops);
    while (@todo) {
        my $component = shift @todo;
        next if $component eq '' || $component eq '.';
        if ($component eq '..') {
            @resolved or die "escaping protobuf stage link: $name\n";
            pop @resolved;
            next;
        }
        my $relative = join '/', @resolved, $component;
        my $path = "$stage/$relative";
        if (-l $path) {
            ++$hops <= 64 or die "cyclic or excessive protobuf stage link: $name\n";
            !$runtime->{$name} || $runtime->{$relative}
                or die "runtime link uses SDK: $name -> $relative\n";
            my $target = readlink $path;
            defined($target) && length($target) && $target !~ /[\x00-\x20\x7f]/ && $target !~ m{/$}
                && !File::Spec->file_name_is_absolute($target)
                or die "unsafe protobuf stage link: $name\n";
            unshift @todo, split m{/}, $target;
            next;
        }
        -e $path or die "missing protobuf stage link target: $name\n";
        !@todo || -d $path or die "non-directory protobuf link component: $name\n";
        push @resolved, $component;
    }
    my $terminal = join '/', @resolved;
    $actual{$terminal} && -f "$stage/$terminal"
        or die "protobuf stage link does not resolve to a listed file: $name\n";
    !$runtime->{$name} || $runtime->{$terminal}
        or die "runtime link resolves to SDK: $name -> $terminal\n";
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
print "PASS: complete protobuf stage has an exhaustive, disjoint $part partition\n";
