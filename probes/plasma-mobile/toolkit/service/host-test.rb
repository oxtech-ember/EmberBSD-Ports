#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Actual service, controlled hosts.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'optparse'
require 'pathname'
require 'shellwords'

abort 'Use Ruby 4 or newer' if RUBY_VERSION.to_i < 4
options = { perl: '/usr/bin/perl', rc_shell: '/bin/sh' }
OptionParser.new do |p|
  p.banner = 'Usage: host-test.rb --rc-subr PATH --work NEW_DIRECTORY [--perl PATH] [--rc-shell PATH]'
  p.on('--rc-shell PATH') { |v| options[:rc_shell] = File.realpath(v) }
  p.on('--rc-subr PATH') { |v| options[:rc_subr] = File.realpath(v) }
  p.on('--work PATH') { |v| options[:work] = File.expand_path(v) }
  p.on('--perl PATH') { |v| options[:perl] = File.expand_path(v) }
end.parse!
abort 'Select a new work directory with an existing parent' unless ARGV.empty? &&
  options[:work] && !File.exist?(options[:work]) && File.directory?(File.dirname(options[:work]))
abort 'Provide the actual EmberBSD rc.subr with --rc-subr PATH' unless options[:rc_subr] && File.file?(options[:rc_subr])
work = options[:work]
Dir.mkdir(work, 0700)
source = File.realpath(__dir__)
ports = File.expand_path('../../../..', source)
production = File.read(source + '/plasma-service.pl')
pins = %w[plasma-service.pl ember_plasma.rc host-test.rb].to_h do |name|
  [name, Digest::SHA256.file(source + '/' + name).hexdigest]
end
rows = []
models = []
check = ->(value, reason) { raise reason unless value }
# One deadline covers the leader and both readers. Never wait indefinitely on
# an inherited output pipe. Only this newly created command group is killed.
capture = lambda do |argv, env = {}|
  out = ''; err = ''; status = nil
  Open3.popen3(env, *argv, chdir: work, pgroup: true) do |input, output, error, waiter|
    input.close
    readers = [Thread.new { output.read }, Thread.new { error.read }]
    deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + 40
    begin
      until !waiter.alive? && readers.none?(&:alive?)
        raise 'Host command deadline' if Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline
        sleep 0.02
      end
      out, err = readers.map(&:value)
      status = waiter.value
    ensure
      if waiter.alive? || readers.any?(&:alive?)
        Process.kill('KILL', -waiter.pid) rescue Errno::ESRCH
        waiter.join
        [output, error].each { |io| io.close rescue IOError }
        readers.each { |reader| reader.join(2); reader.kill if reader.alive? }
      end
    end
  end
  [out, err, status]
end
call = lambda do |name, argv, expected = 0, env = {}|
  out, err, status = capture.call(argv, env)
  File.binwrite(work + '/' + name + '.stdout', out)
  File.binwrite(work + '/' + name + '.stderr', err)
  rows << { name: name, argv: argv, exit: status.exitstatus, signal: status.termsig,
            stdout_sha256: Digest::SHA256.hexdigest(out), stderr_sha256: Digest::SHA256.hexdigest(err) }
  good = status.exited? && (expected == :failure ? status.exitstatus.positive? : status.exitstatus == expected)
  check.call(good, "#{name}: expected #{expected}, got #{status.inspect}: #{err}")
  [out, err]
end
perlquote = ->(v) { "'" + v.gsub('\\') { '\\\\' }.gsub("'") { "\\'" } + "'" }
executable = ->(path, text) { File.write(path, text); File.chmod(0700, path) }
wait_for = lambda do |reason, &predicate|
  deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + 12
  until predicate.call
    raise 'Deadline: ' + reason if Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline
    sleep 0.05
  end
end
model = lambda do |name, mode: 'normal', visibility: 'marked', mutate: nil|
  directory = work + '/' + name
  Dir.mkdir(directory, 0700)
  state = directory + '/state'; Dir.mkdir(state, 0700)
  home = directory + '/home space'; Dir.mkdir(home, 0700)
  File.write(state + '/mode', mode)
  File.write(state + '/visibility', visibility)
  ps = directory + '/ps'
  executable.call(ps, '#!' + options[:perl] + "\n" + <<~'PERL')
    use strict;use warnings;use FindBin qw($Bin);use JSON::PP qw(decode_json);
    sub slurp {open(my $f,'<',$_[0]) or die "$!\n";local $/;return <$f>;}
    sub output {open(my $p,'-|','/bin/ps',@_) or die "$!\n";local $/;my $o=<$p>;close($p);return $o // '';}
    my $state="$Bin/state";my @args=@ARGV;
    if (!grep {$_ eq '-p'} @args) {
        my $out=output(@args);
        # This explicit model inventories only its own controlled processes.
        # Native marker visibility and inventory scale remain target gates.
        print join('',grep {index($_,$Bin)>=0} split(/(?<=\n)/,$out));exit 0;
    }
    my $pid;for(my $i=0;$i<@args;$i++) {$pid=$args[$i+1] if $args[$i] eq '-p';}
    my $out=output(grep {$_ ne '-E' && $_ ne '-e'} @args);
    eval {
        my $r=decode_json(slurp("$state/instance"));
        my $parent=output('-p',$pid,'-o','ppid=');$parent=~s/\s+//g;
        my $owned=$parent eq "$r->{pid}" && (index($out,'sysread(STDIN')>=0 || index($out,"$Bin/entry")>=0);
        for my $name ('entry.pid','detached.pid') {
            if (-e "$state/$name") {my $value=slurp("$state/$name");$value=~s/\s+//g;$owned=1 if $value eq $pid;}
        }
        my $visibility=slurp("$state/visibility");
        if ($owned && $visibility eq 'marked') {$out=~s/\s+$//;$out.=' EMBER_PLASMA_SESSION_MARKER='.$r->{generation}."\n";}
        if ($owned && $visibility eq 'wrong-uid') {my $uid=$<+1;$out=~s/^(\s*\d+\s+)\d+/$1$uid/;}
    };
    print $out;
  PERL
  entry = directory + '/entry'
  executable.call(entry, '#!' + options[:perl] + "\n" + <<~'PERL')
    use strict;use warnings;use FindBin qw($Bin);use JSON::PP qw(encode_json);
    use POSIX qw(setsid);use Time::HiRes qw(sleep);
    my $state="$Bin/state";
    sub write_file {open(my $f,'>',$_[0]) or die "$!\n";print $f $_[1];close($f) or die "$!\n";}
    write_file("$state/entry.pid",$$);
    my @keys=qw(HOME USER LOGNAME SHELL DISPLAY WAYLAND_DISPLAY LD_PRELOAD LD_LIBRARY_PATH KWIN_DRM_DEVICES KDE_FULL_SESSION QT_QPA_PLATFORMTHEME GALLIUM_DRIVER KWIN_COMPOSE XDG_RUNTIME_DIR XDG_SESSION_TYPE XDG_CURRENT_DESKTOP QSG_RHI_BACKEND);
    write_file("$state/environment.json",encode_json({map {$_=>$ENV{$_}} @keys}));
    open(my $f,'<',"$state/mode") or die "$!\n";my $mode=<$f>;close($f);
    exit 7 if $mode eq 'exit7';exit 0 if $mode eq 'exit0';
    if ($mode eq 'detached') {
        my $child=fork();defined($child) or die "$!\n";
        if (!$child) {
            setsid()>=0 or die "$!\n";write_file("$state/detached.pid",$$);
            $SIG{TERM}=sub {write_file("$state/detached.terminated",'yes');exit 0;};
            sleep 60;exit 0;
        }
    }
    $SIG{TERM}='IGNORE' if $mode eq 'ignore-term';
    while (1) {sleep 0.1;}
  PERL
  bus = directory + '/bus'
  executable.call(bus, '#!' + options[:perl] + "\n" + <<~'PERL')
    use strict;use warnings;use FindBin qw($Bin);use JSON::PP qw(encode_json);
    open(my $f,'>',"$Bin/state/bus-arguments.json") or die "$!\n";print $f encode_json(\@ARGV);close($f);
    @ARGV==2 && $ARGV[0] eq '--' && $ARGV[1] eq "$Bin/entry" or exit 99;
    exec "$Bin/entry";die "exec: $!\n";
  PERL
  replacements = {
    'my @account=getpwuid($<);' => 'my @account=("fixture", "", $<, $(, "", "", "", ' + perlquote.call(home) + ', "/bin/sh");',
    "my $state='/var/run/ember-plasma/'.$<;" => 'my $state=' + perlquote.call(state) + ';',
    "'/bin/ps'" => perlquote.call(ps),
    "'/usr/pkg/bin/dbus-run-session'" => perlquote.call(bus),
    "'/usr/pkg/bin/startplasma-wayland'" => perlquote.call(entry)
  }
  text = production.dup
  replacements.each do |old, replacement|
    check.call(text.include?(old), 'Actual service model boundary changed: ' + old)
    text = text.gsub(old) { replacement }
  end
  if mutate
    old, replacement = mutate
    check.call(text.scan(Regexp.new(Regexp.escape(old))).length == 1, 'Mutation boundary changed')
    text = text.sub(old) { replacement }
  end
  script = directory + '/service.pl'; File.write(script, text)
  File.write(directory + '/replacements.json', JSON.pretty_generate(replacements) + "\n")
  row = { directory: directory, state: state, home: home, script: script }
  models << row
  row
end
invoke = lambda do |name, item, action, expected = 0|
  env = { 'HOME'=>'/untrusted', 'DISPLAY'=>':untrusted', 'WAYLAND_DISPLAY'=>'untrusted',
          'LD_LIBRARY_PATH'=>'/untrusted', 'KWIN_DRM_DEVICES'=>'/untrusted',
          'KDE_FULL_SESSION'=>'untrusted', 'GALLIUM_DRIVER'=>'softpipe', 'QSG_RHI_BACKEND'=>'software' }
  call.call(name, [options[:perl], item[:script], action], expected, env)
end
failure = nil
begin
  call.call('production-perl-syntax', [options[:perl], '-c', source + '/plasma-service.pl'])
  call.call('rc-shell-syntax', ['/bin/sh', '-n', source + '/ember_plasma.rc'])
  _, err = call.call('unknown-action', [options[:perl], source + '/plasma-service.pl', 'restart'], :failure)
  check.call(err.include?('Usage:'), 'Unknown action refusal changed')
  item = model.call('missing-state')
  saved = item[:directory] + '/saved-state'; File.rename(item[:state], saved)
  invoke.call('missing-state-status', item, 'status', 3); invoke.call('missing-state-stop', item, 'stop')
  check.call(!File.exist?(item[:state]), 'Status or stop created missing state')
  File.rename(saved, item[:state])
  item = model.call('read-only-metadata')
  File.open(item[:state] + '/lock', File::WRONLY|File::CREAT, 0600) do |locked|
    locked.flock(File::LOCK_EX|File::LOCK_NB)
    _, err = invoke.call('missing-instance-status', item, 'status', :failure)
    check.call(err.include?('open ') && !File.exist?(item[:state] + '/instance'), 'Read-only status created missing instance')
  end
  item = model.call('abandoned-ack', mutate: [
    'my @ready=IO::Select->new($ack_read)->can_read(30);',
    'my @ready;close($ack_read);die "Controlled closed acknowledgement\n";'])
  _, err = invoke.call('abandoned-ack-start', item, 'start', :failure)
  check.call(err.include?('Controlled closed acknowledgement'), 'Startup parent-loss injection changed')
  wait_for.call('abandoned acknowledgement cleanup') { File.exist?(item[:state] + '/session.status') }
  check.call(File.read(item[:state] + '/session.status').strip == '1', 'Lost caller bypassed cleanup')
  invoke.call('abandoned-ack-stopped', item, 'status', 3)
  item = model.call('normal')
  invoke.call('initial-status', item, 'status', 3); invoke.call('initial-stop', item, 'stop')
  invoke.call('start', item, 'start')
  wait_for.call('entry environment') { File.exist?(item[:state] + '/environment.json') }
  invoke.call('running-status', item, 'status')
  _, err = invoke.call('duplicate-start', item, 'start', :failure)
  check.call(err.include?('already running'), 'Duplicate-start cause changed')
  env = JSON.parse(File.read(item[:state] + '/environment.json'))
  check.call(env['HOME'] == item[:home] && env['USER'] == 'fixture', 'Passwd HOME/account lost')
  %w[DISPLAY WAYLAND_DISPLAY LD_PRELOAD LD_LIBRARY_PATH KWIN_DRM_DEVICES KDE_FULL_SESSION QT_QPA_PLATFORMTHEME GALLIUM_DRIVER KWIN_COMPOSE QSG_RHI_BACKEND].each do |key|
    check.call(env[key].nil?, 'Inherited override ' + key)
  end
  check.call(env['XDG_SESSION_TYPE'] == 'wayland' && env['XDG_CURRENT_DESKTOP'] == 'KDE', 'Standard session metadata lost')
  check.call((File.stat(item[:state] + '/runtime').mode & 07777) == 0700, 'Runtime is not private')
  instance = File.read(item[:state] + '/instance'); item[:backup] = instance
  stale = item[:state] + '/stop-' + '0'*32; Dir.mkdir(stale, 0700)
  sleep 0.7; invoke.call('stale-generation-status', item, 'status'); Dir.rmdir(stale)
  foreign = JSON.parse(instance); foreign['pid'] = Process.pid
  File.write(item[:state] + '/instance', JSON.generate(foreign))
  _, err = invoke.call('foreign-pid-stop', item, 'stop', :failure)
  check.call(err.include?('Supervisor identity is not current'), 'Foreign-PID refusal cause changed')
  File.write(item[:state] + '/instance', instance)
  invoke.call('normal-stop', item, 'stop'); invoke.call('normal-stopped-status', item, 'status', 3)
  check.call(File.read(item[:state] + '/session.status').strip == '0', 'Managed stop lost successful cleanup')
  invoke.call('repeat-start', item, 'start')
  wait_for.call('repeated entry') { File.exist?(item[:state] + '/entry.pid') }
  item[:backup] = File.read(item[:state] + '/instance'); invoke.call('repeat-stop', item, 'stop')
  [['exit0',0], ['exit7',7], ['detached',0], ['ignore-term',1]].each do |mode, status|
    item = model.call(mode, mode: mode); invoke.call(mode + '-start', item, 'start')
    wait_for.call(mode + ' entry') { File.exist?(item[:state] + '/entry.pid') }
    item[:backup] = File.read(item[:state] + '/instance')
    if %w[exit0 exit7].include?(mode)
      wait_for.call(mode + ' completion') { File.exist?(item[:state] + '/session.status') }
      invoke.call(mode + '-stopped', item, 'status', 3)
    else
      wait_for.call('detached child') { File.exist?(item[:state] + '/detached.pid') } if mode == 'detached'
      _, err = invoke.call(mode + '-stop', item, 'stop', status.zero? ? 0 : :failure)
      check.call(err.include?('cleanup failed'), 'Forced cleanup was not reported') unless status.zero?
    end
    check.call(File.read(item[:state] + '/session.status').strip == status.to_s, mode + ' status mismatch')
    check.call(File.exist?(item[:state] + '/detached.terminated'), 'Detached child was not stopped') if mode == 'detached'
    generation = JSON.parse(item[:backup])['generation']
    [item[:state] + '/processes.tsv', item[:home] + '/.local/state/ember-plasma/session.log'].each do |log|
      check.call(!File.read(log).include?(generation), 'Private generation leaked to logs')
    end
  end
  %w[hidden wrong-uid].each do |visibility|
    item = model.call(visibility, visibility: visibility)
    _, err = invoke.call(visibility + '-start', item, 'start', :failure)
    check.call(err.include?('startup failed'), 'Ownership refusal cause changed')
    check.call(!File.exist?(item[:state] + '/entry.pid'), 'Unverified entry launched')
  end
  item = model.call('unsafe-runtime'); File.symlink(item[:home], item[:state] + '/runtime')
  _, err = invoke.call('symlink-runtime-refusal', item, 'start', :failure)
  check.call(err.include?('Unsafe directory'), 'Symlink refusal cause changed')
  item = model.call('unsafe-lock'); File.symlink(item[:home] + '/not-created', item[:state] + '/lock')
  _, err = invoke.call('symlink-lock-refusal', item, 'start', :failure)
  check.call(err.include?('open ') && !File.exist?(item[:home] + '/not-created'), 'Lock symlink target was written')
  # The exact marker predicate must distinguish a hidden child from an owned one.
  item = model.call('mutant-marker', mode: 'exit0', visibility: 'hidden', mutate: [
    'next unless $command =~ /(?:^|\s)\Q$needle\E(?:\s|$)/;', 'next if 0;'])
  invoke.call('mutant-marker-start', item, 'start')
  wait_for.call('marker mutant entry') { File.exist?(item[:state] + '/entry.pid') }
  item[:backup] = File.read(item[:state] + '/instance')
  wait_for.call('marker mutant completion') { File.exist?(item[:state] + '/session.status') }
  invoke.call('mutant-marker-stopped', item, 'status', 3)
  rc = File.read(source + '/ember_plasma.rc')
  account = 'ember_plasma_account()' + "\n" + rc.split("ember_plasma_account()\n",2).fetch(1).split("ember_plasma_dispatch()\n",2).first
  fake_id = work + '/id'
  executable.call(fake_id, "#!/bin/sh\ncase \"$2\" in root) echo 0 ;; ordinary) echo 1000 ;; *) exit 1 ;; esac\n")
  account = account.gsub('/usr/bin/id', fake_id)
  [['ordinary',0],['root',1],['',1],['ordinary;false',1],['--root',1]].each do |user, status|
    name = 'rc-account-' + rows.length.to_s; script = work + '/' + name + '.sh'
    File.write(script, "#!/bin/sh\nset -eu\nember_plasma_user='#{user}'\n" + account + "ember_plasma_account\n")
    call.call(name, ['/bin/sh', script], status)
  end
  # Execute the complete actual rc.subr and actual service command dispatch.
  # Only configuration input and privileged leaf commands are controlled.
  fake_su = work + '/su'
  executable.call(fake_su, <<~'SH')
    #!/bin/sh
    [ "$#" -eq 4 ] && [ "$1" = '-m' ] && [ "$2" = 'ordinary' ] && [ "$3" = '-c' ] || exit 98
    [ "$4" = 'exec /usr/bin/env -i PATH=/usr/pkg/bin:/usr/bin:/bin /usr/pkg/bin/perl /usr/pkg/libexec/ember-plasma-service status' ] || exit 99
    echo controlled-status-reached
  SH
  dispatch = rc.dup
  substitutions = {
    '. /etc/rc.subr' => '. ' + Shellwords.escape(options[:rc_subr]),
    'load_rc_config "$name"' => "ember_plasma=YES\nember_plasma_user=ordinary",
    '/usr/bin/id' => Shellwords.escape(fake_id),
    '/usr/bin/su' => Shellwords.escape(fake_su)
  }
  substitutions.each do |old, replacement|
    check.call(dispatch.include?(old), 'RC dispatch boundary changed: ' + old)
    dispatch = dispatch.gsub(old) { replacement }
  end
  File.write(work + '/rc-dispatch-replacements.json', JSON.pretty_generate(substitutions) + "\n")
  script = work + '/rc-dispatch.sh'; File.write(script, dispatch)
  out, err = call.call('rc-dispatch-status', [options[:rc_shell], script, 'status'])
  check.call(out == "controlled-status-reached\n" && !err.include?('unknown directive'), 'Actual rc.subr did not dispatch status')
  declaration = "extra_commands=\"status\"\n"
  check.call(dispatch.scan(Regexp.new(Regexp.escape(declaration))).length == 1, 'Extra status declaration changed')
  script = work + '/rc-dispatch-missing-status.sh'; File.write(script, dispatch.sub(declaration, ''))
  out, err = call.call('rc-dispatch-missing-status', [options[:rc_shell], script, 'status'], 1)
  check.call(err.include?("unknown directive 'status'") && !out.include?('controlled-status-reached'), 'Missing extra command did not reproduce the real status failure')
  check.call(rc.include?('# REQUIRE: DAEMON LOGIN dbus x11_runtime') && !rc.include?('# BEFORE: LOGIN'), 'Desktop starts before LOGIN')
  check.call(rc.include?('exec /usr/bin/env -i PATH=/usr/pkg/bin:/usr/bin:/bin /usr/pkg/bin/perl'), 'Interpreter inherits caller environment')
  check.call(!rc.include?('command_background') && !production.include?('KWIN_DRM_DEVICES') &&
    !production.include?('KDE_FULL_SESSION') && !production.include?('--virtual'), 'Backend, theme or seat workaround added')
  original, err, status = capture.call(['git','-C',ports,'show','f9737bd0:probes/plasma-mobile/toolkit/tests/plasma-session/guard.pl'])
  check.call(status.success? && original == File.binread(source + '/../tests/plasma-session/guard.pl'), 'Bounded test guard changed: ' + err)
rescue Exception => error
  failure = error.message
  raise
ensure
  models.each do |item|
    File.write(item[:state] + '/instance', item[:backup]) if item[:backup]
    capture.call([options[:perl], item[:script], 'stop'])
  rescue StandardError => error
    warn 'Fixture final cleanup: ' + error.message
  end
  File.write(work + '/receipt.json', JSON.pretty_generate({
    status: failure ? 'FAIL' : 'PASS', failure: failure, source_sha256: pins, commands: rows,
    rc_subr: { path: options[:rc_subr], sha256: Digest::SHA256.file(options[:rc_subr]).hexdigest },
    rc_shell: { path: options[:rc_shell], sha256: Digest::SHA256.file(options[:rc_shell]).hexdigest },
    limits: 'Explicit host passwd/ps/Perl command doubles; no KDE, DRM or native marker-visibility claim.'
  }) + "\n")
end
puts "PASS: #{rows.length} actual service host commands"
