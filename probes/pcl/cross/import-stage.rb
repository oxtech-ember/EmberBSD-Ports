#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Add package files after a complete collision check.
require 'digest'
require 'fileutils'
abort 'Usage: import-stage.rb STAGE_PREFIX SYSROOT_PREFIX' unless ARGV.length == 2
source, destination = ARGV.map { |path| File.realpath(path) }
abort 'Source and destination must differ.' if source == destination
entries = Dir.glob('**/*', File::FNM_DOTMATCH, base: source).sort.reject { |path| path == '.' || path == '..' }
files = entries.reject { |path| File.directory?(File.join(source, path)) && !File.symlink?(File.join(source, path)) }
files.each do |path|
  input = File.join(source, path)
  output = File.join(destination, path)
  parent = File.dirname(output)
  loop do
    abort "Symlink in destination parent: #{parent}" if File.symlink?(parent)
    break if parent == destination
    parent = File.dirname(parent)
    abort 'Destination parent escaped prefix.' unless parent.start_with?(destination)
  end
  next unless File.exist?(output) || File.symlink?(output)
  identical = if File.symlink?(input)
    File.symlink?(output) && File.readlink(input) == File.readlink(output)
  else
    File.file?(output) && !File.symlink?(output) && Digest::SHA256.file(input).hexdigest == Digest::SHA256.file(output).hexdigest
  end
  abort "Package collision: #{path}" unless identical
end
files.each do |path|
  input = File.join(source, path)
  output = File.join(destination, path)
  next if File.exist?(output) || File.symlink?(output)
  FileUtils.mkdir_p(File.dirname(output))
  FileUtils.copy_entry(input, output, true, false, true)
  puts path
end
