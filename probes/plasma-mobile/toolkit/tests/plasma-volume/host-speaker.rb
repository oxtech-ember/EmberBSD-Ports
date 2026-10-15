#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
require 'digest'
require 'fileutils'
require 'open3'
abort "Usage: #{$PROGRAM_NAME} DISTFILES NEW_WORK QT_PREFIX CANBERRA_INCLUDE" unless ARGV.length == 4
archives, work, qt, canberra = ARGV.map { |p| File.expand_path(p) }
toolkit = File.expand_path('../..', __dir__)
archive = "#{archives}/plasma-pa-6.8.0.tar.xz"
record = File.readlines("#{toolkit}/sources.tsv").map { |l| l.split("\t") }.find { |r| r[0] == 'audio/plasma6-plasma-pa' }
abort 'Source SHA256 differs' unless record && Digest::SHA256.file(archive).hexdigest == record[2]
Dir.mkdir(work)
def run!(*args)
  abort "Command failed: #{args.inspect}" unless system(*args)
end
run!('tar', '-xJf', archive, '-C', work, 'plasma-pa-6.8.0/src/speakertest.cpp')
source = "#{work}/plasma-pa-6.8.0/src/speakertest.cpp"
original = File.read(source)
patch = "#{toolkit}/recipes/audio/plasma6-plasma-pa/patches/patch-src_speakertest.cpp"
Dir.chdir("#{work}/plasma-pa-6.8.0") { run!('patch', '-p0', '-i', patch) }
fixed = File.read(source)
%w[baseline fixed].each do |variant|
  directory = "#{work}/#{variant}"
  Dir.mkdir(directory)
  body = variant == 'baseline' ? original : fixed
  # Remove only local includes. Keep every production statement and callback.
  body = body.lines.reject { |line| line.match?(/^#include "/) }.join
  File.write("#{directory}/speaker-source.inc", body)
  FileUtils.cp("#{__dir__}/speaker-fallback.cpp", directory)
  FileUtils.cp("#{canberra}/canberra.h", directory)
  File.write("#{directory}/CMakeLists.txt", <<~CMAKE)
    cmake_minimum_required(VERSION 3.21)
    project(SpeakerFallbackTest LANGUAGES CXX)
    set(CMAKE_CXX_STANDARD 20)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
    find_package(Qt6 6.12 REQUIRED COMPONENTS Core)
    add_executable(speaker-fallback speaker-fallback.cpp)
    target_include_directories(speaker-fallback PRIVATE .)
    target_link_libraries(speaker-fallback PRIVATE Qt6::Core)
    target_compile_options(speaker-fallback PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(speaker-fallback PRIVATE -fsanitize=address,undefined)
  CMAKE
  cmake = ENV.fetch('CMAKE', 'cmake')
  run!(cmake, '-S', directory, '-B', "#{directory}/build", "-DCMAKE_PREFIX_PATH=#{qt}", '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON')
  run!(cmake, '--build', "#{directory}/build", '--parallel', '2')
  output, status = Open3.capture2e({'ASAN_OPTIONS'=>'halt_on_error=1', 'UBSAN_OPTIONS'=>'halt_on_error=1'}, "#{directory}/build/speaker-fallback")
  File.write("#{directory}/result.log", output)
  puts "#{variant}: #{output}"
  if variant == 'baseline'
    abort 'Baseline did not detect the missing free' if status.success? || !output.include?('all failed requests must release callback data')
  else
    abort 'Patched production body failed' unless status.success?
  end
end
puts 'PASS: baseline ownership failure and fixed failure/success paths with ASan/UBSan'
