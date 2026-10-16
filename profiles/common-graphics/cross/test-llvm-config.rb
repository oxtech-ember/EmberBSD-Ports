#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise real metadata and refusal paths.
require 'fileutils'
require 'digest'
require 'json'
require 'open3'
require 'tmpdir'
require_relative 'llvm-target'

abort 'usage: test-llvm-config.rb COMPLETED_WORK' unless ARGV.length == 1
work = File.realpath(ARGV.fetch(0))
receipt = JSON.parse(File.read("#{work}/receipt.json"))
target_spec = EmberGraphicsLLVM.for_triple(receipt.fetch('target_triple'))
tool = "#{work}/bin/llvm-config"
builder = File.join(__dir__, 'build-llvm-config.rb')

def check(name)
  abort "FAIL: #{name}" unless yield
  puts "PASS: #{name}"
end

def query(tool, *args)
  Open3.capture3(tool, *args)
end

check('actual upstream tool reports target version/triple/RTTI/assertions') do
  out, _, status = query(tool, '--version', '--host-target', '--has-rtti', '--assertion-mode')
  status.success? && out == "23.1.3\n#{target_spec.fetch(:processor)}-unknown-netbsd\nYES\nOFF\n"
end
check('target component graph includes the selected backend and ORC') do
  out, _, status = query(tool, '--components')
  required = target_spec.fetch(:processor) == 'aarch64' ? %w[aarch64 amdgpu riscv x86 xtensa orcjit jitlink native] : %w[x86 orcjit jitlink native]
  status.success? && required.all? { |c| out.split.include?(c) }
end
check('compiler flags preserve the target C++ ABI') do
  out, _, status = query(tool, '--cxxflags')
  status.success? && out.include?('-D_GLIBCXX_USE_CXX11_ABI=1') && !out.include?('-fno-rtti') && !out.include?(receipt.fetch('native_build'))
end
check('search paths use target sysroot while runtime paths stay target paths') do
  out, _, status = query(tool, '--ldflags')
  status.success? && out.include?("-L#{receipt.fetch('sysroot')}/usr/lib") && out.include?('-Wl,-R/usr/lib') && !out.match?(/(?:^| )-L\/usr\//) && !out.include?('darwin')
end
check('upstream rejects an unknown component') do
  _, err, status = query(tool, '--link-static', '--libs', 'ember_nonexistent_component')
  !status.success? && err.include?('unknown component')
end

Dir.mktmpdir('ember-llvm-config-tests-') do |tmp|
  tmp = File.realpath(tmp)
  %w[metadata/BuildVariables.inc bin/llvm-config.real].each_with_index do |file, i|
    clone = "#{tmp}/changed-#{i}"
    FileUtils.cp_r(work, clone)
    File.open("#{clone}/#{file}", 'a') { |f| f.puts('changed input') }
    check("rejects modified #{file} before query execution") do
      out, err, status = query("#{clone}/bin/llvm-config", '--version')
      !status.success? && out.empty? && err.include?('input receipt changed')
    end
  end
  check('rejects native Darwin metadata as target input') do
    _, err, status = Open3.capture3('ruby', builder, receipt.fetch('source'), receipt.fetch('native_build'), receipt.fetch('native_build'), receipt.fetch('sysroot'), receipt.fetch('target_prefix'), "#{tmp}/wrong-target")
    !status.success? && err.include?('target must be configured for NetBSD/aarch64')
  end
  check('rejects a native prefix substituted for the target payload') do
    _, err, status = Open3.capture3('ruby', builder, receipt.fetch('source'), receipt.fetch('target_build'), receipt.fetch('native_build'), receipt.fetch('sysroot'), receipt.fetch('native_build'), "#{tmp}/wrong-prefix")
    !status.success? && err.include?('staged target header missing or mismatched')
  end
  if receipt.fetch('target_prefix') != receipt.fetch('target_build')
    proof = receipt.fetch('library_proof')
    check('staged shared library has a reproducible build-output identity') do
      actual = Digest::SHA256.file(proof.fetch('staged_library')).hexdigest
      actual == proof.fetch('staged_sha256') &&
        actual == proof.fetch(proof.fetch('method') == 'identical' ? 'built_sha256' : 'reproduced_sha256')
    end
    changed_prefix = "#{tmp}/changed-prefix"
    FileUtils.mkdir_p("#{changed_prefix}/include/llvm/Config")
    FileUtils.mkdir_p("#{changed_prefix}/lib")
    %w[llvm-config.h abi-breaking.h].each do |name|
      FileUtils.cp("#{receipt.fetch('target_prefix')}/include/llvm/Config/#{name}", "#{changed_prefix}/include/llvm/Config/#{name}")
    end
    FileUtils.cp(proof.fetch('staged_library'), "#{changed_prefix}/lib/libLLVM-23.so")
    File.open("#{changed_prefix}/lib/libLLVM-23.so", 'ab') { |f| f.write('changed staged payload') }
    check('rejects a changed staged shared library after exact strip reproduction') do
      _, err, status = Open3.capture3('ruby', builder, receipt.fetch('source'), receipt.fetch('target_build'), receipt.fetch('native_build'), receipt.fetch('sysroot'), changed_prefix, "#{tmp}/wrong-library")
      !status.success? && err.include?('differs from the reproduced CMake install-strip output')
    end
  end
  changed_source = "#{tmp}/source"
  FileUtils.mkdir_p("#{changed_source}/tools/llvm-config")
  File.write("#{changed_source}/tools/llvm-config/llvm-config.cpp", File.read("#{receipt.fetch('source')}/tools/llvm-config/llvm-config.cpp") + "\n// changed upstream input\n")
  check('rejects changed upstream llvm-config source') do
    _, err, status = Open3.capture3('ruby', builder, changed_source, receipt.fetch('target_build'), receipt.fetch('native_build'), receipt.fetch('sysroot'), receipt.fetch('target_prefix'), "#{tmp}/wrong-source")
    !status.success? && err.include?('differs from LLVM 23.1.3')
  end
  wrong_metadata = "#{tmp}/leaked-target"
  %w[CMakeCache.txt include/llvm/Config/llvm-config.h include/llvm/Config/config.h include/llvm/Config/abi-breaking.h tools/llvm-config/BuildVariables.inc tools/llvm-config/LibraryDependencies.inc tools/llvm-config/ExtensionDependencies.inc].each do |name|
    FileUtils.mkdir_p(File.dirname("#{wrong_metadata}/#{name}"))
    FileUtils.cp("#{receipt.fetch('target_build')}/#{name}", "#{wrong_metadata}/#{name}")
  end
  variables = "#{wrong_metadata}/tools/llvm-config/BuildVariables.inc"
  contents = File.read(variables)
  contents.sub!(/^#define LLVM_OBJ_ROOT .*$/, "#define LLVM_OBJ_ROOT #{JSON.generate(wrong_metadata)}")
  contents.sub!(/^#define LLVM_LDFLAGS .*$/, "#define LLVM_LDFLAGS #{JSON.generate('-L' + receipt.fetch('sysroot') + '/usr/pkg/lib')}")
  File.write(variables, contents)
  check('rejects private sysroot leaked into target metadata') do
    _, err, status = Open3.capture3('ruby', builder, receipt.fetch('source'), wrong_metadata, receipt.fetch('native_build'), receipt.fetch('sysroot'), wrong_metadata, "#{tmp}/wrong-metadata")
    !status.success? && err.include?('LLVM_LDFLAGS leaks CMAKE_SYSROOT')
  end
  if receipt.fetch('library_proof', nil)&.fetch('method') == 'cmake-install-strip'
    contents.sub!(/^#define LLVM_LDFLAGS .*$/, "#define LLVM_LDFLAGS #{JSON.generate(receipt.fetch('original_ldflags'))}")
    File.write(variables, contents)
    cache_path = "#{wrong_metadata}/CMakeCache.txt"
    File.write(cache_path, File.read(cache_path).sub(/^CMAKE_STRIP:FILEPATH=.*$/, 'CMAKE_STRIP:FILEPATH=/usr/bin/true'))
    FileUtils.mkdir_p("#{wrong_metadata}/tools/llvm-shlib")
    FileUtils.cp(receipt.fetch('library_proof').fetch('install_script'), "#{wrong_metadata}/tools/llvm-shlib/cmake_install.cmake")
    FileUtils.mkdir_p("#{wrong_metadata}/lib")
    FileUtils.ln_s(File.realpath(receipt.fetch('library_proof').fetch('built_library')), "#{wrong_metadata}/lib/libLLVM.so")
    check('rejects strip metadata inconsistent with the actual install script') do
      _, err, status = Open3.capture3('ruby', builder, receipt.fetch('source'), wrong_metadata, receipt.fetch('native_build'), receipt.fetch('sysroot'), receipt.fetch('target_prefix'), "#{tmp}/wrong-strip")
      !status.success? && err.include?('unsupported shared LLVM install/strip transformation')
    end
  end
end
if File.exist?("#{receipt.fetch('target_prefix')}/lib/libLLVM-23.so")
  check('upstream accepts the available shared LLVM library') do
    out, _, status = query(tool, '--link-shared', '--shared-mode', 'core', 'executionengine', 'orcjit', 'native')
    status.success? && out == "shared\n"
  end
else
  check('upstream refuses a missing shared LLVM library') do
    _, err, status = query(tool, '--link-shared', '--shared-mode', 'core', 'executionengine', 'orcjit', 'native')
    !status.success? && err.include?('libLLVM-23.so is missing')
  end
end
