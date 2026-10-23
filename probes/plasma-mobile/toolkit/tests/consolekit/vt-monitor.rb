#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), pinned native VT monitor source regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
require 'tmpdir'

abort 'Usage: vt-monitor.rb VERIFIED_ARCHIVE NEW_RECEIPT_DIR' unless ARGV.length == 2
archive, receipt = ARGV.map { |p| File.expand_path(p) }
abort 'Receipt path already exists' if File.exist?(receipt)
abort 'ConsoleKit archive SHA256 mismatch' unless Digest::SHA256.file(archive).hexdigest ==
  'f3f4a424f2a4fbb67696b4011caf2fd4c02e5e67c24ef1c86cecb2301bccdba4'
%w[CC SANITIZER_CC PKG_CONFIG CPPCHECK DIGEST].each { |key| abort "Set #{key}" if ENV[key].to_s.empty? }
tests = File.expand_path(__dir__)
toolkit = File.expand_path('../..', tests)
root = File.expand_path('../../..', toolkit)
recipe_relative = 'pkgsrc/sysutils/consolekit'
# The baseline commit predates the move into pkgsrc/.
baseline_recipe_relative = 'probes/plasma-mobile/toolkit/recipes/sysutils/consolekit'
recipe = File.join(root, recipe_relative)
baseline = '74f04e0105d96e5ae370db0b524b5a9f4e3c9be6'
verifier = File.join(root, 'upstream/pkgsrc/mk/checksum/checksum.awk')
FileUtils.mkdir_p(receipt)

def run!(args, log, chdir: nil)
  output, status = Open3.capture2e(*args, **(chdir ? { chdir: chdir } : {}))
  File.write(log, "$ #{args.shelljoin}\n#{output}")
  abort "Failed: #{args.first}; see #{log}" unless status.success?
  output
end
def function(source, name)
  match = source.match(/^#{Regexp.escape(name)}\s*\(.*?^\}\n/m)
  abort "Cannot extract #{name}" unless match
  source[0...match.begin(0)].lines.last + match[0]
end

%w[CC SANITIZER_CC CPPCHECK].each do |key|
  run!([ENV[key], '--version'], File.join(receipt, "#{key.downcase}-version.log"))
end
cflags = Shellwords.split(run!([ENV['PKG_CONFIG'], '--cflags', 'gobject-2.0'], File.join(receipt, 'host-cflags.log')))
libs = Shellwords.split(run!([ENV['PKG_CONFIG'], '--libs', 'gobject-2.0'], File.join(receipt, 'host-libs.log')))

Dir.mktmpdir('consolekit-vt-') do |work|
  previous = File.join(work, 'previous-recipe')
  FileUtils.mkdir_p(File.join(previous, 'patches'))
  old_info = run!(['git', '-C', root, 'show', "#{baseline}:#{baseline_recipe_relative}/distinfo"], File.join(receipt, 'baseline-distinfo.log'))
  File.write(File.join(previous, 'distinfo'), old_info)
  old_info.scan(/^SHA1 \((patch-[^)]+)\)/).flatten.each do |name|
    text = run!(['git', '-C', root, 'show', "#{baseline}:#{baseline_recipe_relative}/patches/#{name}"], File.join(receipt, "baseline-input-#{name}.log"))
    File.write(File.join(previous, 'patches', name), text)
  end
  findings_by_mode = {}
  %w[baseline candidate].each do |mode|
    pkg = mode == 'baseline' ? previous : recipe
    tree = File.join(work, mode)
    FileUtils.mkdir(tree)
    run!(['awk', '-f', verifier, '--', File.join(pkg, 'distinfo'), File.basename(archive)],
         File.join(receipt, "#{mode}-archive-checksum.log"), chdir: File.dirname(archive))
    run!(['tar', '-xf', archive, '--strip-components=1', '-C', tree], File.join(receipt, "#{mode}-extract.log"))
    File.readlines(File.join(pkg, 'distinfo')).filter_map { |l| l[/^SHA1 \((patch-[^)]+)\)/, 1] }.each do |name|
      patch = File.join(pkg, 'patches', name)
      run!(['awk', '-f', verifier, '--', '-p', File.join(pkg, 'distinfo'), patch],
           File.join(receipt, "#{mode}-checksum-#{name}.log"))
      run!(['patch', '-f', '-N', '-F', '0', '-p0', '-i', patch],
           File.join(receipt, "#{mode}-apply-#{name}.log"), chdir: tree)
    end
    FileUtils.cp(File.join(tree, 'COPYING'), File.join(receipt, 'upstream-COPYING'))
    sysdeps = File.read(File.join(tree, 'src/ck-sysdeps-netbsd.c'))
    unix = File.read(File.join(tree, 'src/ck-sysdeps-unix.c'))
    File.write(File.join(tree, 'reader.c'), %w[ck_get_active_console_num ck_get_console_device_for_num].map { |n| function(sysdeps, n) }.join("\n") + "\n" + function(unix, 'ck_activate_console_num'))
    session = File.read(File.join(tree, 'src/ck-session.c'))
    File.write(File.join(tree, 'session-consumer.c'), %w[ck_session_get_id ck_session_set_active].map { |n| function(session, n) }.join("\n"))
    seat = File.read(File.join(tree, 'src/ck-seat.c'))
    selected = %w[match_session_display_device match_session_x11_display_device find_all_func
                  hash_table_find_all find_sessions_for_display_device find_sessions_for_x11_display_device
                  sort_sessions_by_age find_oldest_session find_session_for_display_device
                  change_active_session update_active_vt active_vt_changed].map { |n| function(seat, n) }.join("\n")
    type = seat[/typedef struct\n\{\n        GHRFunc.*?\} HashTableFindAllData;/m]
    abort 'Missing actual seat lookup state type' unless type
    File.write(File.join(tree, 'seat-consumer.c'), type + "\n" + selected)
    File.write(File.join(tree, 'config.h'), "/* Host fixture: no generated platform capability claims. */\n")
    File.write(File.join(tree, 'src/ck-marshal.h'), "/* No generated marshal is referenced by ck-vt-monitor.c. */\n")
    FileUtils.cp(File.join(tests, 'vt-monitor.c'), File.join(tree, 'fixture.c'))
    %w[src/ck-vt-monitor.c reader.c session-consumer.c seat-consumer.c].each do |file|
      FileUtils.cp(File.join(tree, file), File.join(receipt, "#{mode}-#{File.basename(file)}"))
    end
    non_netbsd, status = Open3.capture2e(ENV.fetch('UNIFDEF', 'unifdef'), '-U__NetBSD__', File.join(tree, 'src/ck-vt-monitor.c'))
    abort 'Cannot select the unchanged non-NetBSD source' unless [0, 1].include?(status.exitstatus)
    selected = non_netbsd.lines.reject { |line| line.strip.empty? }.map { |line| line.sub(/^#if[ \t]+/, '#if ') }.join
    if mode == 'baseline'
      @non_netbsd = selected
    else
      abort 'Non-NetBSD monitor source changed' unless selected == @non_netbsd
      File.write(File.join(receipt, 'non-netbsd-source-identical.txt'), "PASS: unifdef -U__NetBSD__, ignoring blank lines and #if directive spacing only.\n")
    end
    # Upstream's complete GObject monitor uses deprecated private-data APIs.
    # Keep the diagnostic visible; only host fixture compilation is performed.
    flags = ['-std=c11', '-Wall', '-Wextra', '-I.', *cflags]
    run!([ENV['CC'], *flags, 'fixture.c', *libs, '-o', 'fixture'], File.join(receipt, "#{mode}-compile.log"), chdir: tree)
    output, status = Open3.capture2e(File.join(tree, 'fixture'))
    File.write(File.join(receipt, "#{mode}-run.log"), output)
    puts "#{mode}: #{output.lines.last&.strip}"
    abort 'Baseline did not expose the VT monitor failure' if mode == 'baseline' && status.success?
    abort 'Candidate VT regression failed' if mode == 'candidate' && !status.success?
    analysis = run!([ENV['CC'], *flags, '-fanalyzer', '-c', 'fixture.c', '-o', 'analysis.o'],
                    File.join(receipt, "#{mode}-gcc-analyzer.log"), chdir: tree)
    abort 'GCC analyzer reported a path finding' if analysis.match?(/\[-Wanalyzer-/)
    args = [ENV['CPPCHECK'], '--quiet', '--enable=warning,performance,portability', '--error-exitcode=1',
            '--template={file}:{line}:{severity}:{id}:{message}', '--std=c11', '--platform=unix64',
            '-I.', *cflags.select { |f| f.start_with?('-I', '-D') }, 'fixture.c']
    output, status = Open3.capture2e(*args, chdir: tree)
    File.write(File.join(receipt, "#{mode}-cppcheck.log"), "$ #{args.shelljoin}\n#{output}")
    abort 'Cppcheck failed to analyze the fixture' unless [0, 1].include?(status.exitstatus)
    findings_by_mode[mode] = output.lines.map { |l| l.sub(/:\d+:/, ':LINE:') }.sort
    if mode == 'candidate'
      abort 'Cppcheck has new findings' unless (findings_by_mode[mode] - findings_by_mode['baseline']).empty?
      run!([ENV['SANITIZER_CC'], *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            'fixture.c', *libs, '-o', 'fixture-asan'], File.join(receipt, 'candidate-asan-compile.log'), chdir: tree)
      run!([File.join(tree, 'fixture-asan')], File.join(receipt, 'candidate-asan-run.log'))
    end
  end
end
inputs = [archive, __FILE__, File.join(tests, 'vt-monitor.c'), File.join(recipe, 'Makefile'), File.join(recipe, 'distinfo')]
inputs.concat(Dir[File.join(recipe, 'patches/patch-*')])
File.write(File.join(receipt, 'inputs.sha256'), inputs.map { |f| "#{Digest::SHA256.file(f).hexdigest}  #{f}\n" }.join)
File.write(File.join(receipt, 'scope.txt'), "Host monitor/consumer fixture with real GLib. Target TU and native D-Bus/VT/device acceptance remain pending.\nBaseline source commit: #{baseline}\nTemporary extracted trees and executables were removed.\n")
puts 'PASS: native VT monitor host contracts; target and runtime acceptance pending'
