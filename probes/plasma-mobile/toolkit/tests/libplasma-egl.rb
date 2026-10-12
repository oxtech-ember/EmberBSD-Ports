#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual non-GLVND Mesa provider regression.
require 'fileutils'
require 'open3'
require 'digest'
abort 'Usage: libplasma-egl.rb LIBPLASMA_SOURCE CROSS_TOOLS SYSROOT NEW_WORK' unless ARGV.size == 4
source, tools, sysroot, work = ARGV.map { |x| File.expand_path(x) }
cmake = ENV.fetch('CMAKE'); ninja = ENV.fetch('NINJA'); pkgconfig = ENV.fetch('PKG_CONFIG')
[source, tools, sysroot, work, cmake, ninja, pkgconfig].each do |p|
  abort 'Use absolute paths without CMake metacharacters' unless p.match?(%r{\A/[a-zA-Z0-9_./+-]+\z})
end
root = File.read(source + '/CMakeLists.txt')
selection = root[/# (?:OpenGL_EGL_FOUND|Non-GLVND Mesa).*?(?=\necm_find_qmlmodule)/m]
linking = File.read(source + '/src/declarativeimports/core/CMakeLists.txt')[/^if\(HAVE_EGL\)\n.*?^endif\(\)/m]
abort 'Production EGL selection/link blocks not found' unless selection && linking
Dir.mkdir(work)
File.write(work + '/egl.c', "#include <EGL/egl.h>\nEGLDisplay ember_egl_provider(void) { return eglGetDisplay(EGL_DEFAULT_DISPLAY); }\n")
File.write(work + '/CMakeLists.txt', <<~CMAKE)
  cmake_minimum_required(VERSION 3.30)
  project(EmberPlasmaEgl C CXX)
  include(FeatureSummary)
  list(APPEND CMAKE_MODULE_PATH "#{sysroot}/usr/pkg/share/ECM/find-modules")
  find_package(OpenGL REQUIRED)
  find_package(EGL REQUIRED)
  if(TARGET OpenGL::EGL)
    message(FATAL_ERROR "This regression requires the actual non-GLVND Mesa provider")
  endif()
  #{selection}
  if(NOT HAVE_EGL)
    message(FATAL_ERROR "Plasma lost the available Mesa EGL provider")
  endif()
  add_library(corebindingsplugin SHARED egl.c)
  #{linking}
CMAKE
args = [cmake, '-S', work, '-B', work + '/build', '-G', 'Ninja',
        '-DCMAKE_MAKE_PROGRAM=' + ninja, '-DCMAKE_SYSTEM_NAME=NetBSD',
        '-DCMAKE_SYSTEM_PROCESSOR=aarch64', '-DCMAKE_SYSROOT=' + sysroot,
        '-DCMAKE_FIND_ROOT_PATH=' + sysroot, '-DCMAKE_PREFIX_PATH=/usr/pkg',
        '-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER', '-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY',
        '-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY', '-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY',
        '-DCMAKE_C_COMPILER=' + tools + '/bin/aarch64--netbsd-gcc',
        '-DCMAKE_CXX_COMPILER=' + tools + '/bin/aarch64--netbsd-g++',
        '-DCMAKE_CXX_FLAGS=-B' + sysroot + '/usr/pkg/gcc16/lib/gcc/aarch64--netbsd/16.2.0/',
        '-DCMAKE_EXE_LINKER_FLAGS=-L' + sysroot + '/usr/pkg/gcc16/lib -L' + sysroot + '/usr/pkg/lib',
        '-DPKG_CONFIG_EXECUTABLE=' + pkgconfig, '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON']
env = {'PKG_CONFIG_SYSROOT_DIR' => sysroot, 'PKG_CONFIG_PATH' => '',
       'PKG_CONFIG_LIBDIR' => sysroot + '/usr/pkg/lib/pkgconfig:' + sysroot + '/usr/pkg/share/pkgconfig'}
[[args, 'configure'], [[cmake, '--build', work + '/build'], 'build']].each do |command, name|
  text, status = Open3.capture2e(env, *command)
  File.write(work + '/' + name + '.log', text)
  abort text unless status.success?
end
elf = work + '/build/libcorebindingsplugin.so'
text, status = Open3.capture2e(tools + '/bin/aarch64--netbsd-readelf', '-d', elf)
File.write(work + '/dynamic.txt', text)
abort 'EGL dependency missing from ELF' unless status.success? && text.match?(/NEEDED.*\[libEGL\.so/)
File.write(work + '/outputs.sha256', [__FILE__, source + '/CMakeLists.txt',
  source + '/src/declarativeimports/core/CMakeLists.txt', elf].map { |f| Digest::SHA256.file(f).hexdigest + '  ' + f }.join("\n") + "\n")
puts 'PASS: production Plasma selection and link blocks retain actual non-GLVND Mesa EGL'
