#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Origin: EmberBSD (AI-assisted). Real-TU GCC16 construction regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: ruby check-selector-registry.rb COMPILE_COMMANDS ORIGINAL_SOURCE NEW_OUTPUT' unless ARGV.length == 3
database, original, output = ARGV.map { |path| File.expand_path(path) }
abort 'Preserve the existing output.' if File.exist?(output) || File.symlink?(output)
relative = 'onnxruntime/core/optimizer/matmul_nbits_fusion.cc'
before = File.join(original, relative)
before_header = before.sub(/\.cc\z/, '.h')
# Keep the baseline tied to the pinned 1.31.0 source, not a reduced substitute.
abort 'Expected the unmodified ONNX Runtime 1.31.0 translation unit.' unless
  Digest::SHA256.file(before).hexdigest == '3037464601a801ac8dc9602fdaa0dbd682601471423f3394065dce549c68bc8e'
entries = JSON.parse(File.read(database)).select do |entry|
  File.expand_path(entry.fetch('file'), entry.fetch('directory')).end_with?("/#{relative}")
end
abort 'Expected one actual target compilation entry.' unless entries.length == 1
entry = entries.first
directory = File.expand_path(entry.fetch('directory'))
source = File.expand_path(entry.fetch('file'), directory)
abort 'The class declaration changed.' unless
  File.binread(before_header) == File.binread(source.sub(/\.cc\z/, '.h'))
base = entry['arguments'] || Shellwords.split(entry.fetch('command'))
abort 'Expected the real AArch64 GCC compiler.' unless File.basename(base.first) == 'aarch64--netbsd-g++'
version, status = Open3.capture2e(base.first, '-dumpfullversion')
abort 'Expected GCC 16.2.0.' unless status.success? && version.strip == '16.2.0'
abort 'Expected production -O2 and -Werror.' unless base.include?('-O2') && base.include?('-Werror')
source_indices = base.each_index.select { |index| File.expand_path(base[index], directory) == source }
abort 'Expected one real source argument.' unless source_indices.length == 1
patch = File.expand_path('../../pkgsrc/local-ai/onnxruntime/patches/patch-static-selector-registry', __dir__)
FileUtils.mkdir_p(output)
FileUtils.cp(before, File.join(output, 'before.cc'))
FileUtils.cp(before, File.join(output, 'after.cc'))
abort 'The canonical patch did not apply exactly.' unless
  system(ENV.fetch('PATCH', 'patch'), '-f', '-N', '-F', '0', File.join(output, 'after.cc'),
         in: patch, out: File.join(output, 'patch.log'), err: [:child, :out])
abort 'The real target source differs from the canonical patch result.' unless
  File.binread(File.join(output, 'after.cc')) == File.binread(source)
results = { 'compiler_version' => version.strip,
            'class_header_sha256' => Digest::SHA256.file(before_header).hexdigest,
            'patch_sha256' => Digest::SHA256.file(patch).hexdigest }
%w[before after].each do |variant|
  copy = File.join(output, "#{variant}.cc")
  object = File.join(output, "#{variant}.o")
  args = base.dup
  args[source_indices.first] = copy
  %w[-o -MF -MT -MQ].each do |option|
    index = args.index(option)
    next unless index
    args[index + 1] = option == '-MF' ? "#{object}.d" : object
  end
  File.write(File.join(output, "#{variant}-command.json"), JSON.pretty_generate(args) + "\n")
  success = system(*args, chdir: directory, out: File.join(output, "#{variant}-compile.log"), err: [:child, :out])
  results[variant] = { 'exit_status' => $?.exitstatus, 'success' => success,
                       'source_sha256' => Digest::SHA256.file(copy).hexdigest }
end
diagnostic = File.read(File.join(output, 'before-compile.log'))
abort 'The baseline did not reproduce the constructor diagnostic.' unless
  results['before']['success'] == false && diagnostic.include?('maybe-uninitialized') &&
  diagnostic.include?('MatMulNBitsFusion::CreateSelectorActionRegistry() const')
abort 'The patched full translation unit did not compile.' unless results['after']['success']
File.write(File.join(output, 'results.json'), JSON.pretty_generate(results) + "\n")
puts 'PASS real GCC16 AArch64 TU: baseline constructor diagnostic, patched compile, unchanged class declaration'
