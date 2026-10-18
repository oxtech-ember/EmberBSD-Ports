#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual pkgsrc CMake dependency precedence.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: cmake-dependency-roots.rb EXPORTED_PKGSRC MAKECONF PREPARED_WRKOBJDIR NEW_WORK' unless ARGV.size == 4
tree, makeconf, objects = ARGV.take(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[3])
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
profile = File.expand_path('../cross/mk.conf', __dir__)
fixed = File.read(profile)
new_order = '${BUILDLINK_DIR:Q}\\;${CROSS_DESTDIR:Q}'
old_order = '${CROSS_DESTDIR:Q}\\;${BUILDLINK_DIR:Q}'
abort 'Expected one common dependency-root setting.' unless fixed.scan(new_order).size == 1
before = fixed.sub(new_order, old_order)
conf = File.read(makeconf)
include_pattern = /^\.include "[^"\n]*(?:\/profiles\/common-build-tools\/cross\/mk\.conf|\/EMBERBSD-CROSS-MK\.CONF)"$/
abort 'MAKECONF must include the common cross profile exactly once.' unless conf.scan(include_pattern).size == 1
FileUtils.mkdir_p(work + '/source')
File.write(work + '/source/CMakeLists.txt', <<~'CMAKE')
  cmake_minimum_required(VERSION 3.25)
  project(EmberCMakeDependencyRoots C)
  find_package(ZLIB REQUIRED)
  include(CheckCSourceCompiles)
  set(CMAKE_REQUIRED_LIBRARIES ZLIB::ZLIB)
  check_c_source_compiles("#include <zlib.h>\nint main(void) { return zlibVersion() == 0; }" ZLIB_API_LINKS)
  if(NOT ZLIB_API_LINKS)
    message(FATAL_ERROR "The discovered zlib API does not link")
  endif()
  if(CMAKE_SYSTEM_NAME STREQUAL "NetBSD")
    find_library(BASE_EXECINFO NAMES execinfo REQUIRED)
  endif()
  file(WRITE "${CMAKE_BINARY_DIR}/provider.txt"
    "include=${ZLIB_INCLUDE_DIR}\nlibrary=${ZLIB_LIBRARY_RELEASE}\nversion=${ZLIB_VERSION}\n"
    "execinfo=${BASE_EXECINFO}\nsystem=${CMAKE_SYSTEM_NAME}\ncross=${CMAKE_CROSSCOMPILING}\n"
    "compiler=${CMAKE_C_COMPILER_ID}\ncompiler_version=${CMAKE_C_COMPILER_VERSION}\n")
CMAKE
commands = []
run = lambda do |name, argv, env = {}|
  stdout, stderr, status = Open3.capture3(env.merge('LC_ALL' => 'C'), *argv)
  File.write(work + '/' + name + '.stdout', stdout)
  File.write(work + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, environment: env, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Failed #{name}." unless status.success?
  stdout
end
bmake = ENV.fetch('BMAKE', 'bmake')
cmake = ENV.fetch('CMAKE', 'cmake')
results = {}
native_metadata = {}
{ 'before' => before, 'fixed' => fixed }.each do |revision, source|
  profile_copy = work + '/' + revision + '.mk'
  selection = work + '/' + revision + '.conf'
  File.write(profile_copy, source)
  File.write(selection, conf.sub(include_pattern, '.include "' + profile_copy + '"'))
  %w[target native].each do |kind|
    name = revision + '-' + kind
    args = [bmake, '-C', tree + '/devel/protobuf', "MAKECONF=#{selection}",
            "WRKOBJDIR=#{objects}", '_PKGSRC_BARRIER=yes']
    args << 'USE_CROSS_COMPILE=no' if kind == 'native'
    flags = Shellwords.split(run.call(name + '-flags', args + ['show-var', 'VARNAME=CMAKE_CONFIGURE_ARGS']))
    env = Shellwords.split(run.call(name + '-environment', args + ['show-var', 'VARNAME=CONFIGURE_ENV'])).to_h { |s| s.split('=', 2) }
    native_metadata[revision] = { flags: flags, environment: env } if kind == 'native'
    if kind == 'target'
      abort 'Prepare the real protobuf buildlink stage first.' unless File.file?(env.fetch('BUILDLINK_DIR') + '/include/zlib.h')
      %w[LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH].each { |key| env[key] = nil }
    end
    run.call(name + '-configure', [cmake, '-S', work + '/source', '-B', work + '/' + name] + flags, env)
    found = File.readlines(work + '/' + name + '/provider.txt', chomp: true).to_h { |line| line.split('=', 2) }
    abort 'Use the current GCC16 compiler.' unless found['compiler'] == 'GNU' && found['compiler_version'].start_with?('16.')
    header = File.realpath(found.fetch('include') + '/zlib.h')
    library = File.realpath(found.fetch('library'))
    results[name] = found.merge('header_realpath' => header, 'library_realpath' => library,
                               'header_sha256' => Digest::SHA256.file(header).hexdigest,
                               'library_sha256' => Digest::SHA256.file(library).hexdigest)
    next if kind == 'native'
    sysroot = flags.find { |s| s.start_with?('-DCMAKE_SYSROOT:') }.split('=', 2)[1]
    abort 'Wrong target identity.' unless found['system'] == 'NetBSD' && found['cross'] == 'TRUE'
    wanted = sysroot + (revision == 'fixed' ? '/usr/pkg' : '/usr')
    abort 'Wrong header provider.' unless header == File.realpath(wanted + '/include/zlib.h')
    abort 'Wrong library provider.' unless library == File.realpath(wanted + '/lib/libz.so')
    abort 'Base execinfo fallback changed.' unless File.realpath(found.fetch('execinfo')) == File.realpath(sysroot + '/usr/lib/libexecinfo.so')
  end
end
abort 'Native pkgsrc flags/environment changed.' unless native_metadata['before'] == native_metadata['fixed']
abort 'Native provider changed.' unless results['before-native'] == results['fixed-native']
abort 'The target SDK must contain distinct base and package providers for this causal check.' if results['before-target']['library_realpath'] == results['fixed-target']['library_realpath']
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Real pkgsrc configure flags/environment, GCC16 discovery and zlib API links; no target execution.',
  profile_sha256: Digest::SHA256.file(profile).hexdigest, results: results
}) + "\n")
puts 'PASS: selected package zlib precedes base zlib; base execinfo fallback and native configuration stay unchanged.'
