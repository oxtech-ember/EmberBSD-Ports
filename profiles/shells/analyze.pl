#!/usr/bin/env perl
# Replay real C compilations with GCC's path analyzer and separate outputs.
use strict;
use warnings;
use JSON::PP;
use File::Path qw(make_path);

my ($work, $component, $mode) = @ARGV;
$mode //= 'gcc';
die "Usage: analyze.pl WORK COMPONENT [gcc|clang]\n" unless defined $component;
die "Invalid component\n" unless $component =~ /\A(?:dash|zsh|mksh|ncurses|editline)\z/;
die "Invalid analyzer\n" unless $mode =~ /\A(?:gcc|clang)\z/;
my $database = "$work/records/$component/compile_commands.json";
open my $fh, '<', $database or die "$database: $!";
my $entries = do { local $/; decode_json(<$fh>) };
my $output = "$work/analysis/$component/$mode";
make_path($output);
my ($number, $failed) = (0, 0);
open my $status, '>', "$output/status.tsv" or die $!;
print {$status} "# source\tprocess_status\n";
for my $entry (@$entries) {
    my @args = @{$entry->{arguments}};
    $args[0] = $ENV{CLANG} // 'clang' if $mode eq 'clang';
    my @command;
    while (@args) {
        my $arg = shift @args;
        if ($arg eq '-o') { shift @args; next; }
        next if $mode eq 'clang' && $arg eq '-c';
        # Clang has no GCC x86 data-alignment or inliner tuning switch.
        next if $mode eq 'clang' && $arg eq '-malign-data=abi';
        if ($mode eq 'clang' && $arg eq '--param') { shift @args; next; }
        next if $arg =~ /\A(?:-o.+|-O[0-9sgfast]+)\z/;
        push @command, $arg;
    }
    ++$number;
    if ($mode eq 'clang') {
        push @command, '-O0', '-std=gnu23', '--analyze', '-Xanalyzer',
            '-analyzer-output=text', '-o', "$output/$number.plist";
    } else {
        push @command, '-O0', '-fanalyzer', '-o', "$output/$number.o";
    }
    chdir $entry->{directory} or die $!;
    my $pid = fork();
    die "fork: $!" unless defined $pid;
    if (!$pid) {
        open STDOUT, '>', "$output/$number.log" or die $!;
        open STDERR, '>&', \*STDOUT or die $!;
        exec 'timeout', '120', @command;
        die "exec: $!";
    }
    waitpid $pid, 0;
    my $result = $?;
    $failed ||= $result != 0;
    print {$status} "$entry->{file}\t$result\n";
}
print "$component/$mode: analyzed $number compilation commands; process failures=$failed\n";
exit($failed ? 1 : 0);
