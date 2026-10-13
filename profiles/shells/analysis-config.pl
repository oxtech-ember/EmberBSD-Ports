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
    if ($component eq 'tail') {
        # Cppcheck 2.22 rejects attributed char *(name)(...) declarations.
        # Preprocess with the recorded GCC configuration before removing the
        # redundant name parentheses in exactly two gnulib declarations.
        # Macro expansion is already complete, so qualifier-generic macros
        # cannot change the meaning. Keep every attribute and line marker.
        die "Unexpected tail source\n" unless $entry->{file} =~ m{/src/tail\.c$};
        my @original = @{$entry->{arguments}};
        my $compiler = $original[0];
        my ($standard) = grep { /^-std=/ } @original;
        $standard //= '-std=gnu23'; # GCC16's production default.
        my @preprocess;
        while (@original) {
            my $arg = shift @original;
            if ($arg =~ /\A(?:-o|-MT|-MQ|-MF)\z/) { shift @original; next; }
            next if $arg =~ /\A(?:-c|-MD|-MMD|-MP|-MT.+|-MQ.+|-MF.+|-o.+)\z/;
            push @preprocess, $arg;
        }
        my $raw = "$work/analysis/tail/tail-gcc.i";
        my $normalized = "$work/analysis/tail/tail-cppcheck.c";
        push @preprocess, '-E', '-o', $raw;
        open my $ledger, '>', "$work/analysis/tail/preprocess.command.json" or die $!;
        print {$ledger} JSON::PP->new->canonical->pretty->encode({
            directory => $entry->{directory}, arguments => \@preprocess,
            file => $entry->{file}
        });
        close $ledger or die $!;
        chdir $entry->{directory} or die $!;
        system(@preprocess) == 0 or die "GCC preprocessing failed: $?\n";
        open my $input, '<', $raw or die $!;
        my $text = do { local $/; <$input> };
        for my $name (qw(mbschr getprogname)) {
            my $changed = ($text =~ s/char \* \(\Q$name\E\)(?= \()/char * $name/g);
            die "Unexpected $name declaration\n" unless $changed == 1;
        }
        open my $copy, '>', $normalized or die $!;
        print {$copy} $text;
        close $copy or die $!;
        # These identifiers are now enum members with GCC-expanded values.
        # Prevent Cppcheck's builtins from expanding them a second time.
        my @undef = map { '-UFP_' . $_ } qw(NAN INFINITE ZERO SUBNORMAL NORMAL);
        $entry->{arguments} = [$compiler, '-x', 'c', $standard, @undef,
            '-D__signed__=signed', '-c', $normalized];
        $entry->{file} = $normalized;
        next;
    }
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
