#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), pinned registration privilege regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
require 'tmpdir'
require 'rexml/document'

abort 'Usage: privilege.rb VERIFIED_ARCHIVE NEW_RECEIPT_DIR' unless ARGV.length == 2
archive, receipt = ARGV.map { |p| File.expand_path(p) }
abort 'Receipt path already exists' if File.exist?(receipt)
abort 'Run the host policy fixture as an ordinary user' if Process.euid.zero?
abort 'ConsoleKit archive SHA256 mismatch' unless Digest::SHA256.file(archive).hexdigest ==
  'f3f4a424f2a4fbb67696b4011caf2fd4c02e5e67c24ef1c86cecb2301bccdba4'
%w[CC SANITIZER_CC PKG_CONFIG CPPCHECK DIGEST].each { |key| abort "Set #{key}" if ENV[key].to_s.empty? }
tests = File.expand_path(__dir__)
toolkit = File.expand_path('../..', tests)
root = File.expand_path('../../..', toolkit)
relative = 'probes/plasma-mobile/toolkit/recipes/sysutils/consolekit'
recipe = File.join(root, relative)
baseline = 'a7b358eceafd02440b3c0dbcc09eeb61bdcbf009'
FileUtils.mkdir_p(receipt)
verifier = File.join(root, 'upstream/pkgsrc/mk/checksum/checksum.awk')

def run(args, log, chdir: nil, env: {})
  output, status = Open3.capture2e(env, *args, **(chdir ? { chdir: chdir } : {}))
  File.write(log, "$ #{args.shelljoin}\n#{output}")
  abort 'Sanitizer diagnostic' if output.match?(/AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:/)
  [output, status]
end
def run!(args, log, **options)
  output, status = run(args, log, **options)
  abort "Failed: #{args.first}; see #{log}" unless status.success?
  output
end
def function(source, name)
  match = source.match(/^#{Regexp.escape(name)}\s*\(.*?^\}\n/m)
  abort "Cannot extract #{name}" unless match
  source[0...match.begin(0)].lines.last + match[0]
end
def policy_test(executable, config, log)
  reader, writer = IO.pipe
  daemon_error = File.open(log + '.dbus', 'w')
  command = [ENV.fetch('DBUS_DAEMON', 'dbus-daemon'), '--nofork', "--config-file=#{config}", '--print-address=1']
  daemon_error.puts "$ #{command.shelljoin}"; daemon_error.flush
  pid = Process.spawn(*command, out: writer, err: daemon_error)
  writer.close
  address = reader.gets&.strip
  abort 'Private policy bus failed' if address.to_s.empty?
  run([executable], log, env: { 'CK_TEST_BUS_ADDRESS' => address })
ensure
  if pid
    begin
      Process.kill('TERM', pid)
    rescue Errno::ESRCH
      # This owned daemon has already stopped.
    end
    Process.wait(pid)
  end
  reader&.close; writer&.close unless writer&.closed?
  daemon_error&.close
end
def launcher_cases(executable, tree, log)
  child = File.join(tree, 'child.sh')
  sentinel = File.join(tree, 'child-ran')
  File.write(child, <<~'SH')
    #!/bin/sh
    printf '%s\n' child > "$CK_CHILD_SENTINEL"
    [ "$XDG_SESSION_COOKIE" = fixture-cookie ] || exit 93
    [ "$XDG_RUNTIME_DIR" = /fixture-runtime ] || exit 94
    case "${1:-shell}" in signal) kill -TERM $$ ;; ok) exit 0 ;; *) exit 42 ;; esac
  SH
  File.chmod(0o755, child)
  rows = []
  %w[null error noerror].each do |mode|
    [[], ['--service', 'test-service']].each do |service|
      [false, true].each do |shell|
        rows << [mode, service + (shell ? [] : ['--', child, 'ok']), 1, false]
      end
    end
  end
  rows.concat([['ok', ['--', child, 'ok'], 0, true], ['ok', ['--', child, 'fail'], 42, true],
               ['ok', ['--', child, 'signal'], 143, true], ['ok', [], 42, true],
               ['ok', ['--service', 'test-service', '--', child, 'fail'], 42, true],
               ['ok', ['--', File.join(tree, 'absent-command')], 1, false],
               ['ok', ['--unknown-option'], 1, false]])
  failures = 0
  output = []
  rows.each_with_index do |(mode, args, expected, executed), index|
    FileUtils.rm_f(sentinel)
    text, status = Open3.capture2e({ 'CK_REGISTRATION_MODE' => mode, 'CK_CHILD_SENTINEL' => sentinel,
                                   'SHELL' => child, 'XDG_SESSION_COOKIE' => nil, 'XDG_RUNTIME_DIR' => nil }, executable, *args)
    abort 'Launcher sanitizer diagnostic' if text.match?(/AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:/)
    good = status.exitstatus == expected && File.exist?(sentinel) == executed
    good &&= text.include?('Unable to ') unless mode == 'ok'
    failures += 1 unless good
    output << "#{good ? 'PASS' : 'FAIL'} #{index}: #{mode} #{args.shelljoin}: exit=#{status.exitstatus}, child=#{File.exist?(sentinel)}\n#{text}"
  end
  File.write(log, output.join + "#{rows.length} launcher cases, #{failures} failures\n")
  failures
end

%w[CC SANITIZER_CC CPPCHECK].each { |key| run!([ENV[key], '--version'], File.join(receipt, "#{key.downcase}-version.log")) }
run!([ENV.fetch('DBUS_DAEMON', 'dbus-daemon'), '--version'], File.join(receipt, 'dbus-version.log'))
cflags = Shellwords.split(run!([ENV['PKG_CONFIG'], '--cflags', 'gio-2.0', 'dbus-1'], File.join(receipt, 'host-cflags.log')))
libs = Shellwords.split(run!([ENV['PKG_CONFIG'], '--libs', 'gio-2.0', 'dbus-1'], File.join(receipt, 'host-libs.log')))
run!([ENV['PKG_CONFIG'], '--modversion', 'gio-2.0', 'dbus-1'], File.join(receipt, 'host-library-versions.log'))
Dir.mktmpdir('consolekit-privilege-') do |work|
  previous = File.join(work, 'previous-recipe'); FileUtils.mkdir_p(File.join(previous, 'patches'))
  info = run!(['git', '-C', root, 'show', "#{baseline}:#{relative}/distinfo"], File.join(receipt, 'baseline-distinfo.log'))
  File.write(File.join(previous, 'distinfo'), info)
  info.scan(/^SHA1 \((patch-[^)]+)\)/).flatten.each do |name|
    text = run!(['git', '-C', root, 'show', "#{baseline}:#{relative}/patches/#{name}"], File.join(receipt, "baseline-input-#{name}.log"))
    File.write(File.join(previous, 'patches', name), text)
  end
  findings = {}
  %w[baseline candidate].each do |mode|
    tree = File.join(work, mode); FileUtils.mkdir(tree)
    pkg = mode == 'baseline' ? previous : recipe
    run!(['awk', '-f', verifier, '--', File.join(pkg, 'distinfo'), File.basename(archive)], File.join(receipt, "#{mode}-archive-checksum.log"), chdir: File.dirname(archive))
    run!(['tar', '-xf', archive, '--strip-components=1', '-C', tree], File.join(receipt, "#{mode}-extract.log"))
    File.readlines(File.join(pkg, 'distinfo')).filter_map { |l| l[/^SHA1 \((patch-[^)]+)\)/, 1] }.each do |name|
      patch = File.join(pkg, 'patches', name)
      run!(['awk', '-f', verifier, '--', '-p', File.join(pkg, 'distinfo'), patch], File.join(receipt, "#{mode}-checksum-#{name}.log"))
      run!(['patch', '-f', '-N', '-F', '0', '-p0', '-i', patch], File.join(receipt, "#{mode}-apply-#{name}.log"), chdir: tree)
    end
    FileUtils.cp(File.join(tree, 'COPYING'), File.join(receipt, 'upstream-COPYING'))
    source = File.read(File.join(tree, 'src/ck-manager.c'))
    File.write(File.join(tree, 'manager-extracted.c'), %w[get_caller_info dbus_open_session dbus_open_session_with_parameters].map { |n| function(source, n) }.join("\n"))
    %w[privilege.c privilege-policy.c launcher-connector.c].each { |n| FileUtils.cp(File.join(tests, n), tree) }
    FileUtils.cp(File.join(tree, 'libck-connector/ck-connector.h'), tree)
    %w[manager-extracted.c tools/ck-launch-session.c data/ConsoleKit.conf].each { |n| FileUtils.cp(File.join(tree, n), File.join(receipt, "#{mode}-#{File.basename(n)}")) }
    doc = REXML::Document.new(File.read(File.join(tree, 'data/ConsoleKit.conf')))
    root_policy = REXML::XPath.first(doc, '/busconfig/policy[@user="root"]')
    abort 'Root manager policy changed unexpectedly' unless root_policy && REXML::XPath.first(root_policy, 'allow[@send_destination="org.freedesktop.ConsoleKit"]')
    config = File.join(tree, 'policy.conf')
    # Only service-name ownership is granted to this test UID. The shipped
    # method policy is unmodified and decides both method calls.
    File.write(config, "<busconfig><type>session</type><listen>unix:tmpdir=#{Dir.tmpdir}</listen><auth>EXTERNAL</auth>" +
      '<policy context="default"><allow send_destination="org.freedesktop.DBus"/><allow send_type="method_return"/><allow send_type="error"/><allow receive_sender="*"/></policy>' +
      "<include>#{File.join(tree, 'data/ConsoleKit.conf')}</include><policy user=\"#{Process.euid}\"><allow own=\"org.freedesktop.ConsoleKit\"/></policy></busconfig>")
    FileUtils.cp(config, File.join(receipt, "#{mode}-private-bus.conf"))
    flags = ['-std=c11', '-D_POSIX_C_SOURCE=200809L', '-Wall', '-Wextra', '-Werror', '-I.', *cflags]
    sources = { 'manager' => ['privilege.c'], 'policy' => ['privilege-policy.c'],
                'launcher' => ['tools/ck-launch-session.c', 'launcher-connector.c'] }
    sources.each { |name, files| run!([ENV['CC'], *flags, *files, *libs, '-o', name], File.join(receipt, "#{mode}-#{name}-compile.log"), chdir: tree) }
    text, manager_status = run([File.join(tree, 'manager')], File.join(receipt, "#{mode}-manager-run.log"))
    puts "#{mode}: #{text.lines.last&.strip}"
    _, policy_status = policy_test(File.join(tree, 'policy'), config, File.join(receipt, "#{mode}-policy-run.log"))
    launcher_failures = launcher_cases(File.join(tree, 'launcher'), tree, File.join(receipt, "#{mode}-launcher-run.log"))
    puts "#{mode}: policy=#{policy_status.exitstatus}, launcher failures=#{launcher_failures}"
    if mode == 'baseline'
      abort 'Baseline did not expose all three causal regressions' unless manager_status.exitstatus == 1 && policy_status.exitstatus == 1 && launcher_failures.positive?
    else
      abort 'Candidate privilege regression failed' unless manager_status.success? && policy_status.success? && launcher_failures.zero?
    end
    sources.each do |name, files|
      files.each_with_index { |file, index| run!([ENV['CC'], *flags, '-fanalyzer', '-c', file, '-o', "#{name}-#{index}.o"], File.join(receipt, "#{mode}-#{name}-#{index}-analyzer.log"), chdir: tree) }
      args = [ENV['CPPCHECK'], '--quiet', '--enable=warning,performance,portability', '--error-exitcode=1',
              '--template={file}:{line}:{severity}:{id}:{message}', '--std=c11', '--platform=unix64',
              '-I.', *flags.select { |f| f.start_with?('-I', '-D') }, *files]
      text, status = run(args, File.join(receipt, "#{mode}-#{name}-cppcheck.log"), chdir: tree)
      abort 'Cppcheck failed' unless [0, 1].include?(status.exitstatus)
      normalized = text.lines.map { |l| l.sub(/:\d+:/, ':LINE:') }.sort
      if mode == 'baseline'; findings[name] = normalized
      else; abort "Changed #{name} findings; review logs" unless findings[name] == normalized
      end
    end
    next unless mode == 'candidate'
    sources.each { |name, files| run!([ENV['SANITIZER_CC'], *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer', *files, *libs, '-o', "#{name}-asan"], File.join(receipt, "candidate-#{name}-asan-compile.log"), chdir: tree) }
    run!([File.join(tree, 'manager-asan')], File.join(receipt, 'candidate-manager-asan-run.log'))
    _, status = policy_test(File.join(tree, 'policy-asan'), config, File.join(receipt, 'candidate-policy-asan-run.log')); abort 'Sanitizer policy failed' unless status.success?
    abort 'Sanitizer launcher failed' unless launcher_cases(File.join(tree, 'launcher-asan'), tree, File.join(receipt, 'candidate-launcher-asan-run.log')).zero?
  end
end
files = [archive, __FILE__, *%w[privilege.c privilege-policy.c launcher-connector.c].map { |n| File.join(tests, n) }, File.join(recipe, 'Makefile'), File.join(recipe, 'distinfo'), *Dir[File.join(recipe, 'patches/patch-*')]]
File.write(File.join(receipt, 'inputs.sha256'), files.map { |f| "#{Digest::SHA256.file(f).hexdigest}  #{f}\n" }.join)
File.write(File.join(receipt, 'scope.txt'), "Native host extracted manager entry points, complete launcher and actual private-bus method policy.\nControlled credential transport and launcher registration API; no target TU, real target PAM/login, kernel TTY/VT entitlement or device acceptance.\nTemporary trees, executable files and the owned test bus were removed.\n")
File.write(File.join(receipt, 'host-privilege-contracts-success'), "PASS: baseline RED; candidate source, policy, launcher, analyzers and ASan/UBSan.\n")
puts 'PASS: registration privilege host contracts; native entitlement and runtime acceptance remain pending'
