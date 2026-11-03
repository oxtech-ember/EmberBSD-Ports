#!/usr/bin/env perl
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Select an audited Qtbase staging partition.
use strict;
use warnings;
use File::Find;
use File::Copy qw(copy);
use File::Path qw(make_path remove_tree);
use File::Spec;
use File::Basename qw(dirname basename);
use Cwd qw(abs_path);

my $operation = shift @ARGV // '';
my $shared;
my $feature_cache;
if ($operation eq 'handoff-runtime') {
    @ARGV == 7 or die "usage: $0 handoff-runtime STAGE FULL_PLIST RUNTIME_PLIST DEVEL_PLIST SELECTED_PLIST SHARED_STAGE CMAKE_CACHE\n";
    $feature_cache = pop @ARGV;
    $operation = 'runtime';
    $shared = pop @ARGV;
    unshift @ARGV, $operation;
} elsif ($operation eq 'copy-devel') {
    @ARGV == 6 or die "usage: $0 copy-devel SHARED_STAGE DESTINATION FULL_PLIST RUNTIME_PLIST DEVEL_PLIST SELECTED_PLIST\n";
    my $source = shift @ARGV;
    my $destination = shift @ARGV;
    copy_devel($source, $destination, @ARGV);
    exit 0;
} else {
    unshift @ARGV, $operation;
    @ARGV == 7 or die "usage: $0 runtime|devel STAGE FULL_PLIST RUNTIME_PLIST DEVEL_PLIST SELECTED_PLIST CMAKE_CACHE\n";
    $feature_cache = pop @ARGV;
}
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

sub portal_feature {
    my ($path) = @_;
    -f $path && !-l $path or die "regular Qtbase CMake cache required: $path\n";
    open my $in, '<', $path or die "$path: $!\n";
    my @values;
    while (my $line = <$in>) {
        push @values, $1 if $line =~ /^QT_FEATURE_xdg_desktop_portal_file_transfer:INTERNAL=(ON|OFF)\r?\n?$/;
    }
    close $in or die "$path: $!\n";
    @values == 1 or die "missing or duplicate Qt portal file-transfer feature in $path\n";
    return $values[0] eq 'ON';
}

sub apply_portal_feature {
    my ($enabled, @manifests) = @_;
    return if $enabled;
    for my $manifest (@manifests) {
        delete $manifest->{$_} for grep {
            m{^qt6/include/QtGui/[^/]+/QtGui/private/qxdgdesktopportalfiletransfer_p\.h$}
        } keys %$manifest;
    }
}

sub filter_selected_manifest {
    my ($path, $enabled) = @_;
    return if $enabled;
    my $pattern = qr{^qt6/include/QtGui/[^/]+/QtGui/private/qxdgdesktopportalfiletransfer_p\.h\r?\n?$};
    open my $in, '<', $path or die "$path: $!\n";
    my @lines = <$in>;
    close $in or die "$path: $!\n";
    my @kept = grep { !/$pattern/ } @lines;
    return if @kept == @lines;
    my $tmp = "$path.tmp.$$";
    open my $out, '>', $tmp or die "$tmp: $!\n";
    print {$out} @kept or die "$tmp: $!\n";
    close $out or die "$tmp: $!\n";
    rename($tmp, $path) or die "cannot update selected Qtbase PLIST: $!\n";
}

sub read_portal_marker {
    my ($path) = @_;
    -f $path && !-l $path or die "Qtbase shared-stage feature marker is missing: $path\n";
    open my $in, '<', $path or die "$path: $!\n";
    local $/;
    my $value = <$in> // '';
    close $in or die "$path: $!\n";
    return 1 if $value eq "ON\n";
    return 0 if $value eq "OFF\n";
    die "invalid Qtbase shared-stage feature marker: $path\n";
}

my ($full, $runtime, $devel, $selected) = map { manifest($_) } @lists;
my $portal_enabled = portal_feature($feature_cache);
apply_portal_feature($portal_enabled, $full, $runtime, $devel, $selected);
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
unless (defined $shared) {
    filter_selected_manifest($lists[3], $portal_enabled);
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
}
print "PASS: complete Qtbase stage has an exhaustive, disjoint $part partition\n";

sub canonical_dir {
    my ($path) = @_;
    File::Spec->file_name_is_absolute($path) && -d $path && !-l $path
        or die "absolute regular directory required: $path\n";
    return abs_path($path) // die "cannot resolve directory: $path\n";
}

sub reject_overlap {
    my ($left, $right) = @_;
    my $a = canonical_target($left);
    my $b = canonical_target($right);
    $a ne '/' && $b ne '/' && $a ne $b
        && index($a, "$b/") != 0 && index($b, "$a/") != 0
        or die "Qtbase shared stage and package destination overlap\n";
}

sub canonical_target {
    my ($path) = @_;
    return abs_path($path) if -e $path;
    my $parent = abs_path(dirname($path));
    defined $parent or die "cannot resolve Qtbase stage parent: $path\n";
    return File::Spec->catdir($parent, basename($path));
}

sub copy_manifest {
    my ($source, $destination, $entries) = @_;
    my $root = canonical_dir($source);
    for my $name (sort keys %$entries) {
        my $from = "$root/$name";
        my $to = "$destination/$name";
        my $parent = $to;
        $parent =~ s{/[^/]+$}{};
        make_path($parent) unless -d $parent;
        if (-l $from) {
            my $target = readlink($from);
            defined $target or die "cannot read symlink: $from\n";
            symlink($target, $to) or die "cannot copy symlink $from: $!\n";
        } elsif (-f $from) {
            copy($from, $to) or die "cannot copy $from: $!\n";
            my $mode = (stat($from))[2] & 07777;
            chmod($mode, $to) or die "cannot preserve mode on $to: $!\n";
        } else {
            die "unsupported Qtbase stage entry: $name\n";
        }
    }
}

sub copy_devel {
    my ($source, $destination, @manifest_paths) = @_;
    my $source_root = canonical_dir($source);
    File::Spec->file_name_is_absolute($destination) && !-l $destination
        or die "absolute Qtbase devel destination required\n";
    if (-e $destination) {
        -d $destination or die "Qtbase devel destination is not a directory\n";
        opendir my $dir, $destination or die "$destination: $!\n";
        my @entries = grep { $_ ne '.' && $_ ne '..' } readdir $dir;
        closedir $dir or die "$destination: $!\n";
        !@entries or die "Qtbase devel destination must be empty\n";
    }
    my ($full, $runtime, $devel, $selected) = map { manifest($_) } @manifest_paths;
    my $portal_enabled = read_portal_marker("$source.features");
    apply_portal_feature($portal_enabled, $full, $runtime, $devel, $selected);
    for my $name (keys %$runtime) {
        !$devel->{$name} or die "Qtbase partitions overlap: $name\n";
    }
    my %union = (%$runtime, %$devel);
    keys(%union) == keys(%$full) && !grep { !$union{$_} } keys %$full
        or die "Qtbase partition union differs from the complete PLIST\n";
    keys(%$devel) == keys(%$selected) && !grep { !$devel->{$_} } keys %$selected
        or die "selected package PLIST differs from its declared partition\n";
    my (%actual, @dirs);
    find({no_chdir => 1, bydepth => 1, wanted => sub {
        my $path = $File::Find::name;
        return if $path eq $source_root;
        my $name = substr($path, length($source_root) + 1);
        if (-l $path || -f $path) {
            $full->{$name} or die "unlisted retained Qtbase file: $name\n";
            $actual{$name} = 1;
        } elsif (-d $path) {
            push @dirs, $path;
        } else {
            die "unsupported retained Qtbase file: $name\n";
        }
    }}, $source_root);
    for my $name (keys %$full) {
        $actual{$name} or die "missing retained Qtbase file: $name\n";
    }
    reject_overlap($source_root, $destination);
    filter_selected_manifest($manifest_paths[3], $portal_enabled);
    make_path($destination) unless -d $destination;
    copy_manifest($source_root, $destination, $devel);
    print "PASS: copied devel partition from retained complete Qtbase stage\n";
}

if (defined $shared) {
    my $stage_root = canonical_dir($stage);
    File::Spec->file_name_is_absolute($shared) && !-l $shared
        or die "absolute Qtbase shared-stage path required\n";
    reject_overlap($stage_root, $shared);
    filter_selected_manifest($lists[3], $portal_enabled);
    my $feature_marker = "$shared.features";
    if (-e $feature_marker || -l $feature_marker) {
        -f $feature_marker && !-l $feature_marker
            or die "unsafe Qtbase feature marker: $feature_marker\n";
        unlink $feature_marker or die "cannot remove old Qtbase feature marker: $!\n";
    }
    if (-d $shared) {
        # The retained tree is being replaced, so its old manifest need not
        # match the freshly validated installation.
        remove_tree($shared) or die "cannot remove old shared stage\n";
    } else {
        !-e $shared or die "Qtbase shared stage is not a directory\n";
        my $parent = $shared;
        $parent =~ s{/[^/]+$}{};
        make_path($parent) unless -d $parent;
    }
    rename($stage, $shared) or die "cannot retain complete Qtbase stage: $!\n";
    my $marker_tmp = "$feature_marker.tmp.$$";
    open my $marker, '>', $marker_tmp or die "$marker_tmp: $!\n";
    print {$marker} ($portal_enabled ? "ON\n" : "OFF\n") or die "$marker_tmp: $!\n";
    close $marker or die "$marker_tmp: $!\n";
    rename($marker_tmp, $feature_marker) or die "cannot publish Qtbase feature marker: $!\n";
    make_path($stage);
    copy_manifest($shared, $stage, $runtime);
}
