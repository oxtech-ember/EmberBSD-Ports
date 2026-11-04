#!/usr/bin/env perl
# SPDX-License-Identifier: BSD-2-Clause
# Exercise the installed XS module used for monotonic process deadlines.
use strict;
use warnings;
use Time::HiRes qw(clock_gettime clock_getres CLOCK_MONOTONIC sleep);

my $resolution = clock_getres(CLOCK_MONOTONIC);
die "invalid monotonic clock resolution\n" unless $resolution > 0;
my $before = clock_gettime(CLOCK_MONOTONIC);
sleep(0.02);
my $after = clock_gettime(CLOCK_MONOTONIC);
die "monotonic clock did not advance\n" unless $after > $before;
print "PASS Time::HiRes monotonic clock and resolution\n";
