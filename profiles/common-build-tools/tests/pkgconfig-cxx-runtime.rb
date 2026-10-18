#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc/CMake C++ provider contract.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: pkgconfig-cxx-runtime.rb PKGSRC MAKECONF TARGET_OBJECTS NATIVE_OBJECTS NEW_WORK' unless ARGV.size == 5
tree, config, target_objects, native_objects = ARGV.take(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[4])
abort 'New absolute output required.' unless ARGV[4].start_with?('/') && !File.exist?(work) && !File.symlink?(work)
profile = File.expand_path('../cross/mk.conf', __dir__)
fixed = File.read(profile)
line = 'CMAKE_CONFIGURE_ARGS+= -DCMAKE_LIBRARY_PATH:PATH=${CROSS_DESTDIR:Q}/usr/pkg/gcc16/lib' + "\n"
abort 'Expected exactly one GCC16 library search assignment.' unless fixed.scan(line).size == 1
before = fixed.sub(line, '')
config_text = File.read(config)
include_pattern = /^\.include "[^"\n]*(?:\/profiles\/common-build-tools\/cross\/mk\.conf|\/EMBERBSD-CROSS-MK\.CONF)"$/
abort 'MAKECONF must include the common cross profile once.' unless config_text.scan(include_pattern).size == 1
FileUtils.mkdir_p(work + '/source')
File.write(work + '/source/CMakeLists.txt', <<~'CMAKE')
  cmake_minimum_required(VERSION 3.25)
  project(EmberPkgConfigRuntime CXX)
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(RAW REQUIRED IMPORTED_TARGET libraw>=0.22.2)
  get_target_property(libraries PkgConfig::RAW INTERFACE_LINK_LIBRARIES)
  file(WRITE "${CMAKE_BINARY_DIR}/provider.txt"
    "libraries=${libraries}\nversion=${RAW_VERSION}\nsystem=${CMAKE_SYSTEM_NAME}\n"
    "cross=${CMAKE_CROSSCOMPILING}\ncompiler=${CMAKE_CXX_COMPILER_ID}\ncompiler_version=${CMAKE_CXX_COMPILER_VERSION}\n")
  add_executable(raw-client main.cpp)
  target_link_libraries(raw-client PRIVATE PkgConfig::RAW)
CMAKE
File.write(work + '/source/main.cpp', <<~'CPP')
  #include <libraw.h>
  #include <string>
  int main() {
      libraw_data_t* raw = libraw_init(0);
      if (!raw) return 1;
      std::string version(libraw_version());
      libraw_close(raw);
      return version.empty();
  }
CPP
commands = []
run = lambda do |name, args, env = {}|
  out, err, status = Open3.capture3(env, *args)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  commands << {name: name, args: args, environment: env, status: status.exitstatus}
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort name + ' failed: ' + err unless status.success?
  out
end
bmake = ENV.fetch('BMAKE', 'bmake')
cmake = ENV.fetch('CMAKE', 'cmake')
readelf = ENV.fetch('READELF', 'readelf')
results = {}; native = {}; providers = {}
{'before' => before, 'fixed' => fixed}.each do |revision, text|
  File.write(work + '/' + revision + '.mk', text)
  conf = work + '/' + revision + '.conf'
  File.write(conf, config_text.sub(include_pattern, '.include "' + work + '/' + revision + '.mk"'))
  %w[target native].each do |kind|
    name = revision + '-' + kind
    objects = kind == 'target' ? target_objects : native_objects
    args = [bmake, '-C', tree + '/graphics/freeimage', 'MAKECONF=' + conf,
            'WRKOBJDIR=' + objects, '_PKGSRC_BARRIER=yes']
    args << 'USE_CROSS_COMPILE=no' if kind == 'native'
    query = lambda { |key| run.call(name + '-' + key, args + ['show-var', 'VARNAME=' + key]).strip }
    flags = Shellwords.split(query.call('CMAKE_CONFIGURE_ARGS'))
    env = Shellwords.split(query.call('CONFIGURE_ENV')).to_h { |s| s.split('=', 2) }
    wrapper = env.fetch('PKG_CONFIG')
    abort 'Prepare genuine FreeImage tools/buildlink first.' unless File.executable?(wrapper) && File.realpath(wrapper).start_with?(objects + '/')
    if kind == 'target'
      %w[LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH].each { |key| env[key] = nil }
      sdk = query.call('CROSS_DESTDIR')
      abort 'Wrong pkg-config sysroot.' unless env['PKG_CONFIG_SYSROOT_DIR'] == sdk
      %w[usr/lib/libstdc++.so usr/pkg/gcc16/lib/libstdc++.so usr/pkg/lib/libraw.so usr/pkg/lib/pkgconfig/libraw.pc].each do |relative|
        path = File.realpath(sdk + '/' + relative)
        abort 'Provider escaped SDK.' unless path.start_with?(sdk + '/')
        hash = Digest::SHA256.file(path).hexdigest
        abort 'Provider mutated during comparison.' if providers.key?(path) && providers[path] != hash
        providers[path] = hash
      end
    else
      native[revision] = {flags: flags, environment: env}
    end
    raw = run.call(name + '-pkg-config', [wrapper, '--libs', 'libraw'], env)
    abort 'The actual provider no longer requests explicit C++ linkage.' unless raw.split.include?('-lstdc++')
    run.call(name + '-configure', [cmake, '-S', work + '/source', '-B', work + '/' + name] + flags, env)
    found = File.readlines(work + '/' + name + '/provider.txt', chomp: true).to_h { |s| s.split('=', 2) }
    abort 'Wrong actual compiler.' unless found['compiler'] == 'GNU' && found['compiler_version'].start_with?('16.')
    abort 'Wrong cross identity.' unless found['cross'] == (kind == 'target' ? 'TRUE' : 'FALSE') && (kind != 'target' || found['system'] == 'NetBSD')
    run.call(name + '-build', [cmake, '--build', work + '/' + name, '--parallel', '1'], env)
    executable = work + '/' + name + '/raw-client'
    elf = run.call(name + '-elf', [readelf, '-h', '-d', executable])
    if kind == 'target'
      abort 'Wrong target ELF.' unless elf.include?('AArch64')
      expected = revision == 'fixed' ? [sdk + '/usr/pkg/gcc16/lib/libstdc++.so'] : [sdk + '/usr/lib/libstdc++.so']
      actual = found.fetch('libraries').split(';').grep(%r{/libstdc\+\+\.so$})
      abort 'Wrong imported C++ provider.' unless actual.map { |p| File.realpath(p) } == expected.map { |p| File.realpath(p) }
      needed = elf.scan(/\(NEEDED\).*?\[(libstdc\+\+\.so\.\d+)\]/).flatten.sort
      abort 'Wrong linked C++ ABI.' unless needed == (revision == 'fixed' ? ['libstdc++.so.7'] : %w[libstdc++.so.7 libstdc++.so.9])
      paths = elf.lines.grep(/\((?:RPATH|RUNPATH)\)/).flat_map { |s| s[/\[([^\]]*)\]/, 1].split(':', -1) }
      abort 'Non-target runtime path.' unless paths.include?('/usr/pkg/gcc16/lib') && (paths - %w[/usr/pkg/lib /usr/pkg/gcc16/lib /usr/lib /lib]).empty?
    else
      run.call(name + '-run', [executable])
    end
    results[name] = found.merge(binary_sha256: Digest::SHA256.file(executable).hexdigest)
  end
end
abort 'Native metadata changed.' unless native['before'] == native['fixed']
before_native = results.fetch('before-native').reject { |k, _| k == :binary_sha256 }
after_native = results.fetch('fixed-native').reject { |k, _| k == :binary_sha256 }
abort 'Native provider changed.' unless before_native == after_native
File.write(work + '/result.json', JSON.pretty_generate(scope: 'Real pkgsrc metadata/wrappers, installed LibRaw, GCC16 and CMake; native execution and target ELF links, no target execution.',
  profile_sha256: Digest::SHA256.file(profile).hexdigest, helper_sha256: Digest::SHA256.file(__FILE__).hexdigest,
  provider_sha256: providers, results: results) + "\n")
puts 'PASS: explicit target C++ linkage selects sole GCC16 ABI; native metadata/providers are unchanged.'
