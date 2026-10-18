#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compile the actual exception module with GCC16.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: check-failure-stack.rb ORIGINAL_SOURCE PATCHED_SOURCE GENERATED_HEADERS NATIVE_PREFIX NEW_WORK' unless ARGV.length == 5
original, patched, headers, prefix = ARGV.take(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute output directory.' unless ARGV.last == work && !File.exist?(work) && !File.symlink?(work)
compiler = Shellwords.split(ENV.fetch('CXX', 'g++'))
version, error, status = Open3.capture3(*compiler, '-dumpfullversion')
abort "GCC16 is required: #{error}" unless status.success? && version.start_with?('16.')
library = File.realpath(prefix + '/lib/libTKernel.so')
FileUtils.mkdir_p(work)
records = []
run = lambda do |name, args|
  stdout, stderr, result = Open3.capture3(*args)
  File.write(work + '/' + name + '.stdout', stdout)
  File.write(work + '/' + name + '.stderr', stderr)
  records << { name: name, argv: args, status: result.exitstatus, signal: result.termsig }
  File.write(work + '/commands.json', JSON.pretty_generate(records) + "\n")
  [stdout + stderr, result]
end
flags = %w[-std=c++17 -O1 -g -Wall -Wextra -fsanitize=undefined -fno-sanitize-recover=all]
inputs = []
{ 'before' => original, 'after' => patched }.each do |name, source|
  unit = source + '/src/FoundationClasses/TKernel/Standard/Standard_Failure.cxx'
  inputs << unit
  binary = work + '/' + name
  _, result = run.call(name + '-build', [*compiler, *flags, '-I' + headers, unit,
    File.join(__dir__, 'failure-stack.cxx'), '-L' + prefix + '/lib',
    '-Wl,-rpath,' + prefix + '/lib', '-lTKernel', '-o', binary])
  abort "#{name} build failed." unless result.success?
  cases = name == 'before' ? ['overflow'] : %w[negative zero small below-cap above-cap overflow]
  cases.each do |mode|
    output, result = run.call(name + '-' + mode, [binary, mode])
    if name == 'before'
      abort 'Baseline did not reproduce signed overflow.' unless !result.success? && output.include?('runtime error: signed integer overflow')
    else
      abort "#{mode} failed." unless result.success?
    end
  end
end
File.write(work + '/result.json', JSON.pretty_generate(
  compiler: compiler, compiler_version: version.strip,
  input_sha256: (inputs + [library, File.join(__dir__, 'failure-stack.cxx')]).to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
  helper_library: library,
  scope: 'Actual Standard_Failure module rebuilt with GCC16. Existing native TKernel supplies unchanged helpers; this is not a full GCC16 OCCT build.'
) + "\n")
puts 'PASS: original signed overflow; six patched exception-trace cases.'
