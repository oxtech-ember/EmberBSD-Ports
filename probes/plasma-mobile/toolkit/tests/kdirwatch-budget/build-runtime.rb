#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: build-runtime.rb CROSS_TOOLS SYSROOT LLD_SPECS NEW_OUTPUT' unless ARGV.size == 4
tools, sysroot, specs = ARGV.first(3).map { |path| File.realpath(path) }
output = File.expand_path(ARGV.last)
abort 'output must not exist' if File.exist?(output)
cc = tools + '/bin/aarch64--netbsd-g++'
readelf = tools + '/bin/aarch64--netbsd-readelf'
linker = File.read(specs)[/^\*linker:\n([^\n]+)$/, 1]
abort 'missing explicit GCC/LLD tools' unless [cc, readelf, linker].all? { |path| path && File.executable?(path) }
def query(*command)
  out, err, status = Open3.capture3(*command)
  abort err unless status.success?
  out.strip
end
abort 'wrong target' unless query(cc, '-dumpmachine') == 'aarch64--netbsd'
abort 'require GCC16.2' unless query(cc, '-dumpfullversion') == '16.2.0'
linker_version = query(linker, '--version')
abort 'require current LLD23.1.3' unless linker_version.start_with?('LLD 23.1.3 ')
source = __dir__ + '/runtime.cpp'
runtime = __dir__ + '/runtime.sh'
prefix = sysroot + '/usr/pkg'
inputs = [__FILE__, source, runtime, cc, readelf, specs, linker,
          prefix + '/lib/libKF6CoreAddons.so.6', prefix + '/qt6/lib/libQt6Core.so.6',
          prefix + '/include/KF6/KCoreAddons/kdirwatch.h']
hashes = inputs.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] }
FileUtils.mkdir_p(output)
command = [cc, '--sysroot=' + sysroot, '-O2', '-g', '-std=c++20', '-fPIC',
           '-Wall', '-Wextra', '-Werror', '-pthread', '-DQT_CORE_LIB',
           '-I' + prefix + '/include/KF6/KCoreAddons', '-I' + prefix + '/qt6/include',
           '-I' + prefix + '/qt6/include/QtCore', source,
           '-L' + prefix + '/lib', '-L' + prefix + '/qt6/lib', '-L' + prefix + '/gcc16/lib',
           '-lKF6CoreAddons', '-lQt6Core', '-specs=' + specs, '-fno-use-linker-plugin',
           '-Wl,-m,aarch64elf', '-Wl,--dynamic-linker,/libexec/ld.elf_so',
           '-Wl,-rpath-link,' + prefix + '/lib', '-Wl,-rpath-link,' + prefix + '/qt6/lib',
           '-Wl,-rpath-link,' + prefix + '/gcc16/lib', '-Wl,-rpath,/usr/pkg/lib',
           '-Wl,-rpath,/usr/pkg/qt6/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib',
           '-o', output + '/kdirwatch-budget']
out, err, status = Open3.capture3(*command)
File.write(output + '/build.log', command.shelljoin + "\n" + out + err)
File.write(output + '/compile-command.json', JSON.pretty_generate(command) + "\n")
abort 'cross build failed' unless status.success?
binary = output + '/kdirwatch-budget'
header = File.binread(binary, 20)
abort 'not AArch64 ELF64' unless header.byteslice(0, 6) == "\x7fELF\x02\x01" && header.byteslice(18, 2).unpack1('v') == 183
program = query(readelf, '-l', binary)
abort 'wrong interpreter' unless program.include?('Requesting program interpreter: /libexec/ld.elf_so')
comment = query(readelf, '-p', '.comment', binary)
abort 'missing actual LLD evidence' unless comment.include?('Linker: LLD 23.1.3')
File.write(output + '/elf.txt', program + "\n" + query(readelf, '-d', binary) + "\n" + comment)
abort 'inputs changed' unless hashes.all? { |path, hash| Digest::SHA256.file(path).hexdigest == hash }
FileUtils.cp(runtime, output + '/runtime.sh')
File.write(output + '/receipt.json', JSON.pretty_generate({inputs: hashes, compiler: query(cc, '--version'),
  linker: linker_version, binary_sha256: Digest::SHA256.file(binary).hexdigest,
  boundary: 'Cross-built public ABI consumer. Native baseline and candidate execution remain required.'}) + "\n")
puts 'PASS: clean public consumer cross build and actual AArch64/LLD/interpreter checks'
