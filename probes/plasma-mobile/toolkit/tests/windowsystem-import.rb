#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual installed CMake consumer regression.
require 'open3'
require 'fileutils'
abort 'Usage: windowsystem-import.rb INSTALLED_CMAKE_DIRECTORY SYSROOT NEW_WORK' unless ARGV.length == 3
installed, sysroot = ARGV.take(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[2]); Dir.mkdir(work)
cmake, cxx = ENV.fetch('CMAKE'), ENV.fetch('CXX')
host_qt = ENV.fetch('QT_HOST_PATH')
File.write(work + '/CMakeLists.txt', <<~'CMAKE')
  cmake_minimum_required(VERSION 3.25)
  project(InstalledWindowSystemExport CXX)
  find_package(KF6WindowSystem CONFIG REQUIRED)
  add_executable(consumer main.cpp)
  target_link_libraries(consumer PRIVATE KF6::WindowSystem)
CMAKE
File.write(work + '/main.cpp', "#include <KKeyServer>\n#include <xcb/xcb.h>\nint main() { xcb_key_press_event_t event{}; return event.detail; }\n")
run = lambda do |name, *args, expected: true|
  out, result = Open3.capture2e(*args)
  File.write(work + '/' + name + '.log', out)
  abort "Unexpected result: #{name}; see saved log" unless result.success? == expected
  out
end
ENV['PKG_CONFIG_SYSROOT_DIR'] = sysroot
ENV['PKG_CONFIG_LIBDIR'] = sysroot + '/usr/pkg/lib/pkgconfig'
ENV['PKG_CONFIG_PATH'] = ''
flags = [cmake, '-S', work, "-DQT_HOST_PATH=#{host_qt}", '-DCMAKE_SYSTEM_NAME=NetBSD', '-DCMAKE_SYSTEM_PROCESSOR=aarch64',
         "-DCMAKE_CXX_COMPILER=#{cxx}", "-DCMAKE_SYSROOT=#{sysroot}",
         "-DCMAKE_FIND_ROOT_PATH=#{sysroot}", '-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER',
         '-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY', '-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY',
         '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY',
         "-DCMAKE_PREFIX_PATH=#{sysroot}/usr/pkg;#{sysroot}/usr/pkg/qt6;#{sysroot}/usr/pkg/share/ECM/cmake",
         "-DCMAKE_CXX_FLAGS=-B#{sysroot}/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/",
         "-DCMAKE_EXE_LINKER_FLAGS=-L#{sysroot}/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib"]
run.call('configure', *flags, '-B', work + '/build', "-DKF6WindowSystem_DIR=#{installed}")
run.call('build', cmake, '--build', work + '/build', '-j2')
# Reintroduce the original producer path in a private installed-export copy.
old = work + '/old/usr/pkg/lib/cmake/KF6WindowSystem'
FileUtils.mkdir_p(old)
FileUtils.cp(Dir.glob(installed + '/*.cmake'), old)
Dir.glob(sysroot + '/usr/pkg/lib/libKF6WindowSystem.so*').each do |lib|
  File.symlink(lib, work + '/old/usr/pkg/lib/' + File.basename(lib))
end
file = old + '/KF6WindowSystemTargets.cmake'
text = File.read(file)
abort 'Missing include property' unless text.include?('INTERFACE_INCLUDE_DIRECTORIES "')
File.write(file, text.sub('INTERFACE_INCLUDE_DIRECTORIES "', 'INTERFACE_INCLUDE_DIRECTORIES "/ember-missing-producer-prefix/include;'))
out = run.call('invalid-producer-prefix', *flags, '-B', work + '/invalid', "-DKF6WindowSystem_DIR=#{old}", expected: false)
abort 'Failure did not diagnose the producer path' unless out.include?('non-existent path') && out.include?('/ember-missing-producer-prefix/include')
puts 'PASS: installed KWindowSystem/XCB consumer configures and cross-links; nonrelocatable producer path rejected'
