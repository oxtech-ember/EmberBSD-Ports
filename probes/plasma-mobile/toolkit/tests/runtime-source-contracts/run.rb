#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Real pinned source contracts. External registrations are doubled explicitly.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
abort "Usage: #{$PROGRAM_NAME} DISTFILES NEW_OUTPUT QT_PREFIX" unless ARGV.size == 3
archives, work, qt = ARGV.map { |path| File.expand_path(path) }
abort 'Output exists' if File.exist?(work)
FileUtils.mkdir_p(work)
source = File.realpath(__dir__)
recipes = File.expand_path('../../recipes', source)
def run(command, log, expected = 0, **options)
  stdout, stderr, status = Open3.capture3({'ASAN_OPTIONS' => 'halt_on_error=1', 'UBSAN_OPTIONS' => 'halt_on_error=1'}, *command, **options)
  File.write(log, command.shelljoin + "\n" + stdout + stderr + "\nexit=#{status.exitstatus}\n")
  abort "Unexpected exit in #{log}: #{status.exitstatus}" unless status.exitstatus == expected
  stdout + stderr
end
def extract(archives, archive, member)
  output, status = Open3.capture2('tar', '-xOf', File.join(archives, archive), member)
  abort "Cannot read #{member}" unless status.success?
  output
end
{
  'kcoreaddons-6.31.0.tar.xz' => ['devel/kf6-kcoreaddons', 'kcoreaddons-6.31.0/src/lib/io/kdirwatch.cpp'],
  'plasma-workspace-6.8.0.tar.xz' => ['x11/plasma6-plasma-workspace', 'plasma-workspace-6.8.0/startkde/waitforname/waiter.cpp']
}.each do |archive, (recipe, _)|
  distinfo = File.read(File.join(recipes, recipe, 'distinfo'))
  expected = distinfo[/^SHA512 \(#{Regexp.escape(archive)}\) = (\h+)$/, 1]
  abort "Archive hash mismatch: #{archive}" unless expected && Digest::SHA512.file(File.join(archives, archive)).hexdigest == expected
end
FileUtils.mkdir_p(work+'/baseline/startkde/waitforname')
FileUtils.mkdir_p(work+'/baseline/src/lib/io')
%w[waiter.cpp waiter.h main.cpp].each do |name|
  File.write(work+'/baseline/startkde/waitforname/'+name,
    extract(archives,'plasma-workspace-6.8.0.tar.xz','plasma-workspace-6.8.0/startkde/waitforname/'+name))
end
File.write(work+'/baseline/src/lib/io/kdirwatch.cpp',extract(archives,'kcoreaddons-6.31.0.tar.xz','kcoreaddons-6.31.0/src/lib/io/kdirwatch.cpp'))
FileUtils.cp_r(work+'/baseline',work+'/patched')
patches = ['devel/kf6-kcoreaddons/patches/patch-src_lib_io_kdirwatch.cpp',
           'x11/plasma6-plasma-workspace/patches/patch-startkde_waitforname_argc',
           'x11/plasma6-plasma-workspace/patches/patch-startkde_waitforname_bus']
patches.each_with_index do |patch, index|
  path = File.join(recipes, patch)
  distinfo = File.read(File.expand_path('../distinfo', File.dirname(path)))
  name = File.basename(path)
  expected = distinfo[/^SHA1 \(#{Regexp.escape(name)}\) = (\h+)$/, 1]
  canonical = File.readlines(path).reject { |line| line.match?(/\$NetBSD.*/) }.join
  abort "Patch hash mismatch: #{name}" unless expected && Digest::SHA1.hexdigest(canonical) == expected
  run(['patch','-p0','-i',File.join(recipes,patch)],work+"/patch-#{index}.log",chdir:work+'/patched')
end
%w[baseline patched].each do |variant|
  input=File.read(work+'/'+variant+'/src/lib/io/kdirwatch.cpp')
  methods = %w[useQFSWatch useStat addWatch].map do |name|
    method=input[/^(?:bool|void) KDirWatchPrivate::#{name}\(Entry \*e\)\n\{.*?^\}/m]
    abort "Missing real method: #{name}" unless method
    method
  end
  File.write(work+'/'+variant+'/kdirwatch-methods.inc', methods.join("\n\n")+"\n")
  File.write(work+'/'+variant+'/startkde/waitforname/debug_p.h', "#include <QLoggingCategory>\nQ_DECLARE_LOGGING_CATEGORY(LOG_PLASMA)\n")
end
File.write(work+'/debug.cpp', "#include <QLoggingCategory>\nQ_LOGGING_CATEGORY(LOG_PLASMA, \"ember.test.waiter\")\n")
File.write(work+'/CMakeLists.txt',<<~CMAKE)
  cmake_minimum_required(VERSION 3.21)
  project(EmberRuntimeContracts LANGUAGES CXX)
  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_AUTOMOC ON)
  set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
  find_package(Qt6 6.12.0 REQUIRED COMPONENTS Core CorePrivate DBus)
  if(SANITIZE)
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address,undefined)
  endif()
  foreach(variant baseline patched)
    add_executable(waiter-${variant} ${variant}/startkde/waitforname/waiter.cpp "#{source}/waiter.cpp" debug.cpp)
    target_include_directories(waiter-${variant} PRIVATE ${variant}/startkde/waitforname)
    target_link_libraries(waiter-${variant} PRIVATE Qt6::CorePrivate Qt6::DBus)
    add_executable(kdirwatch-${variant} "#{source}/kdirwatch.cpp")
    target_include_directories(kdirwatch-${variant} PRIVATE ${variant})
    target_link_libraries(kdirwatch-${variant} PRIVATE Qt6::Core)
  endforeach()
CMAKE
cmake = ENV.fetch('CMAKE','cmake')
%w[normal sanitized].each do |mode|
  build=work+'/'+mode
  run([cmake,'-S',work,'-B',build,'-DCMAKE_PREFIX_PATH='+qt,'-DCMAKE_BUILD_TYPE=Debug',
       '-DSANITIZE='+(mode=='sanitized' ? 'ON' : 'OFF')],work+'/'+mode+'-configure.log')
  run([cmake,'--build',build,'--parallel','2'],work+'/'+mode+'-build.log')
  %w[waiter kdirwatch].each do |test|
    %w[baseline patched].each do |variant|
      log=run([build+'/'+test+'-'+variant],work+'/'+mode+'-'+test+'-'+variant+'.log',variant=='baseline' ? 1 : 0)
      abort 'Wrong causal baseline failure' if variant=='baseline' && !log.include?(test=='waiter' ? 'constructor-local argc' : 'did not reach live Stat fallback')
    end
  end
end
puts 'PASS: real Waiter argc lifetime and real KDirWatch registration/fallback; both baseline failures reproduced, patched normal/ASan/UBSan pass'
