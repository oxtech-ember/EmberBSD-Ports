#!/usr/bin/env perl
# Merge the recorded compiler arguments for each selected component.
use strict;
use warnings;
use JSON::PP;
my $work = shift @ARGV or die "Usage: compilation-database.pl WORK\n";
for my $component (qw(ncurses dash zsh mksh editline)) {
    my @entries;
    my %seen;
    for my $name (sort glob "$work/records/$component/*.json") {
        next if $name =~ /\/compile_commands\.json$/;
        open my $fh, '<', $name or die "$name: $!";
        local $/;
        my $entry = decode_json(<$fh>);
        my $key = join "\0", $entry->{directory}, @{$entry->{arguments}};
        push @entries, $entry if -f $entry->{file} && !$seen{$key}++;
    }
    next unless @entries;
    open my $out, '>', "$work/records/$component/compile_commands.json" or die $!;
    print {$out} JSON::PP->new->canonical->pretty->encode(\@entries);
}
