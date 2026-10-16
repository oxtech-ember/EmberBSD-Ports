#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), pinned ConsoleKit function regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
require 'tmpdir'

abort 'Usage: device-fd.rb VERIFIED_ARCHIVE NEW_RECEIPT_DIR' unless ARGV.length == 2
archive, receipt = ARGV.map { |p| File.expand_path(p) }
abort 'Receipt path already exists' if File.exist?(receipt)
tests = File.expand_path(__dir__)
toolkit = File.expand_path('../..', tests)
recipe = File.join(toolkit, 'recipes/sysutils/consolekit')
root = File.expand_path('../../..', toolkit)
expected = 'f3f4a424f2a4fbb67696b4011caf2fd4c02e5e67c24ef1c86cecb2301bccdba4'
abort 'ConsoleKit archive SHA256 mismatch' unless Digest::SHA256.file(archive).hexdigest == expected
%w[CC SANITIZER_CC PKG_CONFIG CPPCHECK DIGEST].each { |key| abort "Set #{key}" if ENV[key].to_s.empty? }
FileUtils.mkdir_p(receipt)

def run!(argv, log, chdir: nil)
  options = chdir ? { chdir: chdir } : {}
  output, status = Open3.capture2e(*argv, **options)
  File.write(log, "$ #{argv.shelljoin}\n#{output}")
  abort "Failed: #{argv.first}; see #{log}" unless status.success?
  output
end

def extract_function(source, name)
  # These selected upstream functions have no column-zero nested closing brace.
  match = source.match(/^#{Regexp.escape(name)}\s*\(.*?^\}\n/m)
  abort "Cannot extract #{name}" unless match
  declaration = source[0...match.begin(0)].lines.last
  declaration + match[0]
end

def fixture(argv, log)
  # The native GLib 2.90.0 GTestDBus watcher forks an unsanitized helper.
  # Own the daemon here instead. Reap exactly this PID even on fixture failure.
  reader, writer = IO.pipe
  daemon_error = File.open(log + '.dbus', 'w')
  pid = Process.spawn(ENV.fetch('DBUS_DAEMON', 'dbus-daemon'), '--session', '--nofork',
                      "--address=unix:tmpdir=#{Dir.tmpdir}", '--print-address=1', out: writer, err: daemon_error)
  writer.close
  address = reader.gets&.strip
  abort 'Private test bus did not return an address' if address.to_s.empty?
  output, status = Open3.capture2e({ 'CK_TEST_BUS_ADDRESS' => address }, *argv)
  File.write(log, "$ #{argv.shelljoin}\n#{output}")
  abort 'Sanitizer diagnostic in fixture output' if output.match?(/AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:/)
  [output, status]
ensure
  if pid
    begin
      Process.kill('TERM', pid)
    rescue Errno::ESRCH
      # The owned daemon already stopped.
    end
    Process.wait(pid)
  end
  reader&.close
  writer&.close unless writer&.closed?
  daemon_error&.close
end

verifier = File.join(root, 'upstream/pkgsrc/mk/checksum/checksum.awk')
run!(['awk', '-f', verifier, '--', File.join(recipe, 'distinfo'), File.basename(archive)],
     File.join(receipt, 'archive-checksum.log'), chdir: File.dirname(archive))
cflags = Shellwords.split(run!([ENV['PKG_CONFIG'], '--cflags', 'gio-2.0', 'gio-unix-2.0'], File.join(receipt, 'host-cflags.log')))
libs = Shellwords.split(run!([ENV['PKG_CONFIG'], '--libs', 'gio-2.0', 'gio-unix-2.0'], File.join(receipt, 'host-libs.log')))
run!([ENV['CC'], '--version'], File.join(receipt, 'gcc-version.log'))
run!([ENV['SANITIZER_CC'], '--version'], File.join(receipt, 'sanitizer-version.log'))
run!([ENV['CPPCHECK'], '--version'], File.join(receipt, 'cppcheck-version.log'))
run!([ENV['PKG_CONFIG'], '--modversion', 'gio-2.0', 'gio-unix-2.0'], File.join(receipt, 'host-gio-version.log'))
run!([ENV.fetch('DBUS_DAEMON', 'dbus-daemon'), '--version'], File.join(receipt, 'host-dbus-version.log'))

Dir.mktmpdir('consolekit-device-fd-') do |work|
  source = File.join(work, 'source')
  FileUtils.mkdir(source)
  run!(['tar', '-xf', archive, '--strip-components=1', '-C', source], File.join(receipt, 'extract.log'))
  FileUtils.cp(File.join(source, 'COPYING'), File.join(receipt, 'upstream-COPYING'))
  patches = File.readlines(File.join(recipe, 'distinfo')).filter_map { |l| l[/^SHA1 \((patch-[^)]+)\)/, 1] }
  patches.each do |name|
    patch = File.join(recipe, 'patches', name)
    run!(['awk', '-f', verifier, '--', '-p', File.join(recipe, 'distinfo'), patch],
         File.join(receipt, "checksum-#{name}.log"))
  end
  %w[baseline candidate].each do |mode|
    tree = File.join(work, mode)
    FileUtils.cp_r(source, tree)
    patches.each do |name|
      next if mode == 'baseline' && name == 'patch-src_ck-session.c'
      patch = File.join(recipe, 'patches', name)
      run!(['patch', '-f', '-N', '-F', '0', '-p0', '-i', patch],
           File.join(receipt, "#{mode}-#{name}.log"), chdir: tree)
    end
    session = File.read(File.join(tree, 'src/ck-session.c'))
    selected = %w[ck_session_get_device ck_session_create_device ck_session_remove_device
                  ck_session_remove_all_devices dbus_take_device dbus_release_device].map { |name| extract_function(session, name) }.join("\n")
    # The incoming FD list is unused in both upstream and candidate methods.
    selected = selected.sub('GUnixFDList *fd_list,', 'GUnixFDList *fd_list G_GNUC_UNUSED,')
    File.write(File.join(tree, 'extracted.c'), selected)
    FileUtils.cp(File.join(tests, 'device-fd.c'), File.join(tree, 'device-fd.c'))
    FileUtils.cp(File.join(tree, 'extracted.c'), File.join(receipt, "#{mode}-extracted.c"))
    run!([ENV.fetch('GDBUS_CODEGEN', 'gdbus-codegen'), '--c-namespace=ConsoleKit',
          '--interface-prefix=org.freedesktop.ConsoleKit.', '--generate-c-code=ck-session-generated',
          File.join(tree, 'src/org.freedesktop.ConsoleKit.Session.xml')], File.join(receipt, "#{mode}-codegen.log"), chdir: tree)
    FileUtils.cp(File.join(tree, 'ck-session-generated.c'), File.join(receipt, "#{mode}-generated.c"))
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', *cflags]
    run!([ENV['CC'], *flags, 'device-fd.c', 'ck-session-generated.c', *libs, '-o', 'fixture'],
         File.join(receipt, "#{mode}-compile.log"), chdir: tree)
    output, status = fixture([File.join(tree, 'fixture')], File.join(receipt, "#{mode}-run.log"))
    puts "#{mode}: #{output.lines.last&.strip}"
    abort 'Baseline did not expose FD ownership and rollback errors' if mode == 'baseline' && status.exitstatus != 1
    abort 'Candidate regression failed' if mode == 'candidate' && !status.success?
    run!([ENV['CC'], *flags, '-fanalyzer', '-c', 'device-fd.c', '-o', 'analyzer.o'],
         File.join(receipt, "#{mode}-gcc-analyzer.log"), chdir: tree)
    args = [ENV['CPPCHECK'], '--quiet', '--enable=warning,performance,portability', '--error-exitcode=1',
            '--template={file}:{line}:{severity}:{id}:{message}', '--std=c11', '--platform=unix64',
            *cflags.select { |f| f.start_with?('-I', '-D') }, 'device-fd.c']
    findings, check_status = Open3.capture2e(*args, chdir: tree)
    File.write(File.join(receipt, "#{mode}-cppcheck.log"), "$ #{args.shelljoin}\n#{findings}")
    abort 'Cppcheck failed to analyze the fixture' unless [0, 1].include?(check_status.exitstatus)
    if mode == 'baseline'
      @baseline_findings = findings
    else
      abort 'Cppcheck findings changed; review the baseline and candidate logs' unless findings == @baseline_findings
    end
    if mode == 'candidate'
      run!([ENV['SANITIZER_CC'], *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            'device-fd.c', 'ck-session-generated.c', *libs, '-o', 'fixture-asan'], File.join(receipt, 'candidate-asan-compile.log'), chdir: tree)
      _, status = fixture([File.join(tree, 'fixture-asan')], File.join(receipt, 'candidate-asan-run.log'))
      abort 'Sanitizer fixture failed' unless status.success?
    end
  end
end
files = [archive, __FILE__, File.join(tests, 'device-fd.c'), File.join(recipe, 'Makefile'), File.join(recipe, 'distinfo')]
files.concat(Dir[File.join(recipe, 'patches/patch-*')])
File.write(File.join(receipt, 'inputs.sha256'), files.map { |f| "#{Digest::SHA256.file(f).hexdigest}  #{f}\n" }.join)
File.write(File.join(receipt, 'scope.txt'), "Host extracted CK methods with actual generated completion, GIO FD lists and an owned private host D-Bus.\nControlled device construction only; no target TU, native target system-bus policy, controller-vanished handler, VT or device acceptance.\nTemporary source trees, executables and the private test daemon were removed.\n")
File.write(File.join(receipt, 'host-fd-contracts-success'), "PASS: baseline RED; candidate GCC16, path analysis, Cppcheck comparison and ASan/UBSan.\n")
puts 'PASS: pinned ConsoleKit methods with real host GDBus FD replies; native target/runtime gates remain pending'
