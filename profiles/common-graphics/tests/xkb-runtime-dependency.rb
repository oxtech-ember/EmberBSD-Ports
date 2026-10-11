#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check real recipe and package runtime closure.
require 'open3'
require 'fileutils'
abort 'usage: xkb-runtime-dependency.rb PREPARED_PKGSRC MAKECONF PACKAGE NEW_WORK' unless ARGV.length == 4
tree, conf, package = ARGV.first(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
make = ENV.fetch('BMAKE', 'bmake')
base = [make, '-C', tree + '/x11/libxkbcommon', "MAKECONF=#{conf}",
        'show-vars', 'VARNAMES=PKGNAME BUILDLINK_DEPMETHOD.xkeyboard-config DEPENDS']
check = lambda do |args, label, expected|
  output, status = Open3.capture2e(*base, *args)
  File.write(work + "/#{label}.log", output)
  abort "#{label} metadata query failed" unless status.success?
  lines = output.lines.map(&:chomp)
  abort "#{label}: unexpected metadata output" unless lines.size == 3
  has_data = lines[2].split.any? { |item| item.start_with?('xkeyboard-config') }
  abort "#{label}: wrong runtime dependency" unless has_data == expected
  abort "#{label}: wrong dependency method" unless lines[1] == (expected ? 'full' : 'build')
end
check.call(['BUILDLINK_DEPMETHOD.xkeyboard-config=build'], 'original-build-only', false)
check.call([], 'runtime-data', true)
output, status = Open3.capture2e('tar', '-xOf', package, '+CONTENTS')
File.write(work + '/package-contents.txt', output)
abort 'Package omits XKB runtime data dependency' unless status.success? &&
  output.lines.any? { |line| line.start_with?('@pkgdep xkeyboard-config') }
puts 'PASS: build-only control omits data; corrected recipe and package require XKB data at runtime'
