#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); real pkgsrc pkg-config/CMake cross contract.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: pkgconfig-sysroot.rb EXPORTED_PKGSRC MAKECONF TARGET_WRKOBJDIR NATIVE_WRKOBJDIR NEW_WORK' unless ARGV.size == 5
tree, makeconf, target_objects, native_objects = ARGV.take(4).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[4])
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
profile = File.expand_path('../cross/mk.conf', __dir__)
fixed = File.read(profile)
pattern = /^(?:CONFIGURE_ENV|MAKE_ENV)\+= PKG_CONFIG_SYSROOT_DIR=\$\{CROSS_DESTDIR:Q\}\n/
abort 'Expected both common pkg-config environment assignments.' unless fixed.scan(pattern).size == 2
before = fixed.gsub(pattern, '')
conf = File.read(makeconf)
include_pattern = /^\.include "[^"\n]*(?:\/profiles\/common-build-tools\/cross\/mk\.conf|\/EMBERBSD-CROSS-MK\.CONF)"$/
abort 'MAKECONF must include the common cross profile exactly once.' unless conf.scan(include_pattern).size == 1
FileUtils.mkdir_p(work + '/source')
File.write(work + '/source/CMakeLists.txt', <<~'CMAKE')
  cmake_minimum_required(VERSION 3.25)
  project(EmberPkgConfigSysroot C)
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(ZSTD REQUIRED IMPORTED_TARGET libzstd>=1.5.7)
  get_target_property(includes PkgConfig::ZSTD INTERFACE_INCLUDE_DIRECTORIES)
  get_target_property(libraries PkgConfig::ZSTD INTERFACE_LINK_LIBRARIES)
  file(WRITE "${CMAKE_BINARY_DIR}/provider.txt"
    "includes=${includes}\nlibraries=${libraries}\nversion=${ZSTD_VERSION}\n"
    "system=${CMAKE_SYSTEM_NAME}\ncross=${CMAKE_CROSSCOMPILING}\n"
    "compiler=${CMAKE_C_COMPILER_ID}\ncompiler_version=${CMAKE_C_COMPILER_VERSION}\n")
  add_library(zstd-contract SHARED library.c)
  target_link_libraries(zstd-contract PRIVATE PkgConfig::ZSTD)
  add_executable(zstd-client main.c)
  target_link_libraries(zstd-client PRIVATE zstd-contract PkgConfig::ZSTD)
  install(TARGETS zstd-contract zstd-client LIBRARY DESTINATION lib RUNTIME DESTINATION bin)
CMAKE
File.write(work + '/source/library.c', <<~'C')
  #include <zstd.h>
  unsigned zstd_contract(void) { return ZSTD_versionNumber(); }
C
File.write(work + '/source/main.c', <<~'C')
  #include <zstd.h>
  extern unsigned zstd_contract(void);
  int main(void) { return zstd_contract() != ZSTD_versionNumber() || ZSTD_versionNumber() != ZSTD_VERSION_NUMBER; }
C
commands = []
run = lambda do |name, argv, env = {}, success = true|
  out, err, status = Open3.capture3(env.merge('LC_ALL' => 'C'), *argv)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  commands << { name: name, argv: argv, environment: env, status: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort "Unexpected status for #{name}." unless status.success? == success
  out + err
end
bmake = ENV.fetch('BMAKE', 'bmake')
cmake = ENV.fetch('CMAKE', 'cmake')
readelf = ENV.fetch('READELF', 'readelf')
results = {}
native_metadata = {}
{ 'before' => before, 'fixed' => fixed }.each do |revision, source|
  copy = work + '/' + revision + '.mk'
  selection = work + '/' + revision + '.conf'
  File.write(copy, source)
  File.write(selection, conf.sub(include_pattern, '.include "' + copy + '"'))
  %w[target native].each do |kind|
    name = revision + '-' + kind
    objects = kind == 'target' ? target_objects : native_objects
    args = [bmake, '-C', tree + '/graphics/openexr', "MAKECONF=#{selection}",
            "WRKOBJDIR=#{objects}", '_PKGSRC_BARRIER=yes']
    args << 'USE_CROSS_COMPILE=no' if kind == 'native'
    query = lambda { |variable| run.call(name + '-' + variable, args + ['show-var', "VARNAME=#{variable}"]) }
    flags = Shellwords.split(query.call('CMAKE_CONFIGURE_ARGS'))
    env = Shellwords.split(query.call('CONFIGURE_ENV')).to_h { |s| s.split('=', 2) }
    make_env = Shellwords.split(query.call('MAKE_ENV')).to_h { |s| s.split('=', 2) }
    native_metadata[revision] = { flags: flags, environment: env, make_environment: make_env } if kind == 'native'
    %w[LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH].each { |key| env[key] = nil } if kind == 'target'
    # An inherited sysroot must not conceal the baseline omission.
    env['PKG_CONFIG_SYSROOT_DIR'] = nil unless env.key?('PKG_CONFIG_SYSROOT_DIR')
    wrapper = env.fetch('PKG_CONFIG')
    abort 'Prepare the actual OpenEXR tools/buildlink stages first.' unless File.executable?(wrapper)
    abort 'The pkg-config wrapper must belong to the prepared build tree.' unless File.realpath(wrapper).start_with?(objects + '/')
    raw = run.call(name + '-pkg-config', [wrapper, '--cflags', '--libs', 'libzstd'], env)
    rejected = revision == 'before' && kind == 'target'
    out = run.call(name + '-configure', [cmake, '-S', work + '/source', '-B', work + '/' + name] + flags, env, !rejected)
    found = File.readlines(work + '/' + name + '/provider.txt', chomp: true).to_h { |line| line.split('=', 2) }
    abort 'Use actual GCC16.' unless found['compiler'] == 'GNU' && found['compiler_version'].start_with?('16.')
    abort 'Wrong CMake target identity.' unless found['cross'] == (kind == 'target' ? 'TRUE' : 'FALSE') && (kind != 'target' || found['system'] == 'NetBSD')
    results[name] = found.merge('pkg_config' => raw)
    if rejected
      abort 'The baseline must fail at the unrooted imported include path.' unless out.include?('PkgConfig::ZSTD') && out.include?('non-existent path') && out.include?('/usr/pkg/include')
      next
    end
    if kind == 'target'
      sysroot = query.call('CROSS_DESTDIR').strip
      abort 'Wrong configure/build sysroot.' unless env['PKG_CONFIG_SYSROOT_DIR'] == sysroot && make_env['PKG_CONFIG_SYSROOT_DIR'] == sysroot
      includes = found.fetch('includes').split(';')
      libraries = found.fetch('libraries').split(';')
      abort 'Target includes escaped the sysroot.' unless includes == [sysroot + '/usr/pkg/include']
      abort 'Target library escaped the sysroot.' unless libraries.size == 1 && File.realpath(libraries[0]).start_with?(sysroot + '/usr/pkg/lib/')
      results[name]['header_sha256'] = Digest::SHA256.file(includes[0] + '/zstd.h').hexdigest
      results[name]['library_sha256'] = Digest::SHA256.file(libraries[0]).hexdigest
      abort 'Target runtime path was rooted by pkg-config.' if raw.include?('-Wl,-R' + sysroot)
    end
    run.call(name + '-build', [cmake, '--build', work + '/' + name, '--parallel', '1'], env)
    run.call(name + '-install', [cmake, '--install', work + '/' + name], env.merge('DESTDIR' => work + '/' + name + '-stage'))
    if kind == 'target'
      %w[lib/libzstd-contract.so bin/zstd-client].each do |relative|
        installed = work + '/' + name + '-stage/usr/pkg/' + relative
        elf = run.call(name + '-' + File.basename(relative) + '-elf', [readelf, '-h', '-d', installed])
        abort 'Wrong target ELF or dependency.' unless elf.include?('AArch64') && elf.include?('Shared library: [libzstd.so.1]')
        paths = elf.lines.grep(/\((?:RPATH|RUNPATH)\)/).flat_map do |line|
          value = line[/\[([^\]]*)\]/, 1]
          abort 'Unrecognized runtime path record.' unless value
          value.split(':', -1)
        end
        allowed = %w[/usr/pkg/lib /usr/pkg/gcc16/lib /usr/lib /lib]
        abort 'Installed runtime paths contain non-target directories.' unless (paths - allowed).empty?
        abort 'Installed target library path is absent.' unless paths.include?('/usr/pkg/lib')
      end
    end
  end
end
abort 'Native configure/build metadata changed.' unless native_metadata['before'] == native_metadata['fixed']
abort 'Native provider changed.' unless results['before-native'] == results['fixed-native']
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Real pkgsrc wrappers, installed zstd and GCC16; target ELF linkage, no target execution.',
  profile_sha256: Digest::SHA256.file(profile).hexdigest, results: results
}) + "\n")
puts 'PASS: target pkg-config paths use the sysroot, installed RPATH stays target-only, native metadata stays unchanged.'
