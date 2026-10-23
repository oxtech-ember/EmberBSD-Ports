#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the actual pkgsrc interpreter helper.
require 'digest'
require 'fileutils'
require 'open3'

abort 'Usage: cross-generator.rb PKGSRC CROSS_MAKECONF ARCHIVE NEW_OUTPUT' unless ARGV.length == 4
pkgsrc, conf, archive, output = ARGV.map { |p| File.expand_path(p) }
recipe = File.expand_path('../Makefile', __dir__)
abort 'Output already exists' if File.exist?(output) || File.symlink?(output)
abort 'Archive SHA256 differs' unless Digest::SHA256.file(archive).hexdigest ==
  '43b327073d1ac7bc6cbc0d3dfff729348fc970dfff0551ad40e366332e990204'
bmake = ENV.fetch('BMAKE', 'bmake')
base = [bmake, '-C', "#{pkgsrc}/devel/basu", '-f', recipe, "MAKECONF=#{conf}"]
vars = %w[USE_CROSS_COMPILE PYTHON_FOR_BUILD_ONLY TOOL_PYTHONBIN PYTHONBIN REPLACE_TOOL_PYTHON REPLACE_PYTHON DEPENDS TOOLBASE MESON_BINARY.gperf SITES.basu-0.2.1.tar.gz]
values, err, status = Open3.capture3(*(base + vars.flat_map { |v| ['-v', v] }))
abort err unless status.success?
config = vars.zip(values.lines.map(&:chomp)).to_h
abort 'A real cross configuration is required' unless config['USE_CROSS_COMPILE'] == 'yes'
abort 'Python must be a build tool only' unless config['PYTHON_FOR_BUILD_ONLY'] == 'tool'
abort 'Generator must use REPLACE_TOOL_PYTHON' unless config['REPLACE_TOOL_PYTHON'] == 'src/basic/generate-gperfs.py'
abort 'Generator still has target replacement' unless config['REPLACE_PYTHON'].empty?
abort 'Host and target Python paths must differ' if config['TOOL_PYTHONBIN'] == config['PYTHONBIN']
abort 'Host Python is not executable' unless File.executable?(config['TOOL_PYTHONBIN'])
abort 'Unexpected Python runtime dependency' if config['DEPENDS'].split.any? { |dep| dep.match?(/\Apython[0-9]/) }
gperf = File.join(config.fetch('TOOLBASE'), 'bin/gperf')
abort 'Meson must use the declared native gperf' unless config['MESON_BINARY.gperf'] == gperf
abort 'Source archive URL is not selected' unless config['SITES.basu-0.2.1.tar.gz'] ==
  '-https://git.sr.ht/~emersion/basu/archive/v0.2.1.tar.gz'
meson = File.join(config.fetch('TOOLBASE'), 'bin/meson')
abort 'Native Meson is not executable' unless File.executable?(meson)
original, err, status = Open3.capture3('tar', '-xOf', archive, 'basu-v0.2.1/src/basic/generate-gperfs.py')
abort err unless status.success?
FileUtils.mkdir_p("#{output}/source/src/basic")
File.write("#{output}/metadata.txt", vars.map { |v| "#{v}=#{config[v]}\n" }.join)
script = "#{output}/source/src/basic/generate-gperfs.py"
input = "#{output}/errno-list.txt"
File.write(input, "EINVAL\nENOMEM\nEIO\n")
replacement = base + ["WRKDIR=#{output}/work", "WRKSRC=#{output}/source"]
run_helper = lambda do |name, extra|
  out, error, result = Open3.capture3(*(replacement + extra + ['replace-interpreter']))
  File.write("#{output}/#{name}.log", out + error)
  abort "#{name} failed: #{error}" unless result.success?
end
# Reproduce the old target-interpreter classification with an absent target.
File.write(script, original)
File.chmod(0o755, script)
run_helper.call('negative-target', ['REPLACE_TOOL_PYTHON=',
  'REPLACE_PYTHON=src/basic/generate-gperfs.py', "PYTHONBIN=#{output}/absent-target-python"])
begin
  Open3.capture3(script, 'errno', '', input)
  abort 'Negative control accepted the absent target interpreter'
rescue Errno::ENOENT
  puts 'PASS: old target interpreter classification fails before the script starts'
end
File.write(script, original)
File.chmod(0o755, script)
run_helper.call('native-tool', [])
lines = File.readlines(script)
abort 'Incorrect native shebang' unless lines.first.chomp == "#!#{config['TOOL_PYTHONBIN']}"
abort 'Generator body changed' unless lines.drop(1).join == original.lines.drop(1).join
captured = "#{output}/errno-from-name.gperf"
out, err, status = Open3.capture3(meson, '--internal', 'exe', '--capture', captured,
  '--', script, 'errno', '', input)
File.write("#{output}/meson-generator.log", out + err)
abort 'Meson could not execute the rewritten generator' unless status.success?
result = File.read(captured)
abort 'Generated errno table is incomplete' unless result.include?('struct errno_name') &&
  %w[EINVAL ENOMEM EIO].all? { |name| result.include?("#{name}, #{name}\n") }
puts 'PASS: native generator executes through the original Meson capture path'
out, err, status = Open3.capture3(gperf, '-L', 'ANSI-C', '-t', '--ignore-case',
  '-N', 'lookup_errno', '-H', 'hash_errno_name', '-p', '-C', captured)
File.write("#{output}/errno-from-name.h", out)
abort "Declared native gperf failed: #{err}" unless status.success? &&
  out.include?('lookup_errno') && out.include?('hash_errno_name') &&
  %w[EINVAL ENOMEM EIO].all? { |name| out.include?(name) }
version, err, status = Open3.capture3(gperf, '--version')
abort err unless status.success?
File.write("#{output}/gperf-version.txt", version)
puts 'PASS: declared native gperf generates the errno lookup table'
out, err, status = Open3.capture3(script, 'capability', 'CAP_', input)
abort 'Generator prefix behavior changed' unless status.success? &&
  out.include?('struct capability_name') && out.include?("EINVAL, CAP_EINVAL\n")
puts 'PASS: upstream generator body and prefix behavior are preserved'
out, err, status = Open3.capture3(meson, '--internal', 'exe', '--capture', "#{output}/invalid.gperf",
  '--', script, 'errno', '', "#{output}/missing-input")
File.write("#{output}/missing-input.log", out + err)
abort 'Missing input did not fail' if status.success?
puts 'PASS: generator failure propagates through Meson'
puts 'PASS: Python is a native build tool, with no target Python runtime dependency'
