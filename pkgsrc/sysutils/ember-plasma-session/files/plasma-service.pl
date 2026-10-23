#!/usr/pkg/bin/perl
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Derived from the Plasma session guard.
# Manage one opted-in ordinary-user session. Do not trust a PID for signals.
use strict;
use warnings;
use POSIX qw(setsid WNOHANG);
use Time::HiRes qw(clock_gettime CLOCK_MONOTONIC sleep);
use Fcntl qw(:DEFAULT :flock :mode);
use IO::Select;
use JSON::PP qw(encode_json decode_json);
use Cwd qw(abs_path);
use Errno qw(EWOULDBLOCK EAGAIN EEXIST);
@ARGV == 1 && $ARGV[0] =~ /^(start|stop|status)$/ or die "Usage: plasma-service.pl start|stop|status\n";
my $action=$ARGV[0];
$< != 0 && $< == $> or die "Run as the configured ordinary user\n";
my @account=getpwuid($<);
@account && $account[7] =~ m{^/} && $account[8] =~ m{^/} && -x $account[8]
    or die "Invalid account HOME or shell\n";
my ($user,$home,$shell)=@account[0,7,8];
my $state='/var/run/ember-plasma/'.$<;
my $runtime="$state/runtime";
my ($deadline,$needle,$log);
my (%seen,%baseline);
sub directory {
    my ($path,$private,$create)=@_;
    mkdir($path,0700) or die "mkdir $path: $!\n" if $create && !-e $path && !-l $path;
    my @s=lstat($path);
    @s && S_ISDIR($s[2]) && $s[4]==$< && ($s[2]&0022)==0 &&
        (!$private || ($s[2]&07777)==0700) or die "Unsafe directory: $path\n";
}
sub file {
    my ($path,$truncate,$readonly)=@_;
    sysopen(my $fh,$path,($readonly ? O_RDONLY : O_RDWR|O_CREAT)|O_NOFOLLOW,0600) or die "open $path: $!\n";
    my @s=stat($fh);
    @s && S_ISREG($s[2]) && $s[3]==1 && $s[4]==$< && ($s[2]&07777)==0600
        or die "Unsafe private file: $path\n";
    truncate($fh,0) or die "truncate $path: $!\n" if $truncate;
    return $fh;
}
sub record {
    my ($name,$value)=@_;
    my $fh=file("$state/$name",1);
    print $fh $value or die "write $name: $!\n";
    close($fh) or die "close $name: $!\n";
}
sub instance {
    my $fh=file("$state/instance",0,1);
    my $text='';read($fh,$text,1025);close($fh);
    length($text)<=1024 or die "Oversized instance record\n";
    my $r=decode_json($text);
    ref($r) eq 'HASH' && $r->{pid}=~/^\d+$/ && $r->{pid}>1 &&
        $r->{generation}=~/^[0-9a-f]{32}$/ && $r->{identity}=~/^\d+\t[^\n]+$/
        or die "Invalid instance record\n";
    return $r;
}
sub inventory {
    my ($environment, @selection) = @_;
    (!defined($deadline) || clock_gettime(CLOCK_MONOTONIC) < $deadline) or die "Process inventory deadline\n";
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
        print $log "$candidate\t$identity\n" if defined($log) && !$seen{"$candidate\t$identity"}++;
    }
    return %owned;
}
directory($home,0,0);
if ($action ne 'start' && !-e $state && !-l $state) {
    print "Plasma service is stopped\n";exit($action eq 'status' ? 3 : 0);
}
directory($state,1,0);
umask 077;
my $lock=file("$state/lock",0);
sub held {
    return 0 if flock($lock,LOCK_EX|LOCK_NB);
    ($! == EWOULDBLOCK || $! == EAGAIN) or die "lock query: $!\n";
    return 1;
}
sub supervisor {
    my $r=instance();
    my %current=inventory(0);
    exists($current{$r->{pid}}) && $current{$r->{pid}}[0] eq $r->{identity} &&
        index($current{$r->{pid}}[1],abs_path($0))>=0
        or die "Supervisor identity is not current\n";
    return $r;
}
if ($action eq 'status') {
    if (!held()) { print "Plasma service is stopped\n";exit 3; }
    my $r=supervisor();print "Plasma service supervisor PID $r->{pid}\n";exit 0;
}
if ($action eq 'stop') {
    if (!held()) { print "Plasma service is stopped\n";exit 0; }
    my $r=supervisor();
    my $request="$state/stop-$r->{generation}";
    mkdir($request,0700) or $! == EEXIST or die "stop request: $!\n";
    directory($request,1,0);
    my $end=clock_gettime(CLOCK_MONOTONIC)+20;
    while (held()) {
        clock_gettime(CLOCK_MONOTONIC)<$end or die "Plasma stop deadline; supervisor was not signalled by PID\n";
        sleep 0.1;
    }
    my $fh=file("$state/session.status",0,1);
    my $status='';read($fh,$status,16);close($fh);
    defined($status) && $status=~/^\d+\n$/ && $status==0 or die "Plasma cleanup failed\n";
    print "Plasma service stopped\n";exit 0;
}
flock($lock,LOCK_EX|LOCK_NB) or die "Plasma service is already running\n";
$deadline=clock_gettime(CLOCK_MONOTONIC)+10;
# A stale record is never an executable or signal target. Refuse old marked
# children instead of adopting or terminating a previous uncertain session.
if (-e "$state/instance" || -l "$state/instance") {
    my $r=instance();$needle='EMBER_PLASMA_SESSION_MARKER='.$r->{generation};
    my %prior=snapshot();keys(%prior)==0 or die "Prior marked session remains; inspect it before starting\n";
}
directory($runtime,1,1);
my $logs=$home;
for my $part ('.local','state','ember-plasma') {$logs.='/'.$part;directory($logs,$part eq 'ember-plasma',1);}
my $session_log=file("$logs/session.log",0);seek($session_log,0,2) or die "log seek: $!\n";
for my $path ('/usr/pkg/bin/dbus-run-session','/usr/pkg/bin/startplasma-wayland') {-x $path or die "Missing executable: $path\n";}
pipe(my $ack_read,my $ack_write) or die "startup pipe: $!\n";
my $daemon=fork();defined($daemon) or die "fork: $!\n";
if ($daemon) {
    close($ack_write);close($session_log);close($lock);
    my @ready=IO::Select->new($ack_read)->can_read(30);
    my $line=@ready ? <$ack_read> : undef;close($ack_read);
    defined($line) && $line eq "started\n" or die "Plasma service startup failed; inspect the private session log\n";
    print "Plasma service started\n";exit 0;
}
close($ack_read);setsid()>=0 or die "setsid: $!\n";
open(STDIN,'<','/dev/null') or die "$!\n";
open(STDOUT,'>&',$session_log) or die "$!\n";open(STDERR,'>&',$session_log) or die "$!\n";close($session_log);
select(STDERR);$|=1;select(STDOUT);$|=1;
%ENV=(PATH=>'/usr/pkg/qt6/bin:/usr/pkg/bin:/usr/pkg/sbin:/usr/bin:/usr/sbin:/bin:/sbin',
    HOME=>$home,USER=>$user,LOGNAME=>$user,SHELL=>$shell,LC_ALL=>'C.UTF-8',
    XDG_RUNTIME_DIR=>$runtime,XDG_CONFIG_DIRS=>'/usr/pkg/etc/xdg',XDG_DATA_DIRS=>'/usr/pkg/share',
    XDG_SESSION_TYPE=>'wayland',XDG_CURRENT_DESKTOP=>'KDE');
chdir($home) or die "HOME: $!\n";
open(my $random,'<','/dev/urandom') or die "$!\n";read($random,my $bytes,16)==16 or die "random read\n";close($random);
my $generation=unpack('H*',$bytes);$needle='EMBER_PLASMA_SESSION_MARKER='.$generation;
$deadline=clock_gettime(CLOCK_MONOTONIC)+10;
my %self=inventory(0);exists($self{$$}) or die "Cannot identify supervisor\n";
record('instance',encode_json({pid=>$$,identity=>$self{$$}[0],generation=>$generation})."\n");
$log=file("$state/processes.tsv",1);$log->autoflush(1);
@ARGV=('/usr/pkg/bin/dbus-run-session','--','/usr/pkg/bin/startplasma-wayland');
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
    $deadline=undef;
    {
        local $SIG{PIPE} = 'IGNORE';
        print $ack_write "started\n" or die "startup acknowledgement: $!\n";
        close($ack_write) or die "startup acknowledgement close: $!\n";
    }
    while (poll_child()) {
        my $requested=0;
        if (-e "$state/stop-$generation" || -l "$state/stop-$generation") {
            directory("$state/stop-$generation",1,0);
            $requested=1;
        }
        if ($interrupted || $requested) {$result=0;last;}
        sleep 0.5;
    }
    1;
} or $error = $@ || "Session supervisor failed\n";
close $gate_write if defined fileno $gate_write;
if (defined $error) {
    print STDERR "FAIL: $error";
    $result = 1;
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
rmdir("$state/stop-$generation") if -d "$state/stop-$generation" && !-l "$state/stop-$generation";
record('session.status',"$result\n");
print STDERR "Plasma service exited status=$result\n";
exit $result;
