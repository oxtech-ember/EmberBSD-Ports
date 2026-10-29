#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise actual emitted CMake cross settings.
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'usage: cmake-cross.rb PREPARED_PKGSRC COMMON_CROSS_MAKECONF NEW_WORK' unless ARGV.length == 3
tree, common = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
cmake = ENV.fetch('TEST_CMAKE', 'cmake')
File.write("#{work}/mk.conf", <<~MK)
  .include "#{common}"
  .if defined(BSD_PKG_MK)
  WRKOBJDIR=#{work}/work
  EMBERBSD_COMMON_GRAPHICS_CROSS=yes
  .include "#{tree}/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
  .endif
MK

def run(log, *args)
  out, status = Open3.capture2e(*args)
  File.write(log, out)
  abort "command failed: #{log}" unless status.success?
  out
end

def check(name)
  abort "FAIL: #{name}" unless yield
  puts "PASS: #{name}"
end

base = [make, '-C', "#{tree}/devel/libepoll-shim", "MAKECONF=#{work}/mk.conf"]
refusal = 'requires the measured EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=0 or 1'
forward = '-DALLOWS_ONESHOT_TIMERS_WITH_TIMEOUT_ZERO_EXITCODE:STRING='
out = run("#{work}/probe-2.log", *base, 'EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=2', 'show-var', 'VARNAME=PKG_FAIL_REASON')
check('rejects 2 target zero-timer status') { out.include?(refusal) }
# Only AArch64 has a recorded target measurement (exit status 1).
out = run("#{work}/probe-x86_64.log", *base, 'CROSS_MACHINE_ARCH=x86_64', 'show-var', 'VARNAME=PKG_FAIL_REASON')
check('rejects a platform without a recorded zero-timer status') { out.include?(refusal) }
out = run("#{work}/probe-aarch64.log", *base, 'CROSS_MACHINE_ARCH=aarch64', 'show-vars', 'VARNAMES=PKG_FAIL_REASON CMAKE_CONFIGURE_ARGS')
lines = out.lines.map(&:chomp)
check('uses the recorded AArch64 zero-timer status 1') do
  !lines[0].to_s.include?(refusal) && Shellwords.split(lines[1].to_s).include?("#{forward}1")
end
%w[0 1].each do |value|
  out = run("#{work}/probe-#{value}.log", *base, "EMBERBSD_EPOLL_ZERO_TIMER_EXITCODE=#{value}", 'show-vars', 'VARNAMES=PKG_FAIL_REASON CMAKE_CONFIGURE_ARGS CROSS_DESTDIR')
  lines = out.lines.map(&:chomp)
  abort 'unexpected pkgsrc diagnostic lines' unless lines.length == 3
  check("accepts and forwards explicit target zero-timer status #{value}") { lines[0].empty? && Shellwords.split(lines[1]).include?("#{forward}#{value}") }
end
raw = File.readlines("#{work}/probe-1.log").map(&:chomp)
sysroot = raw.fetch(2)
flags = Shellwords.split(raw.fetch(1)).select { |v| v.match?(/\A-DCMAKE_(?:SYSTEM_NAME|SYSTEM_PROCESSOR|SYSROOT|FIND_ROOT_PATH(?:_MODE_(?:PROGRAM|LIBRARY|INCLUDE|PACKAGE))?):/) }
check('actual CMake args contain all eight cross isolation settings') { flags.length == 8 }
FileUtils.mkdir_p("#{work}/project")
File.write("#{work}/project/CMakeLists.txt", <<~CMAKE)
  cmake_minimum_required(VERSION 3.20)
  project(graphics_cross_isolation NONE)
  file(WRITE "${CMAKE_BINARY_DIR}/platform.txt" "${CMAKE_SYSTEM_NAME}\n${CMAKE_SYSTEM_PROCESSOR}\n${CMAKE_CROSSCOMPILING}\n${APPLE}\n")
  if(CMAKE_CROSSCOMPILING)
    find_library(TARGET_M NAMES m PATHS /usr/lib NO_DEFAULT_PATH REQUIRED)
    find_path(TARGET_STDIO stdio.h PATHS /usr/include NO_DEFAULT_PATH REQUIRED)
    find_program(HOST_SH NAMES sh PATHS /bin /usr/bin NO_DEFAULT_PATH REQUIRED)
    file(WRITE "${CMAKE_BINARY_DIR}/paths.txt" "${TARGET_M}\n${TARGET_STDIO}\n${HOST_SH}\n")
  endif()
CMAKE
run("#{work}/control.log", cmake, '-S', "#{work}/project", '-B', "#{work}/control")
check('unconfigured host control actually selects Darwin') { File.readlines("#{work}/control/platform.txt").map(&:chomp)[0, 3] == ['Darwin', 'arm64', 'FALSE'] }
run("#{work}/target.log", cmake, '-S', "#{work}/project", '-B', "#{work}/target", *flags)
platform = File.readlines("#{work}/target/platform.txt").map(&:chomp)
check('production cross flags select NetBSD/AArch64 instead of Darwin') { platform[0, 3] == ['NetBSD', 'aarch64', 'TRUE'] && platform.fetch(3).empty? }
paths = File.readlines("#{work}/target/paths.txt").map(&:chomp)
check('real target headers/libraries and a real host program are isolated') { paths[0].start_with?(sysroot + '/') && paths[1].start_with?(sysroot + '/') && %w[/bin/sh /usr/bin/sh].include?(paths[2]) }
puts 'PASS: real pkgsrc/CMake selection and explicit target try_run status; no dependency was built'
