#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Real recipe flags and CMake system selection.
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'Usage: x265-cross.rb PREPARED_PKGSRC CROSS_MAKECONF NEW_WORK' unless ARGV.size == 3
tree, config = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
cmake = ENV.fetch('TEST_CMAKE', 'cmake')

def run(log, *args)
  out, status = Open3.capture2e(*args)
  File.write(log, out)
  abort "Command failed: #{log}" unless status.success?
  out
end

raw = run(work + '/recipe.log', make, '-C', tree + '/multimedia/x265', "MAKECONF=#{config}",
          'show-var', 'VARNAME=CMAKE_CONFIGURE_ARGS')
flags = Shellwords.split(raw).select { |v| v.match?(/\A-DCMAKE_SYSTEM(?:_NAME|_VERSION|_PROCESSOR)?:/) }
abort 'Recipe sets derived CMAKE_SYSTEM' if flags.any? { |v| v.start_with?('-DCMAKE_SYSTEM:') }
%w[NAME VERSION PROCESSOR].each do |part|
  abort "Missing target #{part}" unless flags.any? { |v| v.start_with?("-DCMAKE_SYSTEM_#{part}:") }
end
Dir.mkdir(work + '/source')
File.write(work + '/source/CMakeLists.txt', <<~'CMAKE')
  cmake_minimum_required(VERSION 3.20)
  project(x265_platform NONE)
  file(WRITE "${CMAKE_BINARY_DIR}/platform.txt"
       "${CMAKE_SYSTEM_NAME}\n${CMAKE_SYSTEM_PROCESSOR}\n${CMAKE_CROSSCOMPILING}\n${APPLE}\n")
CMAKE
run(work + '/good.log', cmake, '-S', work + '/source', '-B', work + '/good', *flags)
actual = File.readlines(work + '/good/platform.txt', chomp: true)
abort "Wrong target: #{actual.inspect}" unless actual == ['NetBSD', 'aarch64', 'TRUE', '']
run(work + '/original.log', cmake, '-S', work + '/source', '-B', work + '/original',
    *flags, '-DCMAKE_SYSTEM:STRING=NetBSD-11.0')
before = File.readlines(work + '/original/platform.txt', chomp: true)
abort 'Original control unexpectedly initialized cross compilation' if before[2] == 'TRUE'
puts 'PASS: actual x265 recipe initializes target CMake; original derived-variable control fails'
