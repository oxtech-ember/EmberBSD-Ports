#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), finite genuine upstream pixel-copy regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: check-source.rb FREEIMAGE_ARCHIVE NATIVE_GXX NEW_WORK' unless ARGV.size == 3
archive, compiler = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'New absolute output required.' unless ARGV.last.start_with?('/') && !File.exist?(work) && !File.symlink?(work)
abort 'Wrong official FreeImage archive.' unless Digest::SHA256.file(archive).hexdigest == 'dab013044c3d9122b0a93cee7b53a656426bccc571d3d46880dd8d90a10d1968'
Dir.mkdir(work)
commands = []
run = lambda do |label, args, expected = 0|
  out, err, status = Open3.capture3(*args)
  File.write(work + '/' + label + '.stdout', out)
  File.write(work + '/' + label + '.stderr', err)
  commands << {label: label, args: args, status: status.exitstatus, signal: status.termsig}
  File.write(work + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort 'Unexpected result: ' + label unless status.exitstatus == expected && !status.signaled?
  out + err
end
abort 'Native GCC16 is required.' unless run.call('compiler', [compiler, '-dumpfullversion']).start_with?('16.')
triplet = run.call('triplet', [compiler, '-dumpmachine'])
abort 'Use a native compiler.' if triplet.include?('netbsd')
patch = File.expand_path('../../recipes/graphics/freeimage/patches/patch-Source_Utilities.h', __dir__)
fixture = File.join(__dir__, 'pixels.cpp')
sources = {}
%w[before after].each do |variant|
  dir = work + '/' + variant
  Dir.mkdir(dir)
  run.call(variant + '-extract', ['tar', '-xzf', archive, '-C', dir,
    'FreeImage-3.19.25/Source/FreeImage.h', 'FreeImage-3.19.25/Source/Utilities.h'])
  source = dir + '/FreeImage-3.19.25'
  run.call('apply', ['patch', '-d', source, '-p0', '--fuzz=0', '-i', patch]) if variant == 'after'
  utilities = source + '/Source/Utilities.h'
  text = File.binread(utilities)
  pattern = /inline void \nAssignPixel\(BYTE\* dst, const BYTE\* src, unsigned bytesperpixel\) \{.*?\n\}\n/m
  matches = text.scan(pattern)
  abort 'Unexpected source function boundary.' unless matches.size == 1
  # Extract the complete real function so unrelated header-only diagnostics do
  # not obscure the alignment failure. Public byte/word types stay upstream.
  header = dir + '/assign-pixel.hpp'
  File.write(header, "#include <cassert>\n#include <cstring>\n" + matches.first)
  sources[variant] = {utilities_sha256: Digest::SHA256.file(utilities).hexdigest,
                     function_sha256: Digest::SHA256.hexdigest(matches.first)}
  flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-I' + dir, '-I' + source + '/Source']
  binary = dir + '/pixels'
  run.call(variant + '-compile', [compiler] + flags + ['-fsanitize=alignment', '-fno-sanitize-recover=alignment', fixture, '-o', binary])
  result = run.call(variant + '-run', [binary], variant == 'before' ? 1 : 0)
  if variant == 'before'
    abort 'Wrong baseline failure.' unless result.include?('runtime error: load of misaligned address') && result.include?("requires 2 byte alignment")
  else
    abort 'Missing byte/guard oracle.' unless result.include?('PASS: all eight pixel sizes, unaligned storage and exact guards.')
    plain = dir + '/pixels-plain'
    run.call('plain-compile', [compiler] + flags + [fixture, '-o', plain])
    memory = run.call('memcheck', ['valgrind', '--error-exitcode=1', '--leak-check=full', '--show-leak-kinds=all',
      '--errors-for-leak-kinds=all', '--track-origins=yes', plain])
    abort 'Memory result differs.' unless memory.include?('in use at exit: 0 bytes in 0 blocks') && memory.include?('ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 0 from 0)')
  end
end
inputs = [archive, compiler, __FILE__, fixture, patch]
File.write(work + '/result.json', JSON.pretty_generate(scope: 'Exact upstream AssignPixel function and public types; eight pixel sizes and four storage offsets, native alignment sanitizer and strict Memcheck. No complete library or target runtime claim.',
  sources: sources, input_sha256: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }, status: 'PASS') + "\n")
puts 'PASS: genuine misaligned-load baseline and repaired pixel-byte/guard checks.'
