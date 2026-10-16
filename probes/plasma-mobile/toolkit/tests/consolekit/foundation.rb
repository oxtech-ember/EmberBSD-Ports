#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), pinned ConsoleKit function regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
require 'tmpdir'

abort 'Usage: foundation.rb VERIFIED_ARCHIVE NEW_RECEIPT_DIR' unless ARGV.length == 2
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

verifier = File.join(root, 'upstream/pkgsrc/mk/checksum/checksum.awk')
run!(['awk', '-f', verifier, '--', File.join(recipe, 'distinfo'), File.basename(archive)],
     File.join(receipt, 'archive-checksum.log'), chdir: File.dirname(archive))
cflags = Shellwords.split(run!([ENV['PKG_CONFIG'], '--cflags', 'gio-2.0'], File.join(receipt, 'host-cflags.log')))
libs = Shellwords.split(run!([ENV['PKG_CONFIG'], '--libs', 'gio-2.0'], File.join(receipt, 'host-libs.log')))
run!([ENV['CC'], '--version'], File.join(receipt, 'gcc-version.log'))
run!([ENV['SANITIZER_CC'], '--version'], File.join(receipt, 'sanitizer-version.log'))
run!([ENV['CPPCHECK'], '--version'], File.join(receipt, 'cppcheck-version.log'))

Dir.mktmpdir('consolekit-foundation-') do |work|
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
      next if mode == 'baseline' && %w[patch-src_ck-session.c patch-src_ck-sysdeps-netbsd.c].include?(name)
      patch = File.join(recipe, 'patches', name)
      run!(['patch', '-f', '-N', '-F', '0', '-p0', '-i', patch],
           File.join(receipt, "#{mode}-#{name}.log"), chdir: tree)
    end
    session = File.read(File.join(tree, 'src/ck-session.c'))
    sysdeps = File.read(File.join(tree, 'src/ck-sysdeps-netbsd.c'))
    selected = [extract_function(session, 'get_caller_info'), extract_function(session, 'dbus_take_control'),
                extract_function(sysdeps, 'ck_process_stat_get_tty'), extract_function(sysdeps, 'ck_get_console_num_from_device')].join("\n")
    File.write(File.join(tree, 'extracted.c'), selected)
    FileUtils.cp(File.join(tests, 'foundation.c'), File.join(tree, 'foundation.c'))
    FileUtils.cp(File.join(tree, 'extracted.c'), File.join(receipt, "#{mode}-extracted.c"))
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', *cflags]
    run!([ENV['CC'], *flags, 'foundation.c', *libs, '-o', 'fixture'],
         File.join(receipt, "#{mode}-compile.log"), chdir: tree)
    output, status = Open3.capture2e(File.join(tree, 'fixture'))
    File.write(File.join(receipt, "#{mode}-run.log"), output)
    puts "#{mode}: #{output.lines.last&.strip}"
    abort 'Baseline did not expose the missing guards' if mode == 'baseline' && status.success?
    abort 'Candidate regression failed' if mode == 'candidate' && !status.success?
    run!([ENV['CC'], *flags, '-fanalyzer', '-c', 'foundation.c', '-o', 'analyzer.o'],
         File.join(receipt, "#{mode}-gcc-analyzer.log"), chdir: tree)
    args = [ENV['CPPCHECK'], '--quiet', '--enable=warning,performance,portability', '--error-exitcode=1',
            '--template={file}:{line}:{severity}:{id}:{message}', '--std=c11', '--platform=unix64',
            *cflags.select { |f| f.start_with?('-I', '-D') }, 'foundation.c']
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
            'foundation.c', *libs, '-o', 'fixture-asan'], File.join(receipt, 'candidate-asan-compile.log'), chdir: tree)
      run!([File.join(tree, 'fixture-asan')], File.join(receipt, 'candidate-asan-run.log'))
    end
  end
end
files = [archive, __FILE__, File.join(tests, 'foundation.c'), File.join(recipe, 'Makefile'), File.join(recipe, 'distinfo')]
files.concat(Dir[File.join(recipe, 'patches/patch-*')])
File.write(File.join(receipt, 'inputs.sha256'), files.map { |f| "#{Digest::SHA256.file(f).hexdigest}  #{f}\n" }.join)
File.write(File.join(receipt, 'scope.txt'), "Host extracted-function fixture only. No target TU build, native D-Bus, VT or device acceptance.\nTemporary extracted source and executables were removed.\n")
puts 'PASS: pinned ConsoleKit foundation functions; target and runtime gates remain pending'
