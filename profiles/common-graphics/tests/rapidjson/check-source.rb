#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real source ownership regressions.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort "Usage: #{$PROGRAM_NAME} SOURCE_ARCHIVE NATIVE_GXX GTEST_PREFIX NEW_WORK" unless ARGV.size == 4
archive, compiler, gtest, work = ARGV.map { |p| File.expand_path(p) }
abort 'Expected the pinned RapidJSON source archive' unless
  Digest::SHA256.file(archive).hexdigest == '2d2601a82d2d3b7e143a3c8d43ef616671391034bc46891a9816b79cf2d3e7a8'
abort 'Use an actual native compiler executable' unless File.file?(compiler) && File.executable?(compiler)
version, error, status = Open3.capture3(compiler, '-dumpfullversion')
abort error unless status.success? && version.start_with?('16.')
library = gtest + '/lib/libgtest.a'
abort 'Expected installed GoogleTest headers and native static library' unless
  File.file?(gtest + '/include/gtest/gtest.h') && File.file?(library)
abort 'NEW_WORK already exists' if File.exist?(work) || File.symlink?(work)
Dir.mkdir(work, 0700)
records = []
run = lambda do |name, argv, **options|
  out, err, result = Open3.capture3(*argv, **options)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  records << { name: name, argv: argv, exit: result.exitstatus, signal: result.termsig }
  File.write(work + '/commands.json', JSON.pretty_generate(records) + "\n")
  [out, err, result]
end
original = work + '/original'
patched = work + '/patched'
[original, patched].each do |destination|
  Dir.mkdir(destination)
  _, err, result = run.call(File.basename(destination) + '-extract',
                           ['tar', '-xzf', archive, '--strip-components=1', '-C', destination])
  abort err unless result.success?
end
recipe = File.expand_path('../../../../pkgsrc/textproc/rapidjson', __dir__)
patches = Dir.glob(recipe + '/patches/patch-*').sort
patches.each do |patch|
  _, err, result = run.call(File.basename(patch),
                           ['patch', '--batch', '--fuzz=0', '-p0', '-d', patched, '-i', patch])
  abort err unless result.success?
end
memcheck = ['valgrind', '--error-exitcode=1', '--leak-check=full', '--show-leak-kinds=all',
            '--errors-for-leak-kinds=all', '--track-origins=yes']
%w[pointer owner].each do |test|
  %w[before after after-optimized].each do |variant|
    source = variant == 'before' ? original : patched
    name = test + '-' + variant
    executable = work + '/' + name
    sources = test == 'pointer' ? [File.join(__dir__, 'pointer.cpp')] :
      [patched + '/test/unittest/allocatorstest.cpp', patched + '/test/unittest/unittest.cpp']
    args = [compiler, '-std=c++17', variant == 'after-optimized' ? '-O2' : '-O0', '-g',
            '-Wall', '-Wextra', '-Werror', '-DRAPIDJSON_HAS_STDSTRING=1', '-I' + source + '/include',
            '-I' + gtest + '/include', *sources]
    args.concat([library, '-pthread']) if test == 'owner'
    args.concat(['-o', executable])
    _, err, result = run.call(name + '-compile', args)
    abort err unless result.success?
    command = [*memcheck, executable]
    command << '--gtest_filter=Allocator.SharedBufferOwner' if test == 'owner'
    out, err, result = run.call(name, command)
    if variant != 'before'
      abort "#{name} failed" unless result.success? && err.include?('in use at exit: 0 bytes in 0 blocks') &&
        err.include?('ERROR SUMMARY: 0 errors')
    elsif test == 'pointer'
      abort 'Missing the original null-name-buffer failure' unless !result.success? &&
        err.include?('Invalid read') && err.include?('Address 0x0')
    else
      abort 'Missing the original shared-owner leak' unless result.exitstatus == 1 &&
        out.include?('[  FAILED  ] Allocator.SharedBufferOwner') &&
        err.include?('definitely lost: 1 bytes in 1 blocks')
    end
  end
end
File.write(work + '/result.json', JSON.pretty_generate({
  result: 'PASS', compiler_version: version.strip,
  source_sha256: Digest::SHA256.file(archive).hexdigest,
  gtest_archive_sha256: Digest::SHA256.file(library).hexdigest,
  input_sha256: [compiler, __FILE__, File.join(__dir__, 'pointer.cpp'),
                 gtest + '/include/gtest/gtest.h', *patches].to_h { |p| [File.realpath(p), Digest::SHA256.file(p).hexdigest] },
  scope: 'Matched -O0 native source ownership regressions plus repaired -O2 controls; no target or whole-package acceptance.'
}) + "\n")
puts 'PASS: actual pointer crash and shared-owner leak regressions, strict Memcheck after repair.'
