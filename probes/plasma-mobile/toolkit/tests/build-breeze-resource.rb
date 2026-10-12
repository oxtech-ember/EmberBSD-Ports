#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), cross-build the unchanged upstream resource test.
require 'digest'
require 'fileutils'
require 'open3'
abort 'Usage: build-breeze-resource.rb BREEZE_SOURCE SYSROOT NEW_WORK' unless ARGV.length == 3
source, sysroot = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[2])
abort 'NEW_WORK must be absent and absolute' unless ARGV[2].start_with?('/') && !File.exist?(work)
cmake, cxx, qt = ENV.fetch('CMAKE'), ENV.fetch('CXX'), ENV.fetch('QT_HOST_PATH')
FileUtils.mkdir_p(work)
files = %w[resourcetest.cpp testhelpers.h]
files.each { |name| FileUtils.cp("#{source}/autotests/#{name}", work) }
File.write(work + '/source.sha256', files.map { |name| "#{Digest::SHA256.file(work+'/'+name).hexdigest}  #{name}\n" }.join)
# Only generated test-data locations differ: both use a runtime reference tree.
File.write(work + '/testdata.h', <<~'HEADER')
  #include <QDir>
  #define PROJECT_SOURCE_DIR QDir::currentPath()
  #define PROJECT_BINARY_DIR QDir::currentPath()
  #define ICON_DIRS QStringList{ QStringLiteral("icons") }
HEADER
File.write(work + '/CMakeLists.txt', <<~'CMAKE')
  cmake_minimum_required(VERSION 3.25)
  project(InstalledBreezeResourceTest CXX)
  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_AUTOMOC ON)
  find_package(Qt6 6.12 CONFIG REQUIRED Core Gui Test)
  find_package(KF6BreezeIcons 6.31 CONFIG REQUIRED)
  add_executable(resource resourcetest.cpp)
  target_link_libraries(resource PRIVATE KF6::BreezeIcons Qt6::Core Qt6::Gui Qt6::Test)
  set_target_properties(resource PROPERTIES BUILD_WITH_INSTALL_RPATH ON
    INSTALL_RPATH "/usr/pkg/lib;/usr/pkg/qt6/lib;/usr/pkg/gcc16/lib")
CMAKE
ENV['PKG_CONFIG_SYSROOT_DIR'] = sysroot
ENV['PKG_CONFIG_LIBDIR'] = sysroot + '/usr/pkg/lib/pkgconfig'
ENV['PKG_CONFIG_PATH'] = ''
args = [cmake, '-S', work, '-B', work+'/build', "-DQT_HOST_PATH=#{qt}",
        '-DCMAKE_SYSTEM_NAME=NetBSD', '-DCMAKE_SYSTEM_PROCESSOR=aarch64',
        "-DCMAKE_CXX_COMPILER=#{cxx}", "-DCMAKE_SYSROOT=#{sysroot}",
        "-DCMAKE_FIND_ROOT_PATH=#{sysroot}", '-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER',
        '-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY', '-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY',
        '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY',
        "-DCMAKE_PREFIX_PATH=#{sysroot}/usr/pkg;#{sysroot}/usr/pkg/qt6",
        "-DCMAKE_CXX_FLAGS=-B#{sysroot}/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/",
        "-DCMAKE_EXE_LINKER_FLAGS=-L#{sysroot}/usr/pkg/gcc16/lib -Wl,-rpath,/usr/pkg/gcc16/lib"]
[['configure',args],['build',[cmake,'--build',work+'/build','-j2']]].each do |name, command|
  out, status = Open3.capture2e(*command)
  File.write(work+'/'+name+'.log',out)
  abort "#{name} failed; see saved log" unless status.success?
end
File.write(work + '/output.sha256', Digest::SHA256.file(work+'/build/resource').hexdigest + "  resource\n")
puts 'Built unchanged upstream Breeze resource test for an installed target reference tree'
