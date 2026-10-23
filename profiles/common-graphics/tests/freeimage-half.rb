#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real FreeImage source and Imath boundary check.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: freeimage-half.rb ARCHIVE IMATH_PREFIX NEW_WORK' unless ARGV.length == 3
archive, imath, work = ARGV.map { |p| File.expand_path(p) }
abort 'Output exists.' if File.exist?(work) || File.symlink?(work)
expected = 'dab013044c3d9122b0a93cee7b53a656426bccc571d3d46880dd8d90a10d1968'
abort 'FreeImage source hash differs.' unless Digest::SHA256.file(archive).hexdigest == expected
abort 'Real installed Imath headers and metadata required.' unless File.file?(imath + '/include/Imath/half.h') && File.file?(imath + '/lib/pkgconfig/Imath.pc')
compiler = Shellwords.split(ENV.fetch('CXX'))
abort 'An explicit native CXX command is required.' if compiler.empty?
FileUtils.mkdir_p(work)
records = []
run = lambda do |name, command, success = true, options = {}|
  out, err, status = Open3.capture3(*command, **options)
  File.write(work + '/' + name + '.log', out + err)
  records << { name: name, command: command, exit: status.exitstatus }
  File.write(work + '/commands.json', JSON.pretty_generate(records) + "\n")
  abort "Unexpected #{name} status: #{status.exitstatus}" unless status.success? == success
  out + err
end
version = run.call('compiler', compiler + ['--version'])
abort 'Native GCC16 is required.' unless version.match?(/\b16\.\d+\.\d+/)
run.call('extract', ['tar', '-xzf', archive, '-C', work])
source = work + '/FreeImage-3.19.25'
recipe = File.expand_path('../../../pkgsrc/graphics/freeimage', __dir__)
original = File.binread(source + '/Source/FreeImage/PluginTIFF.cpp')
File.write(source + '/Source/FreeImage/PluginTIFF.cpp', original.delete("\r"))
# Keep the baseline in the same directory so its relative header lookup is real.
FileUtils.cp(source + '/Source/FreeImage/PluginTIFF.cpp', source + '/Source/FreeImage/PluginTIFF-before.cpp')
patches = %w[patch-CMakeLists.txt patch-Source_FreeImage_PluginTIFF.cpp patch-TestAPI_CMakeLists.txt]
patches.each do |name|
  run.call('apply-' + name, ['patch', '--batch', '--fuzz=0', '-p0', '-i', recipe + '/patches/' + name], true, { chdir: source })
end
headers = work + '/core-headers'
FileUtils.mkdir_p(headers)
Dir[source + '/Source/*.h'].each { |p| FileUtils.cp(p, headers) }
flags = ['-std=c++17', '-O2', '-g', '-DFREEIMAGE_SYSTEM_LIBTIFF', '-DFREEIMAGE_SYSTEM_OPENEXR', '-DINCLUDE_LIB_TIFF4',
         '-I' + imath + '/include', '-I' + headers, '-I' + source + '/Source/Metadata',
         '-I' + source + '/Source/FreeImageToolkit', '-I' + source + '/Source/LibTIFF4']
# The TIFF headers are the release's current 4.7.2 headers. This is a translation
# unit check, not an installed TIFF provider or complete FreeImage library test.
%w[before after].each do |mode|
  name = mode == 'before' ? 'PluginTIFF-before.cpp' : 'PluginTIFF.cpp'
  run.call('tiff-' + mode, compiler + flags + ['-MMD', '-MF', work + '/tiff-' + mode + '.d', '-c', source + '/Source/FreeImage/' + name, '-o', work + '/tiff-' + mode + '.o'])
end
before = File.read(work + '/tiff-before.d')
after = File.read(work + '/tiff-after.d')
abort 'Baseline does not use bundled half.' unless before.include?('OpenEXR/Half/half.h')
abort 'Patched TIFF does not use only installed Imath half.' unless after.include?(imath + '/include/Imath/half.h') && !after.include?('OpenEXR/Half/half.h')
contract = File.join(__dir__, 'freeimage-half.cpp')
link = ['-L' + imath + '/lib', '-Wl,-rpath,' + imath + '/lib', '-lImath-3_2']
run.call('bundled-header-link', compiler + ['-std=c++17', '-O2', '-include', source + '/Source/OpenEXR/Half/half.h', contract] + link + ['-o', work + '/bundled-header'])
run.call('bundled-header-run', [work + '/bundled-header'])
run.call('system-half-link', compiler + ['-std=c++17', '-O2', '-g', '-include', imath + '/include/Imath/half.h', contract] + link + ['-o', work + '/system-half'])
closure = run.call('system-half-loader', ['ldd', work + '/system-half'])
loaded = closure[/^\s*libImath-3_2\.so\.30 => (\S+)/, 1]
abort 'The executable does not resolve the selected installed Imath.' unless loaded &&
  File.realpath(loaded).start_with?(File.realpath(imath + '/lib') + '/')
run.call('system-half-run', [work + '/system-half'])
run.call('system-half-memcheck', Shellwords.split(ENV.fetch('VALGRIND', 'valgrind')) + ['--leak-check=full', '--show-leak-kinds=all', '--errors-for-leak-kinds=all', '--error-exitcode=99', work + '/system-half'])
inputs = [archive, contract, imath + '/include/Imath/half.h', imath + '/lib/pkgconfig/Imath.pc'] + patches.map { |p| recipe + '/patches/' + p }
inputs += Dir[imath + '/lib/libImath-3_2.so*'].select { |p| File.file?(p) && !File.symlink?(p) }
File.write(work + '/result.json', JSON.pretty_generate({
  scope: 'Native GCC16 translation units and system Imath half conversions only. No complete codec, package or target runtime acceptance.',
  inputs: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }, commands: records
}) + "\n")
puts 'PASS: real TIFF header selection, equivalent 65536 half values and strict Memcheck.'
