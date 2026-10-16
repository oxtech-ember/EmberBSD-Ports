#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), link real consumers against staged shared LLVM.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: build-llvm-api-tests.rb CROSS_TOOLS SYSROOT HOST_LLVM_CONFIG NEW_WORK' unless ARGV.length == 4
tools, sysroot, config = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be a new absolute path' unless ARGV.last.start_with?('/') && !File.exist?(work)
owner = File.dirname(File.realpath(__FILE__))

def query(*command)
  out, err, status = Open3.capture3(*command)
  abort "failed: #{Shellwords.join(command)}\n#{err}" unless status.success?
  out.strip
end

def run(log, *command)
  File.write(log + '.command', Shellwords.join(command) + "\n")
  out, err, status = Open3.capture3(*command)
  File.write(log, out + err)
  abort "command failed: #{log}" unless status.success?
end

prefix = query(config, '--prefix')
metadata_receipt = "#{File.dirname(File.dirname(config))}/receipt.json"
metadata = JSON.parse(File.read(metadata_receipt))
abort 'require a validated staged target prefix and matching sysroot' unless prefix.start_with?('/') && File.directory?(prefix) && metadata.fetch('target_prefix') == prefix && metadata.fetch('sysroot') == sysroot && metadata.fetch('staged_library_sha256', nil)
triple = query(config, '--host-target')
arch = triple[/\A(aarch64|x86_64)-(?:unknown)?-netbsd(?:[0-9]+(?:\.[0-9]+)*)?\z/, 1]
abort 'require staged LLVM 23.1.3 for a supported NetBSD CPU' unless query(config, '--version') == '23.1.3' && arch
elf_machine, elf_label = {'aarch64' => [183, 'AArch64'], 'x86_64' => [62, 'Advanced Micro Devices X86-64']}.fetch(arch)
abort 'LLVM must have shared linkage and RTTI' unless query(config, '--has-rtti') == 'YES' && query(config, '--link-shared', '--shared-mode', 'core', 'bitreader', 'bitwriter', 'orcjit', 'native') == 'shared'
cc, cxx, readelf = %w[gcc g++ readelf].map { |name| "#{tools}/bin/#{arch}--netbsd-#{name}" }
abort 'missing cross compiler or ELF inspector' unless [cc, cxx, readelf].all? { |p| File.executable?(p) }
abort 'unexpected cross compiler target' unless query(cc, '-dumpmachine') == "#{arch}--netbsd"
libraries = Shellwords.split(query(config, '--link-shared', '--libfiles', 'core', 'bitreader', 'bitwriter', 'orcjit', 'native'))
abort 'expected one shared LLVM provider in the target sysroot' unless libraries.length == 1 && libraries[0].start_with?(prefix + '/lib/') && File.file?(libraries[0])
library = libraries[0]
abort 'shared LLVM differs from the metadata tool receipt' unless Digest::SHA256.file(library).hexdigest == metadata.fetch('staged_library_sha256')
dynamic = query(readelf, '-d', library)
soname = dynamic[/\(SONAME\).*\[([^\]]+)\]/, 1]
abort 'unexpected shared LLVM SONAME' unless soname && soname.match?(/\AlibLLVM(?:-23)?\.so(?:\.23(?:\.1(?:\.2)?)?)?\z/)
header = File.binread(library, 20)
abort 'LLVM must be an ELF64 shared library for the selected CPU' unless header.byteslice(0, 6) == "\x7fELF\x02\x01" && header.byteslice(16, 4).unpack('v2') == [3, elf_machine]

source_names = %w[llvm-c-api-test.c llvm-orc-test.cpp run-llvm-api-tests.sh]
inputs = source_names.map { |name| "#{owner}/#{name}" } + [__FILE__, cc, cxx, readelf, config, library, metadata_receipt]
initial = inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
FileUtils.mkdir_p("#{work}/bundle/bin")
FileUtils.mkdir_p("#{work}/bundle/source")
File.write("#{work}/bundle/target-arch.txt", arch + "\n")
source_names.first(2).each { |name| FileUtils.cp("#{owner}/#{name}", "#{work}/bundle/source/#{name}") }
FileUtils.cp("#{owner}/run-llvm-api-tests.sh", "#{work}/bundle/run-llvm-api-tests.sh")
File.chmod(0755, "#{work}/bundle/run-llvm-api-tests.sh")

link = Shellwords.split(query(config, '--ldflags')) + Shellwords.split(query(config, '--link-shared', '--libs', '--system-libs', 'core', 'bitreader', 'bitwriter', 'orcjit', 'native'))
link += ["-Wl,-rpath-link,#{prefix}/lib", "-Wl,-rpath-link,#{sysroot}/usr/pkg/lib", "-Wl,-rpath-link,#{sysroot}/usr/pkg/gcc16/lib", '-Wl,-rpath,/usr/pkg/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib']
%w[llvm-c-api-test llvm-orc-test].each do |name|
  is_c = name == 'llvm-c-api-test'
  flags = Shellwords.split(query(config, is_c ? '--cflags' : '--cxxflags'))
  # LLVM's public headers are external headers, but keep their actual target flags.
  flags = flags.flat_map { |v| v == "-I#{prefix}/include" ? ['-isystem', "#{prefix}/include"] : [v] }
  flags << '-std=c11' if is_c
  source = "#{work}/bundle/source/#{name}.#{is_c ? 'c' : 'cpp'}"
  binary = "#{work}/bundle/bin/#{name}"
  run("#{work}/#{name}.build.log", is_c ? cc : cxx, "--sysroot=#{sysroot}", "-B#{sysroot}/usr/pkg/gcc16/lib/gcc/#{arch}--netbsd/16.2.0/", '-O2', '-Wall', '-Wextra', '-Werror', *flags, source, *link, '-o', binary)
  run("#{work}/#{name}.elf.log", readelf, '-h', '-d', binary)
  elf = File.read("#{work}/#{name}.elf.log")
  abort "#{name} is not linked to the selected shared LLVM" unless elf.include?("[#{soname}]") && elf.include?(elf_label)
  abort "#{name} leaks a build directory in dynamic metadata" if [prefix, sysroot, work].any? { |path| elf.include?(path) }
end

File.write("#{work}/bundle/runtime-library.sha256", "#{initial.fetch(library)}  /usr/pkg/lib/#{soname}\n")
File.write("#{work}/receipt.json", JSON.pretty_generate({compiler: cc, compiler_version: query(cc, '--version'), cxx: cxx, sysroot: sysroot, llvm_config: config, llvm_soname: soname, llvm_library_sha256: initial.fetch(library), sources: initial}) + "\n")
inputs.each { |p| abort "input changed during build: #{p}" unless Digest::SHA256.file(p).hexdigest == initial.fetch(p) }
File.write("#{work}/inputs.sha256", initial.map { |p, sha| "#{sha}  #{p}\n" }.join)
artifacts = Dir.glob("#{work}/bundle/**/*").select { |p| File.file?(p) }.sort
File.write("#{work}/bundle/artifacts.sha256", artifacts.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(work + '/bundle/')}\n" }.join)
archive = "#{work}/llvm-api-tests.tar.gz"
abort 'archive creation failed' unless system({'COPYFILE_DISABLE' => '1'}, 'tar', '--no-xattrs', '--exclude', '._*', '-czf', archive, '-C', "#{work}/bundle", '.')
puts "#{Digest::SHA256.file(archive).hexdigest}  #{archive}"
