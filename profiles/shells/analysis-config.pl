#!/usr/bin/env perl
# Add the compiler's implicit headers and macros to a Cppcheck-only database.
use strict;
use warnings;
use JSON::PP;
use File::Spec;
my ($work, $component) = @ARGV;
die "Usage: analysis-config.pl WORK COMPONENT\n" unless defined $component;
die "Invalid component\n" unless $component =~ /\A(?:dash|zsh|mksh|ncurses|editline|tail)\z/;
open my $fh, '<', "$work/records/$component/compile_commands.json" or die $!;
my $entries = do { local $/; decode_json(<$fh>) };
open my $includes, '<', "$work/analysis/config/includes.txt" or die $!;
my @includes = <$includes>;
chomp @includes;
my $number = 0;
for my $entry (@$entries) {
    # Cppcheck's project importer retains only one forced include. Preserve
    # the compiler configuration as well as implicit builtin definitions.
    my (@args, @forced);
    my @original = @{$entry->{arguments}};
    while (@original) {
        my $arg = shift @original;
        if ($arg eq '-include') {
            push @forced, File::Spec->rel2abs(shift @original, $entry->{directory});
        } else {
            push @args, $arg;
        }
    }
    my $header = "$work/analysis/$component/preamble-" . ++$number . '.h';
    open my $preamble, '>', $header or die $!;
    for my $name ("$work/analysis/config/compiler-defines.h", @forced) {
        die "Unsupported header path\n" if $name =~ /[\"\n\r]/;
        print {$preamble} qq{#include "$name"\n};
    }
    close $preamble or die $!;
    $entry->{arguments} = [@args, map { '-I' . $_ } @includes];
    push @{$entry->{arguments}}, '-include', $header;
    # Cppcheck 2.22 rejects the GNU spelling in Linux's __int128 typedef.
    # This is the identical signed keyword, not a changed type or warning mask.
    push @{$entry->{arguments}}, '-D__signed__=signed';
    if ($component eq 'dash' && $entry->{file} =~ m{/jobs\.c$}) {
        # Cppcheck 2.22's parser rejects valid C '-!block'. Parentheses
        # preserve the exact unary operation; production sources stay intact.
        # A minimal reproduction and GCC assembly comparison are recorded in
        # the dash validation document. Keep original diagnostic line numbers.
        open my $input, '<', $entry->{file} or die $!;
        my $text = do { local $/; <$input> };
        my $changed = ($text =~ s/-!block/-(!block)/g);
        die "Unexpected dash job expression\n" unless $changed == 1;
        my $original = $entry->{file};
        my $normalized = "$work/analysis/$component/jobs-cppcheck.c";
        open my $copy, '>', $normalized or die $!;
        print {$copy} qq{#line 1 "$original"\n}, $text;
        close $copy or die $!;
        for my $arg (@{$entry->{arguments}}) {
            $arg = $normalized if $arg eq $original || $arg eq 'jobs.c';
        }
        $entry->{file} = $normalized;
    }
}
open my $out, '>', "$work/analysis/$component/cppcheck_commands.json" or die $!;
print {$out} JSON::PP->new->canonical->pretty->encode($entries);
