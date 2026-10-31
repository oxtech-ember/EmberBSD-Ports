#!/usr/bin/env perl
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Keep target Qt metadata independent of the build host.
use strict;
use warnings;
use File::Find;
use File::Path qw(remove_tree);

if (@ARGV == 4 && $ARGV[0] eq '--native') {
    my (undef, $root, $cc, $cxx) = @ARGV;
    for ($root, $cc, $cxx) {
        m{^/[^\n]+[^/]$} or die "absolute, non-root paths required\n";
    }
    # CMake quoted arguments must retain literal path characters.
    s/([\\"\$])/\\$1/g for ($cc, $cxx);
    for my $item (["$root/lib/cmake/Qt6/qt.toolchain.cmake", 'compiler'],
                  ["$root/lib/cmake/Qt6BuildInternals/QtBuildInternalsExtra.cmake", 'source']) {
        my ($path, $kind) = @$item;
        open my $in, '<', $path or die "$path: $!\n";
        local $/;
        my $text = <$in>;
        close $in or die "$path: $!\n";
        if ($kind eq 'compiler') {
            $text =~ s{^(set\(__qt_initial_c_compiler )"(?:\\.|[^"\\])*"\)}{$1"$cc")}m == 1 or die "missing C compiler in $path\n";
            $text =~ s{^(set\(__qt_initial_cxx_compiler )"(?:\\.|[^"\\])*"\)}{$1"$cxx")}m == 1 or die "missing C++ compiler in $path\n";
        } else {
            $text =~ s{^(set\(QT_SOURCE_TREE )"[^"]*"}{$1""}m == 1 or die "missing source tree in $path\n";
        }
        open my $out, '>', $path or die "$path: $!\n";
        print {$out} $text or die "$path: $!\n";
        close $out or die "$path: $!\n";
    }
    print "PASS: native Qt metadata uses selected compilers\n";
    exit 0;
}

my $module = @ARGV == 5 && $ARGV[4] eq "--module";
@ARGV == 4 || $module or die "usage: $0 STAGED_QT SYSROOT WORKDIR PREFIX [--module]\n";
my ($root, $sysroot, $work, $prefix) = @ARGV;
for ($root, $sysroot, $work, $prefix) {
    m{^/[^\n]+[^/]$} or die "absolute, non-root paths required\n";
}
-d "$root/lib/cmake" or die "not a staged Qt module tree\n";
if (!$module) {
    -f "$root/lib/cmake/Qt6/Qt6Config.cmake" or die "not a staged Qtbase tree\n";
    -f "$root/bin/qmake" or die "target qmake missing\n";
}

# These wrappers run the build machine's generators. Target qmake/qtpaths
# are already built and installed separately by QT_FORCE_BUILD_TOOLS.
for my $name (qw(host-qmake host-qmake6 host-qtpaths host-qtpaths6 target_qt.conf)) {
    my $path = "$root/bin/$name";
    unlink($path) or die "$path: $!\n" if -e $path || -l $path;
}
# An in-source CMake build creates this intermediate directory under mkspecs.
remove_tree("$root/mkspecs/preliminary");

my @files;
find({no_chdir => 1, wanted => sub {
    return if -l $_ || !-f $_;
    push @files, $File::Find::name if /\.(?:pri|prl|conf|pc|cmake)$/;
}}, grep { -d $_ } ("$root/mkspecs", "$root/lib"));
push @files, grep { -f $_ } map { "$root/$_" } qw(bin/qt-cmake bin/qt-cmake-create libexec/qt-cmake-private);
for my $path (@files) {
    open my $in, '<', $path or die "$path: $!\n";
    local $/;
    my $old = <$in>;
    close $in or die "$path: $!\n";
    my $text = $old;
    $text =~ s{\Q$sysroot\E(?=/)}{}g;
    $text =~ s{\Q$work\E/\.buildlink(?=/|["\s)])}{$prefix}g;
    # CMake does not sysroot absolute include directories on imported targets.
    # Qt's exported platform flags refer to the common prefix beside qt6.
    if ($path eq "$root/lib/cmake/Qt6/Qt6Targets.cmake") {
        $text =~ s{(?<=[";])\Q$prefix\E/(include|lib)(?=[/";])}{\${_IMPORT_PREFIX}/../$1}g;
    }
    $text =~ s{^PKG_CONFIG_EXECUTABLE\s*=.*$}{PKG_CONFIG_EXECUTABLE = $prefix/bin/pkg-config}mg;
    $text =~ s{^QMAKE_CC\s*=.*$}{QMAKE_CC = $prefix/gcc16/bin/gcc}mg;
    $text =~ s{^QMAKE_CXX\s*=.*$}{QMAKE_CXX = $prefix/gcc16/bin/g++}mg;
    $text =~ s{^original_cmake_path="[^"]*"$}{original_cmake_path="$prefix/bin/cmake"}mg;
    $text =~ s{^(set\(__qt_platform_initial_qt_host_path(?:_cmake_dir)? )"[^"]*"\)}{$1"")}mg;
    $text =~ s{^(set\(QT_SOURCE_TREE )"[^"]*"}{$1""}mg;
    if ($path eq "$root/mkspecs/qmodule.pri") {
        # The installed package is used natively on EmberBSD. Cross consumers
        # supply their own host tools and toolchain instead of inheriting ours.
        $text =~ s{^(CONFIG \+=|QT\.global_private\.enabled_features =)([^\n]*)}{
            my ($key, $values) = ($1, $2);
            $values =~ s/\bcross_compile\b\s*//g;
            "$key$values";
        }meg;
        $text =~ s{^(QT\.global_private\.disabled_features =[^\n]*)$}{$1 cross_compile}m
            unless $text =~ /^QT\.global_private\.disabled_features =[^\n]*\bcross_compile\b/m;
    }
    die "unresolved build path in $path\n" if index($text, $sysroot) >= 0 || index($text, $work) >= 0;
    if ($text ne $old) {
        open my $out, '>', $path or die "$path: $!\n";
        print {$out} $text or die "$path: $!\n";
        close $out or die "$path: $!\n";
    }
}
if (!$module) {
    # qmake otherwise remembers the build host's mkspec. Relative paths keep the
    # installed SDK relocatable; this file also works after ordinary package install.
    open my $conf, '>', "$root/bin/qt.conf" or die "$root/bin/qt.conf: $!\n";
    print {$conf} "[Paths]\nPrefix=..\nHostPrefix=..\nHostData=.\nSysroot=\nSysrootifyPrefix=false\nTargetSpec=netbsd-g++\nHostSpec=netbsd-g++\n" or die "$!\n";
    close $conf or die "$!\n";
}
print "PASS: target Qt metadata uses target paths and tools\n";
