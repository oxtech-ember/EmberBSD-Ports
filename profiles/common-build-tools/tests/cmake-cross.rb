#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); causal common-profile CMake configuration.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
# Recipes are UTF-8; a clean environment has no locale to say so.
Encoding.default_external = Encoding::UTF_8
abort 'Usage: cmake-cross.rb EXPORTED_PKGSRC MAKECONF NEW_WORK' unless ARGV.length == 3
tree, makeconf = ARGV.take(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[2])
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
root = File.expand_path('../../..', __dir__)
profile = root + '/profiles/common-build-tools/cross/mk.conf'
fixed = File.read(profile)
pattern = /^EMBERBSD_CROSS_CMAKE_ARGS\+= -DCMAKE_(?:SYSTEM_NAME|SYSTEM_PROCESSOR|SYSROOT|FIND_ROOT_PATH(?:_MODE_(?:PROGRAM|LIBRARY|INCLUDE|PACKAGE))?):[^\n]+\n/
removed = fixed.scan(pattern)
abort 'Expected eight common CMake settings.' unless removed.size == 8
before = fixed.gsub(pattern, '')
conf = File.read(makeconf)
include_pattern = /^\.include "[^"\n]*(?:\/profiles\/common-build-tools\/cross\/mk\.conf|\/EMBERBSD-CROSS-MK\.CONF)"$/
abort 'MAKECONF must include the common cross profile exactly once.' unless conf.scan(include_pattern).size == 1
FileUtils.mkdir_p(work + '/fixture')
File.write(work + '/fixture/CMakeLists.txt', <<~'CMAKE')
  cmake_minimum_required(VERSION 3.25)
  project(EmberCMakeCrossIdentity NONE)
  find_program(HOST_CMAKE NAMES cmake REQUIRED)
  if(CMAKE_SYSTEM_NAME STREQUAL "NetBSD")
    find_library(TARGET_EXECINFO NAMES execinfo REQUIRED)
    find_path(TARGET_PARAM NAMES sys/param.h REQUIRED)
  endif()
  file(WRITE "${CMAKE_BINARY_DIR}/identity.txt"
    "system=${CMAKE_SYSTEM_NAME}\nprocessor=${CMAKE_SYSTEM_PROCESSOR}\ncross=${CMAKE_CROSSCOMPILING}\n"
    "sysroot=${CMAKE_SYSROOT}\nroots=${CMAKE_FIND_ROOT_PATH}\nprogram=${CMAKE_FIND_ROOT_PATH_MODE_PROGRAM}\n"
    "library=${CMAKE_FIND_ROOT_PATH_MODE_LIBRARY}\ninclude=${CMAKE_FIND_ROOT_PATH_MODE_INCLUDE}\n"
    "package=${CMAKE_FIND_ROOT_PATH_MODE_PACKAGE}\nhost_cmake=${HOST_CMAKE}\n"
    "execinfo=${TARGET_EXECINFO}\nparam=${TARGET_PARAM}\n")
CMAKE
commands = []
run = lambda do |name, argv|
  out, err, status = Open3.capture3({ 'LC_ALL' => 'C' }, *argv)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  commands << { name: name, argv: argv, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Failed #{name}" unless status.success?
  out
end
bmake = ENV.fetch('BMAKE', 'bmake')
cmake = ENV.fetch('CMAKE', 'cmake')
results = {}
{ 'before' => before, 'fixed' => fixed }.each do |revision, source|
  path = work + '/' + revision + '.mk'
  File.write(path, source)
  selection = work + '/' + revision + '.conf'
  File.write(selection, conf.sub(include_pattern, '.include "' + path + '"'))
  %w[aarch64 amd64 native].each do |kind|
    name = revision + '-' + kind
    args = [bmake, '-C', tree + '/devel/abseil', "MAKECONF=#{selection}",
            "WRKOBJDIR=#{work}/objects", "PACKAGES=#{work}/packages", '_PKGSRC_BARRIER=yes']
    args += kind == 'native' ? ['USE_CROSS_COMPILE=no'] : ["EMBERBSD_CROSS_TARGET=#{kind}"]
    flags = Shellwords.split(run.call(name + '-metadata', args + ['show-var', 'VARNAME=CMAKE_CONFIGURE_ARGS']))
    selected = flags.select { |s| s.match?(/\A-DCMAKE_(?:SYSTEM_NAME|SYSTEM_PROCESSOR|SYSROOT|FIND_ROOT_PATH)(?::|_)/) }
    # This project has no compiler. The real Abseil configure/build checks target
    # GCC separately; amd64 here establishes identity/search metadata only.
    run.call(name + '-configure', [cmake, '-S', work + '/fixture', '-B', work + '/' + name] + selected)
    identity = File.readlines(work + '/' + name + '/identity.txt', chomp: true).to_h { |l| l.split('=', 2) }
    if revision == 'fixed' && kind != 'native'
      abort 'Wrong target identity.' unless identity['system'] == 'NetBSD' && identity['cross'] == 'TRUE' && identity['processor'] == (kind == 'amd64' ? 'x86_64' : kind)
      abort 'Wrong target root modes.' unless identity['program'] == 'NEVER' && %w[library include package].all? { |k| identity[k] == 'ONLY' }
      roots = identity['roots'].split(';')
      abort 'Package dependencies must precede target base files.' unless roots.size == 2 && roots[0].end_with?('/.buildlink') && roots[1] == identity['sysroot']
      abort 'Library/header escaped target root.' unless %w[execinfo param].all? { |k| identity[k].start_with?(identity['sysroot'] + '/') }
      abort 'Host program searched in target root.' if identity['host_cmake'].start_with?(identity['sysroot'] + '/')
    else
      abort 'Native configuration was forced cross.' unless identity['cross'] == 'FALSE' && selected.empty?
    end
    results[name] = { selected_flags: selected, identity: identity }
  end
end
abort 'Native recursion changed.' unless results['before-native'] == results['fixed-native']
# LLVM keeps equivalent local cross settings. Check its final argument order
# too, because a later recipe setting can override the shared profile.
%w[aarch64 amd64 native].each do |kind|
  name = 'llvm-' + kind
  args = [bmake, '-C', tree + '/lang/llvm', "MAKECONF=#{work}/fixed.conf",
          "WRKOBJDIR=#{work}/objects", "PACKAGES=#{work}/packages", '_PKGSRC_BARRIER=yes']
  args += kind == 'native' ? ['USE_CROSS_COMPILE=no'] : ["EMBERBSD_CROSS_TARGET=#{kind}"]
  flags = Shellwords.split(run.call(name + '-metadata', args + ['show-var', 'VARNAME=CMAKE_CONFIGURE_ARGS']))
  selected = flags.select { |s| s.match?(/\A-DCMAKE_(?:SYSTEM_NAME|SYSTEM_PROCESSOR|SYSROOT|FIND_ROOT_PATH)(?::|_)/) }
  run.call(name + '-configure', [cmake, '-S', work + '/fixture', '-B', work + '/' + name] + selected)
  identity = File.readlines(work + '/' + name + '/identity.txt', chomp: true).to_h { |line| line.split('=', 2) }
  if kind == 'native'
    abort 'LLVM native recursion was forced cross.' unless selected.empty? && identity['cross'] == 'FALSE'
  else
    roots = identity['roots'].split(';')
    abort 'LLVM overrides package-first lookup.' unless roots.size == 2 && roots[0].end_with?('/.buildlink') && roots[1] == identity['sysroot']
    abort 'Wrong LLVM target identity.' unless identity['system'] == 'NetBSD' && identity['processor'] == (kind == 'amd64' ? 'x86_64' : kind)
    abort 'Wrong LLVM root modes.' unless identity['program'] == 'NEVER' && %w[library include package].all? { |key| identity[key] == 'ONLY' }
  end
  results[name] = { selected_flags: selected, identity: identity }
end
# The LAPACK recipes assign CMAKE_CONFIGURE_ARGS= after the MAKECONF. The
# configure framework must still append the shared target settings, once.
%w[aarch64 native].each do |kind|
  name = 'blas-' + kind
  args = [bmake, '-C', tree + '/math/blas', "MAKECONF=#{work}/fixed.conf",
          "WRKOBJDIR=#{work}/objects", "PACKAGES=#{work}/packages", '_PKGSRC_BARRIER=yes']
  args += kind == 'native' ? ['USE_CROSS_COMPILE=no'] : ["EMBERBSD_CROSS_TARGET=#{kind}"]
  flags = Shellwords.split(run.call(name + '-metadata', args + ['show-var', 'VARNAME=CMAKE_CONFIGURE_ARGS']))
  abort 'The recipe lost its own CMake settings.' unless flags.include?('-DBUILD_DEPRECATED=ON')
  selected = flags.select { |s| s.match?(/\A-DCMAKE_(?:SYSTEM_NAME|SYSTEM_PROCESSOR|SYSROOT|FIND_ROOT_PATH)(?::|_)/) }
  run.call(name + '-configure', [cmake, '-S', work + '/fixture', '-B', work + '/' + name] + selected)
  identity = File.readlines(work + '/' + name + '/identity.txt', chomp: true).to_h { |line| line.split('=', 2) }
  if kind == 'native'
    abort 'Assigning recipe native recursion was forced cross.' unless selected.empty? && identity['cross'] == 'FALSE'
  else
    abort 'Assigning recipe dropped the target identity.' unless identity['system'] == 'NetBSD' && identity['cross'] == 'TRUE' && identity['processor'] == kind
    abort 'Assigning recipe repeats target settings.' unless selected.size == 8 && selected.uniq.size == 8
    roots = identity['roots'].split(';')
    abort 'Assigning recipe overrides package-first lookup.' unless roots.size == 2 && roots[0].end_with?('/.buildlink') && roots[1] == identity['sysroot']
  end
  results[name] = { selected_flags: selected, identity: identity }
end
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Real pkgsrc metadata and compiler-free CMake identity/search checks; amd64 is metadata only.',
  profile_sha256: Digest::SHA256.file(profile).hexdigest, results: results
}) + "\n")
puts 'PASS: actual CMake host-to-target identity change, rooted library/header lookup, native program lookup, unchanged native recursion, recipe-assigned CMake arguments; aarch64 and amd64 metadata.'
