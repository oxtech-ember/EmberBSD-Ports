#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), validate real upstream Designer option patches.
require 'digest'
require 'fileutils'
require 'open3'
abort 'usage: designer-options.rb DISTFILES NEW_WORK' unless ARGV.length == 2
root = File.expand_path('..', __dir__)
distfiles = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'NEW_WORK must be absent and absolute' unless ARGV[1].start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
cmake = ENV.fetch('CMAKE', 'cmake')
manifest = File.readlines("#{root}/sources.tsv").reject { |l| l.start_with?('#') }.map { |l| l.strip.split("\t") }.to_h { |a| [a[0], a[1..]] }
count = 0
Dir.glob("#{root}/recipes/*/kf6-*/PLIST").sort.each do |plist|
  next unless File.read(plist).include?('qt6/plugins/designer/')
  recipe = File.dirname(plist).delete_prefix("#{root}/recipes/")
  archive, hash, = manifest.fetch(recipe)
  input = "#{distfiles}/#{archive}"
  abort "archive mismatch: #{archive}" unless Digest::SHA256.file(input).hexdigest == hash
  source, err, status = Open3.capture3('tar', '-xOf', input, "#{archive.delete_suffix('.tar.xz')}/CMakeLists.txt")
  abort err unless status.success?
  name = File.basename(recipe)
  dir = "#{work}/#{name}"
  FileUtils.mkdir_p(dir)
  File.write("#{dir}/CMakeLists.txt", source)
  old = source.lines.map(&:strip).find { |l| l.match?(/^(?:cmake_dependent_option|option)\(BUILD_DESIGNERPLUGIN /) }
  abort "missing upstream option: #{recipe}" unless old
  patch = "#{root}/recipes/#{recipe}/patches/patch-CMakeLists.txt"
  if File.exist?(patch)
    output, status = Open3.capture2e('patch', '-f', '-N', '-F', '0', '-p0', '-d', dir, '-i', patch)
    File.write("#{dir}/patch.log", output)
    abort "patch failed: #{recipe}" unless status.success?
    output, status = Open3.capture2e('patch', '-f', '-N', '-F', '0', '-p0', '-d', dir, '-i', patch)
    File.write("#{dir}/repeated.log", output)
    abort "repeated patch accepted: #{recipe}" if status.success?
  end
  fixed = File.read("#{dir}/CMakeLists.txt").lines.map(&:strip).find { |l| l.start_with?('option(BUILD_DESIGNERPLUGIN ') }
  abort "cross option still excluded: #{recipe}" unless fixed
  [[false, old, nil, 'ON'], [true, old, nil, old.start_with?('option(') ? 'ON' : 'OFF'],
   [false, fixed, nil, 'ON'], [true, fixed, nil, 'ON'], [true, fixed, 'OFF', 'OFF']].each_with_index do |(cross, option, override, expected), i|
    script = "#{dir}/case-#{i}.cmake"
    value = "#{dir}/value-#{i}"
    File.write(script, "cmake_minimum_required(VERSION 3.21)\ninclude(CMakeDependentOption)\nset(CMAKE_CROSSCOMPILING #{cross ? 'TRUE' : 'FALSE'})\n" +
      (override ? "set(BUILD_DESIGNERPLUGIN #{override} CACHE BOOL \"User choice\")\n" : '') + option + "\nfile(WRITE \"#{value}\" \"${BUILD_DESIGNERPLUGIN}\")\n")
    output, status = Open3.capture2e(cmake, '-P', script)
    File.write("#{dir}/case-#{i}.log", output)
    abort "wrong option result: #{recipe}, #{i}" unless status.success? && File.read(value) == expected
  end
  count += 1
end
abort 'expected all eleven Frameworks plugin providers' unless count == 11
puts "PASS: #{count} verified upstream sources; zero-fuzz patches, native/cross defaults and explicit OFF preserved"
