#!/usr/bin/env perl
# Record actual production compilations without changing their arguments.
use strict;
use warnings;
use Cwd qw(getcwd abs_path);
use JSON::PP;

my $compiler = $ENV{SHELL_REAL_CC} or die "Set SHELL_REAL_CC\n";
my $output = $ENV{SHELL_CC_RECORDS} or die "Set SHELL_CC_RECORDS\n";
if (grep { $_ eq '-c' } @ARGV) {
    for my $arg (@ARGV) {
        next unless $arg =~ /\.c$/ && -f $arg;
        next if $arg =~ /(?:conftest|conftstm|conftestval)\.c$/;
        open my $fh, '>', "$output/$$.json" or die "$output: $!";
        print {$fh} encode_json({ directory => getcwd(),
            arguments => [$compiler, @ARGV], file => abs_path($arg) });
        close $fh or die "$output: $!";
        last;
    }
}
exec {$compiler} $compiler, @ARGV;
die "$compiler: $!";
