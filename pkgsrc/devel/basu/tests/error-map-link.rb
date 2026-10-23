#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Relink the actual upstream marshal test.
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'Usage: error-map-link.rb BASU_MESON_BUILD NEW_OUTPUT' unless ARGV.size == 2
build, work = ARGV.map { |p| File.expand_path(p) }
Dir.mkdir(work)
commands, status = Open3.capture2(ENV.fetch('NINJA'), '-C', build, '-t', 'commands', 'test-bus-marshal')
raise 'Cannot read the production link command' unless status.success?
line = commands.lines.find { |l| l.include?(' -o test-bus-marshal ') }
raise 'Missing marshal test link command' unless line
args = Shellwords.split(line)
raise 'Expected section garbage collection' unless args.include?('-Wl,--gc-sections')
args[0] = ENV.fetch('CC')
args = args.reject { |a| a == '-Wl,-z,nostart-stop-gc' }
readelf = ENV.fetch('READELF')
%w[original retained].each do |variant|
  command = args.dup
  target = File.join(work, variant)
  command[command.index('-o') + 1] = target
  command << '-Wl,-z,nostart-stop-gc' if variant == 'retained'
  File.write(File.join(work, "#{variant}.command"), Shellwords.join(command) + "\n")
  output, result = Open3.capture2e(*command, chdir: build)
  File.write(File.join(work, "#{variant}.log"), output)
  if variant == 'original'
    raise 'Original link did not reproduce the error-map failure' if result.success? || !output.include?('undefined symbol: __start_BUS_ERROR_MAP')
  else
    raise "Retained map link failed: #{output}" unless result.success?
    symbols, result = Open3.capture2e(readelf, '-Ws', target)
    File.write(File.join(work, 'symbols.txt'), symbols)
    raise 'Cannot read linked symbols' unless result.success?
    %w[__start_BUS_ERROR_MAP __stop_BUS_ERROR_MAP bus_standard_errors].each do |name|
      row = symbols.lines.find { |l| l.split.last == name }
      raise "Missing defined symbol #{name}" unless row && row.split[6] != 'UND'
    end
    sections, result = Open3.capture2e(readelf, '-SW', target)
    File.write(File.join(work, 'sections.txt'), sections)
    raise 'Missing retained error-map section' unless result.success? && sections.include?('BUS_ERROR_MAP')
  end
end
puts 'PASS: original upstream test link fails; retained error-map link and definitions pass'
puts 'Target execution is not part of this host check.'
