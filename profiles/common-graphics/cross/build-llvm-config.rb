#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compile upstream LLVM's metadata interpreter;
# do not emulate llvm-config answers or compile any LLVM library.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require_relative 'llvm-target'

UPSTREAM_SHA256 = '7c54727d9deda1689a7e6c9096f6627d73659da04a6ac88c3e0a0595f26e74bb'
VERSION = '23.1.3'

def fail!(message)
  abort "build-llvm-config: #{message}"
end

def capture(*command)
  output, error, status = Open3.capture3(*command)
  fail!("#{Shellwords.join(command)} failed: #{error.strip}") unless status.success?
  output.strip
end

def cache(path)
  File.readlines(path).each_with_object({}) do |line, result|
    match = line.match(/\A([^#\/][^:=]*):[^=]+=(.*)\n?\z/)
    result[match[1]] = match[2].strip if match
  end
end

def definitions(path)
  File.readlines(path).each_with_object({}) do |line, result|
    match = line.match(/\A#define ([A-Z][A-Z0-9_]*) (.+)\n?\z/)
    result[match[1]] = match[2].strip if match
  end
end

def string(defs, key)
  JSON.parse(defs.fetch(key))
rescue KeyError, JSON::ParserError
  fail!("missing or unsupported C string #{key}")
end

def replace_once(text, old, replacement)
  fail!("upstream context changed: #{old.lines.first.strip}") unless text.scan(old).length == 1
  text.sub(old, replacement)
end

unless ARGV.length == 6
  fail!('usage: build-llvm-config.rb LLVM_SOURCE TARGET_BUILD NATIVE_BUILD SYSROOT TARGET_PREFIX NEW_WORK')
end
source, target, native, sysroot, prefix = ARGV.first(5).map do |path|
  fail!("expected existing absolute directory: #{path}") unless path.start_with?('/') && File.directory?(path)
  resolved = File.realpath(path)
  fail!("whitespace/control characters are unsupported in input paths: #{path}") if resolved.match?(/[\s\x00-\x1f]/)
  resolved
end
work = File.expand_path(ARGV.last)
fail!('NEW_WORK must be absolute and absent') unless ARGV.last.start_with?('/') && !File.exist?(work)
fail!('NEW_WORK may not be inside an input tree') if [source, target, native, sysroot, prefix].any? { |p| work.start_with?(p + '/') }
fail!('NEW_WORK may not contain whitespace/control characters') if work.match?(/[\s\x00-\x1f]/)

cpp = "#{source}/tools/llvm-config/llvm-config.cpp"
fail!('upstream llvm-config.cpp differs from LLVM 23.1.3') unless File.file?(cpp) && Digest::SHA256.file(cpp).hexdigest == UPSTREAM_SHA256
required = [cpp]
[target, native].each do |build|
  required.concat(%w[CMakeCache.txt include/llvm/Config/llvm-config.h include/llvm/Config/config.h include/llvm/Config/abi-breaking.h].map { |p| "#{build}/#{p}" })
end
required.concat(%w[BuildVariables.inc LibraryDependencies.inc ExtensionDependencies.inc].map { |p| "#{target}/tools/llvm-config/#{p}" })
required.each { |p| fail!("missing input: #{p}") unless File.file?(p) }
initial_hashes = required.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
tc, nc = cache("#{target}/CMakeCache.txt"), cache("#{native}/CMakeCache.txt")
td, nd = [target, native].map { |p| definitions("#{p}/include/llvm/Config/llvm-config.h") }
target_config = definitions("#{target}/include/llvm/Config/config.h")
vars = definitions("#{target}/tools/llvm-config/BuildVariables.inc")
fail!('target must be configured for NetBSD/aarch64 or NetBSD/x86_64') unless tc['CMAKE_SYSTEM_NAME'] == 'NetBSD' && %w[aarch64 x86_64].include?(tc['CMAKE_SYSTEM_PROCESSOR'])
fail!('supplied sysroot differs from the target configuration') unless tc['CMAKE_SYSROOT'] && File.directory?(tc['CMAKE_SYSROOT']) && File.realpath(tc['CMAKE_SYSROOT']) == sysroot
fail!('target and native LLVM versions must both be 23.1.3') unless [td, nd].all? { |d| string(d, 'LLVM_VERSION_STRING') == VERSION }
fail!('target PACKAGE_VERSION disagrees with LLVM_VERSION_STRING') unless string(target_config, 'PACKAGE_VERSION') == string(td, 'LLVM_VERSION_STRING')
fail!('native source does not match the supplied source tree') unless File.realpath(nc.fetch('CMAKE_HOME_DIRECTORY')) == source
fail!('target object root does not match TARGET_BUILD') unless string(vars, 'LLVM_OBJ_ROOT') == target
fail!('target source root does not match its CMake cache') unless string(vars, 'LLVM_SRC_ROOT') == tc['CMAKE_HOME_DIRECTORY']
target_cpp = "#{tc.fetch('CMAKE_HOME_DIRECTORY')}/tools/llvm-config/llvm-config.cpp"
fail!('target llvm-config source differs from the pinned upstream source') unless File.file?(target_cpp) && Digest::SHA256.file(target_cpp).hexdigest == UPSTREAM_SHA256
required << target_cpp
initial_hashes[target_cpp] = Digest::SHA256.file(target_cpp).hexdigest
%w[LLVM_ENABLE_DYLIB LLVM_LINK_DYLIB LLVM_HAS_RTTI].each do |key|
  fail!("target requires #{key}=1") unless vars[key] == '1'
end
fail!('target shared LLVM/RTTI cache disagrees with generated metadata') unless %w[LLVM_BUILD_LLVM_DYLIB LLVM_LINK_LLVM_DYLIB LLVM_ENABLE_RTTI].all? { |k| tc[k] == 'ON' }
fail!('only the canonical /usr/pkg install layout is supported') unless tc['CMAKE_INSTALL_PREFIX'] == '/usr/pkg' && string(vars, 'LLVM_INSTALL_INCLUDEDIR') == 'include' && string(vars, 'LLVM_LIBDIR_SUFFIX').empty?
fail!('unsupported target assertion mode') unless %w[ON OFF].include?(tc['LLVM_ENABLE_ASSERTIONS'])
fail!('native assertion mode must be explicit') unless %w[ON OFF].include?(nc['LLVM_ENABLE_ASSERTIONS'])
components = File.read("#{target}/tools/llvm-config/LibraryDependencies.inc")
begin
  target_spec = EmberGraphicsLLVM.validate(tc, td, components)
rescue ArgumentError => error
  fail!(error.message)
end

# An installed-layout prefix must be the actual output of this target build.
# Development-tree mode remains available for metadata inspection before link.
target_library_hash = nil
library_proof = nil
unless prefix == target
  %w[llvm-config.h abi-breaking.h].each do |name|
    staged = "#{prefix}/include/llvm/Config/#{name}"
    generated = "#{target}/include/llvm/Config/#{name}"
    fail!("staged target header missing or mismatched: #{name}") unless File.file?(staged) && File.binread(staged) == File.binread(generated)
    required << staged
    initial_hashes[staged] = Digest::SHA256.file(staged).hexdigest
  end
  library = "#{prefix}/lib/libLLVM-23.so"
  built_library = "#{target}/lib/libLLVM.so"
  fail!('staged shared LLVM or its original target build output is missing') unless File.file?(library) && File.file?(built_library)
  fail!('staged shared LLVM resolves outside the target prefix') unless File.realpath(library).start_with?(prefix + '/lib/')
  header = File.binread(library, 20)
  begin
    EmberGraphicsLLVM.validate_elf(header, target_spec)
  rescue ArgumentError => error
    fail!(error.message)
  end
  target_library_hash = Digest::SHA256.file(library).hexdigest
  built_hash = Digest::SHA256.file(built_library).hexdigest
  library_proof = {method: 'identical', built_library: built_library,
                   built_sha256: built_hash, staged_library: library,
                   staged_sha256: target_library_hash}
  # pkgsrc uses CMake install-strip. Accept only the exact no-argument strip
  # transformation recorded by this build, never an unexplained DSO mismatch.
  if target_library_hash != built_hash
    strip = tc.fetch('CMAKE_STRIP', '')
    fail!('CMAKE_STRIP must be an absolute executable') unless strip.start_with?('/') && File.executable?(strip)
    install_script = "#{target}/tools/llvm-shlib/cmake_install.cmake"
    fail!('missing shared LLVM install script') unless File.file?(install_script)
    script = File.read(install_script)
    installed = '$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/' + File.basename(File.realpath(built_library))
    invocation = "execute_process(COMMAND \"#{strip}\" \"#{installed}\")"
    block = "if(CMAKE_INSTALL_DO_STRIP)\n      #{invocation}\n    endif()"
    install = 'file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE SHARED_LIBRARY FILES "' + File.realpath(built_library) + '")'
    fail!('unsupported shared LLVM install/strip transformation') unless script.scan(block).length == 1 && script.scan(install).length == 1 && script.scan(/execute_process\([^\n]*/).map(&:strip) == [invocation] && !script.match?(/RPATH_(?:CHANGE|REMOVE)/)
    library_proof.merge!(method: 'cmake-install-strip', strip: strip,
                         strip_version: capture(strip, '--version'),
                         install_script: install_script)
    required.concat([strip, install_script])
  end
  required.concat([library, built_library])
  required.each { |p| initial_hashes[p] ||= Digest::SHA256.file(p).hexdigest }
end

host_config = "#{native}/bin/llvm-config"
fail!('missing runnable native llvm-config') unless File.executable?(host_config)
initial_hashes[host_config] = Digest::SHA256.file(host_config).hexdigest
fail!('native llvm-config version mismatch') unless capture(host_config, '--version') == VERSION
fail!('native llvm-config must describe Darwin') unless capture(host_config, '--host-target').include?('darwin')
host_flags = Shellwords.split(capture(host_config, '--cxxflags'))
host_libs = Shellwords.split(capture(host_config, '--link-static', '--libfiles', 'support', 'targetparser'))
expected_libs = %w[LLVMSupport LLVMTargetParser LLVMDemangle].map { |l| "#{native}/lib/lib#{l}.a" }
fail!('native Support library closure differs from the supported minimal closure') unless host_libs.sort == expected_libs.sort
host_system = Shellwords.split(capture(host_config, '--link-static', '--system-libs', 'support', 'targetparser'))
fail!('unexpected native system library requirements') unless host_system == ['-lm']
cxx = nc.fetch('CMAKE_CXX_COMPILER')
fail!('native C++ compiler must be an existing absolute executable') unless cxx.start_with?('/') && File.executable?(cxx)
native_sdk = nc.fetch('CMAKE_OSX_SYSROOT', '')
native_sdk = capture('/usr/bin/xcrun', '--show-sdk-path') if native_sdk.empty?
fail!('native macOS SDK must be an existing absolute directory') unless native_sdk.start_with?('/') && File.directory?(native_sdk)
native_sdk = File.realpath(native_sdk)
host_flags += ['-isysroot', native_sdk]
deployment_target = nc.fetch('CMAKE_OSX_DEPLOYMENT_TARGET', '')
host_flags << "-mmacosx-version-min=#{deployment_target}" unless deployment_target.empty?
required.concat([host_config, cxx] + host_libs)
([cxx] + host_libs).each { |p| initial_hashes[p] = Digest::SHA256.file(p).hexdigest }

# Map target library search paths, never runtime RPATHs. The target prefix's
# libdir is already prepended by upstream llvm-config. Dependencies use sysroot.
original_ldflags = string(vars, 'LLVM_LDFLAGS')
mapped_ldflags = Shellwords.split(original_ldflags).map do |flag|
  if flag.start_with?('-L/')
    path = flag[2..-1]
    if path == sysroot || path.start_with?(sysroot + '/')
      fail!('target LLVM_LDFLAGS leaks CMAKE_SYSROOT; fix target metadata before building this tool')
    elsif path == '/usr/lib' || path.start_with?('/usr/lib/') || path == '/usr/pkg' || path.start_with?('/usr/pkg/') || path == '/lib' || path.start_with?('/lib/')
      "-L#{sysroot}#{path}"
    else
      fail!("unmapped library search path: #{path}")
    end
  elsif flag.start_with?('-L') || flag.match?(/\s/)
    fail!("unsupported target linker flag: #{flag}")
  elsif flag.include?(source) || flag.include?(target) || flag.include?(native) || flag.include?(sysroot)
    fail!("build path outside a library search flag: #{flag}")
  else
    flag
  end
end.join(' ')

FileUtils.mkdir_p("#{work}/metadata")
FileUtils.mkdir_p("#{work}/bin")
if library_proof && library_proof[:method] == 'cmake-install-strip'
  copied = "#{work}/strip-check.so"
  FileUtils.cp(library_proof.fetch(:built_library), copied)
  fail!('shared LLVM copy differs before stripping') unless Digest::SHA256.file(copied).hexdigest == library_proof.fetch(:built_sha256)
  strip_command = [library_proof.fetch(:strip), copied]
  File.write("#{work}/strip.command", Shellwords.join(strip_command) + "\n")
  File.open("#{work}/strip.log", 'w') do |log|
    fail!('target strip failed; see strip.log') unless system(*strip_command, out: log, err: [:child, :out])
  end
  library_proof[:reproduced_sha256] = Digest::SHA256.file(copied).hexdigest
  fail!('staged shared LLVM differs from the reproduced CMake install-strip output') unless library_proof[:reproduced_sha256] == target_library_hash
  FileUtils.rm(copied)
end
%w[BuildVariables.inc LibraryDependencies.inc ExtensionDependencies.inc].each do |name|
  FileUtils.cp("#{target}/tools/llvm-config/#{name}", "#{work}/metadata/#{name}")
end
build_vars = File.read("#{work}/metadata/BuildVariables.inc")
build_vars = replace_once(build_vars, "#define LLVM_LDFLAGS #{vars.fetch('LLVM_LDFLAGS')}", "#define LLVM_LDFLAGS #{JSON.generate(mapped_ldflags)}")
File.write("#{work}/metadata/BuildVariables.inc", build_vars)
# Include all host headers before these report-only replacements. Never compile
# native Support interfaces against a NetBSD platform/ABI configuration header.
report = %w[LLVM_HOST_TRIPLE LLVM_DEFAULT_TARGET_TRIPLE].map { |key| "#undef #{key}\n#define #{key} #{td.fetch(key)}" }.join("\n")
report += "\n#undef PACKAGE_VERSION\n#define PACKAGE_VERSION #{target_config.fetch('PACKAGE_VERSION')}\n"
report += "#define EMBER_TARGET_ASSERTIONS #{tc['LLVM_ENABLE_ASSERTIONS'] == 'ON' ? 1 : 0}\n"
text = File.read(cpp)
text = replace_once(text, "using namespace llvm;", "// EmberBSD: report target facts after parsing coherent native headers.\n#{report}\nusing namespace llvm;")
text = replace_once(text, "CurrentExecPrefix =\n      sys::path::parent_path(sys::path::parent_path(CurrentPath)).str();", "CurrentExecPrefix = #{JSON.generate(prefix)}; // EmberBSD target prefix")
text = replace_once(text, '#if defined(NDEBUG)', '#if !EMBER_TARGET_ASSERTIONS')
File.write("#{work}/llvm-config.cpp", text)
FileUtils.cp(__FILE__, "#{work}/build-llvm-config.rb")
FileUtils.cp(File.join(__dir__, 'llvm-target.rb'), "#{work}/llvm-target.rb")
compile_args = [cxx, *host_flags, '-DLLVM_BUILD_STATIC', '-O2', (nc['LLVM_ENABLE_ASSERTIONS'] == 'OFF' ? '-DNDEBUG' : '-UNDEBUG'), "-I#{work}/metadata", "#{work}/llvm-config.cpp"]
# Discover and hash the exact non-system headers before the compilation. The
# generated metadata is private; all external headers must belong to the
# matching native source/build, never the target platform headers.
dependency_command = [*compile_args, '-MM', '-MT', 'llvm-config', '-MF', "#{work}/llvm-config.d"]
File.write("#{work}/dependencies.command", Shellwords.join(dependency_command) + "\n")
capture(*dependency_command)
dependencies = Shellwords.split(File.read("#{work}/llvm-config.d").gsub("\\\n", ' ').sub(/\Allvm-config:\s*/, ''))
dependencies.each do |path|
  next if path.start_with?(work + '/')
  fail!("unexpected native header dependency: #{path}") unless path.start_with?(source + '/') || path.start_with?(native + '/') || File.realpath(path).start_with?(native_sdk + '/')
  required << path
  initial_hashes[path] ||= Digest::SHA256.file(path).hexdigest
end
command = [*compile_args, *host_libs, *host_system, '-o', "#{work}/bin/llvm-config.real"]
File.write("#{work}/compile.command", Shellwords.join(command) + "\n")
File.open("#{work}/compile.log", 'w') { |log| fail!('host llvm-config compilation failed; see compile.log') unless system(*command, out: log, err: [:child, :out]) }
File.write("#{work}/receipt.json", JSON.pretty_generate({version: VERSION, source: source, target_build: target, native_build: native, native_sdk: native_sdk, sysroot: sysroot, target_prefix: prefix, target_triple: string(td, 'LLVM_HOST_TRIPLE'), staged_library_sha256: target_library_hash, library_proof: library_proof, compiler: cxx, compiler_version: capture(cxx, '--version'), original_ldflags: original_ldflags, mapped_ldflags: mapped_ldflags, command: command}) + "\n")
shasum = capture('/usr/bin/which', 'shasum')
fail!('shasum must have an absolute executable path') unless shasum.start_with?('/') && File.executable?(shasum)
File.write("#{work}/bin/llvm-config", <<~SH)
  #!/bin/sh
  # SPDX-License-Identifier: BSD-2-Clause
  # Integrity guard only; all query handling is upstream llvm-config.
  set -eu
  base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
  cd "$base"
  #{Shellwords.escape(shasum)} -a 256 -c inputs.sha256 > /dev/null || {
      echo 'llvm-config: input receipt changed; rebuild metadata tool' >&2
      exit 1
  }
  exec "$base/bin/llvm-config.real" "$@"
SH
File.chmod(0755, "#{work}/bin/llvm-config")
local_inputs = %w[metadata/BuildVariables.inc metadata/LibraryDependencies.inc metadata/ExtensionDependencies.inc llvm-config.cpp build-llvm-config.rb llvm-target.rb llvm-config.d dependencies.command compile.command receipt.json bin/llvm-config.real bin/llvm-config]
local_inputs += %w[strip.command strip.log] if library_proof && library_proof[:method] == 'cmake-install-strip'
required.uniq.each do |p|
  fail!("input changed during compilation: #{p}; discard NEW_WORK") unless Digest::SHA256.file(p).hexdigest == initial_hashes.fetch(p)
end
manifest = required.uniq.map { |p| "#{initial_hashes.fetch(p)}  #{p}\n" }
manifest += local_inputs.map { |p| "#{Digest::SHA256.file("#{work}/#{p}").hexdigest}  #{p}\n" }
File.write("#{work}/inputs.sha256", manifest.join)
puts "#{work}/bin/llvm-config"
