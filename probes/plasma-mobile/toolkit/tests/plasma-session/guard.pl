#!/usr/bin/env perl
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Bound and clean one marked private session.
use strict;
use warnings;
use POSIX qw(setsid WNOHANG);
use Time::HiRes qw(clock_gettime CLOCK_MONOTONIC sleep);
@ARGV >= 4 or die "Usage: guard.pl OUTPUT SECONDS -- COMMAND [ARG...]\n";
my ($output, $seconds, $separator) = splice @ARGV, 0, 3;
$separator eq '--' && $seconds =~ /^\d+$/ && $seconds > 0 && $seconds <= 300
    or die "Invalid guard arguments\n";
$< != 0 or die "Run as an ordinary user\n";
-d $output && !-e "$output/guard.status" or die "Invalid guard output\n";
open my $random, '<', '/dev/urandom' or die "urandom: $!\n";
read($random, my $bytes, 16) == 16 or die "short random read\n";
close $random;
my $needle = 'EMBER_PLASMA_SESSION_MARKER=' . unpack('H*', $bytes);
my (%seen, %baseline);
open my $log, '>', "$output/processes.tsv" or die "$!\n";
$log->autoflush(1);
my $deadline = clock_gettime(CLOCK_MONOTONIC) + $seconds;
sub inventory {
    my ($environment, @selection) = @_;
    clock_gettime(CLOCK_MONOTONIC) < $deadline or die "Process inventory deadline\n";
    local $ENV{LC_ALL} = 'C';
    my @flags = $environment ? ('-ww', ($^O eq 'darwin' ? '-E' : '-e')) : ('-ax');
    my $ps_pid = open my $ps, '-|', '/bin/ps', @flags, @selection,
        '-o', 'pid=', '-o', 'uid=', '-o', 'lstart=', '-o', 'state=', '-o', 'command=';
    defined $ps_pid or die "ps: $!\n";
    my %processes;
    my $closed = 0;
    my $error;
    {
        # ps has no children. A failed or blocked inventory cannot bypass the
        # outer session cleanup or leave a blocked pipe reader behind.
        local $SIG{ALRM} = sub { die "Process inventory timed out\n" };
        eval {
            alarm 2;
            while (my $line = <$ps>) {
                next unless $line =~ /^\s*(\d+)\s+(\d+)\s+(\S+\s+\S+\s+\d+\s+\S+\s+\d+)\s+(\S+)\s+(.*)$/;
                my ($pid, $uid, $birth, $state, $command) = ($1, $2, $3, $4, $5);
                next unless $uid == $< && $state !~ /^Z/;
                $processes{$pid} = ["$uid\t$birth", $command];
            }
            close $ps;
            my $status = $?;
            $closed = 1;
            # A selected process can exit between the two reads.
            die "ps failed (status $status)\n" if $status && !($environment && ($status >> 8) == 1);
            alarm 0;
            1;
        } or $error = $@ || "Process inventory failed\n";
        alarm 0;
    }
    unless ($closed) {
        if (waitpid($ps_pid, WNOHANG) == 0) { kill 'KILL', $ps_pid; waitpid($ps_pid, 0); }
        close $ps;
    }
    die $error if defined $error;
    return %processes;
}
sub snapshot {
    my %all = inventory(0);
    my @new = grep { !exists $baseline{$_} || $baseline{$_} ne $all{$_}[0] } keys %all;
    my %owned;
    # Read environments only for new processes owned by this user. Keep
    # non-matching data in memory; never log another process environment.
    # EmberBSD ps accepts one PID per -p, not a comma-separated PID list.
    for my $candidate (@new) {
        my %entry = inventory(1, '-p', $candidate);
        next unless exists $entry{$candidate};
        my ($identity, $command) = @{$entry{$candidate}};
        next unless $command =~ /(?:^|\s)\Q$needle\E(?:\s|$)/;
        $owned{$candidate} = $identity;
        print $log "$candidate\t$identity\n" unless $seen{"$candidate\t$identity"}++;
    }
    return %owned;
}
# Refuse to launch if the initial process inventory cannot be read.
my %initial = inventory(0);
%baseline = map { $_ => $initial{$_}[0] } keys %initial;
my $interrupted = 0;
$SIG{INT} = sub { $interrupted = 130 };
$SIG{TERM} = sub { $interrupted = 143 };
$SIG{HUP} = sub { $interrupted = 129 };
pipe my $gate_read, my $gate_write or die "pipe: $!\n";
my $pid = fork();
defined $pid or die "fork: $!\n";
if (!$pid) {
    close $gate_write;
    setsid() >= 0 or die "setsid: $!\n";
    $ENV{EMBER_PLASMA_SESSION_MARKER} = substr $needle, length 'EMBER_PLASMA_SESSION_MARKER=';
    open STDIN, '<&', $gate_read or die "stdin: $!\n";
    close $gate_read;
    # Wait after exec so ps sees the marker before any session program starts.
    exec $^X, '-e', 'sysread(STDIN, my $b, 1) == 1 or exit 1; open STDIN, "<", "/dev/null" or die "stdin: $!\n"; exec @ARGV; die "exec: $!\n"', '--', @ARGV;
    die "exec: $!\n";
}
close $gate_read;
my $alive = 1;
my $result;
sub poll_child {
    return 0 unless $alive;
    if (waitpid($pid, WNOHANG) == $pid) {
        my $status = $?;
        $alive = 0;
        $result = ($status & 127) ? 128 + ($status & 127) : $status >> 8 unless defined $result;
    }
    return $alive;
}
my $error;
eval {
    my $handshake_end = clock_gettime(CLOCK_MONOTONIC) + 5;
    while (1) {
        my %owned = snapshot();
        last if exists $owned{$pid};
        poll_child() && clock_gettime(CLOCK_MONOTONIC) < $handshake_end
            or die "Cannot verify private process ownership; session was not started\n";
        sleep 0.05;
    }
    {
        local $SIG{PIPE} = 'IGNORE';
        print $gate_write '1' or die "Session gate write: $!\n";
        close $gate_write or die "Session gate close: $!\n";
    }
    while (poll_child()) {
        if ($interrupted || clock_gettime(CLOCK_MONOTONIC) >= $deadline) {
            $result = $interrupted || 124;
            last;
        }
        snapshot();
        sleep 0.5;
    }
    1;
} or $error = $@ || "Session supervisor failed\n";
close $gate_write if defined fileno $gate_write;
if (defined $error) {
    print STDERR "FAIL: $error";
    $result = clock_gettime(CLOCK_MONOTONIC) >= $deadline ? 124 : 1;
}
# Final cleanup always runs, including after inventory failures. A live,
# unreaped child pins its private group ID. Never signal a group after reaping
# its leader. Detached children require a fresh marker/uid/birth-time check.
sub signal_owned {
    my ($signal) = @_;
    my %before = snapshot();
    my %current = snapshot();
    for my $target (keys %before) {
        next unless exists $current{$target} && $current{$target} eq $before{$target};
        kill $signal, $target;
    }
}
sub known_group {
    my ($signal) = @_;
    return unless $alive;
    kill $signal, -$pid;
    kill $signal, $pid;
}
$deadline = clock_gettime(CLOCK_MONOTONIC) + 12;
my $cleanup_error;
eval {
    known_group('TERM');
    signal_owned('TERM');
    my $term_end = clock_gettime(CLOCK_MONOTONIC) + 6;
    while (1) {
        my %remaining = snapshot();
        last unless poll_child() || keys %remaining;
        if (clock_gettime(CLOCK_MONOTONIC) >= $term_end) {
            print STDERR "FAIL: private session required SIGKILL\n";
            $result ||= 1;
            known_group('KILL');
            signal_owned('KILL');
            sleep 0.2;
            last;
        }
        sleep 0.2;
    }
    my %remaining = snapshot();
    die "Marked private processes remain\n" if poll_child() || keys %remaining;
    1;
} or $cleanup_error = $@ || "Session cleanup failed\n";
if (defined $cleanup_error) {
    print STDERR "FAIL: cleanup: $cleanup_error";
    $result ||= 1;
    # Even a broken ps cannot strand the direct child and its private group.
    # Do not guess ownership of detached processes when inventory is broken.
    known_group('KILL');
}
my $reap_end = clock_gettime(CLOCK_MONOTONIC) + 2;
while (poll_child() && clock_gettime(CLOCK_MONOTONIC) < $reap_end) { sleep 0.05; }
if ($alive) { print STDERR "FAIL: direct child did not exit after cleanup\n"; $result ||= 1; }
open my $status, '>', "$output/guard.status" or die "$!\n";
print $status "$result\n";
close $status;
exit $result;
