#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual KiCad dependency selection in pkgsrc.
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'Usage: kicad-protobuf.rb PREPARED_PKGSRC MAKECONF NEW_WORK' unless ARGV.length == 3
tree, makeconf = ARGV.first(2).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'New absolute output directory required.' unless ARGV.last.start_with?('/') && !File.exist?(work)
recipe = File.join(tree, 'cad/kicad10')
abort 'Prepared KiCad recipe is missing.' unless File.file?(File.join(recipe, 'Makefile'))
FileUtils.mkdir_p(work)
make = ENV.fetch('BMAKE', 'bmake')

query = lambda do |label, mode, *overrides|
  command = [make, '-C', recipe, "MAKECONF=#{makeconf}", mode, *overrides,
             'show-var', 'VARNAME=BUILDLINK_API_DEPENDS.protobuf']
  output, status = Open3.capture2e(*command)
  File.write(File.join(work, "#{label}.log"), output)
  abort "#{label}: pkgsrc metadata query failed (#{status.exitstatus})" unless status.success?
  Shellwords.split(output)
end

check = lambda do |label, dependencies, expected|
  protobuf_floor = dependencies.grep(/\Aprotobuf>=36\.2(?:nb1)?\z/)
  selected = protobuf_floor.uniq
  abort "#{label}: expected only #{expected}, got #{selected.inspect}" unless selected == [expected]
  puts "PASS: #{label} selects #{expected}"
end

native = query.call('native', 'USE_CROSS_COMPILE=no')
cross = query.call('cross', 'USE_CROSS_COMPILE=yes')
check.call('native KiCad', native, 'protobuf>=36.2')
check.call('cross KiCad', cross, 'protobuf>=36.2nb1')

# Deliberately override the native floor to prove the checker rejects the
# regression from commit 8f464874.
wrong_native = query.call('wrong-native', 'USE_CROSS_COMPILE=no',
                          'BUILDLINK_API_DEPENDS.protobuf=protobuf>=36.2nb1')
rejected = false
begin
  check.call('mutated native KiCad', wrong_native, 'protobuf>=36.2')
rescue SystemExit
  rejected = true
end
abort 'The native nb1 regression was not detected.' unless rejected
puts 'PASS: deliberate native protobuf nb1 regression is rejected'
