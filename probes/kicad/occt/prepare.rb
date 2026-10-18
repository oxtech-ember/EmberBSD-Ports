#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Prepare pinned, patched OCCT source.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'usage: prepare.rb ARCHIVE NEW_SOURCE' unless ARGV.size == 2
archive, destination = ARGV.map { |p| File.expand_path(p) }
abort 'source destination exists' if File.exist?(destination) || File.symlink?(destination)
metadata = JSON.parse(File.read(File.join(__dir__, 'source.json')))
abort 'archive hash mismatch' unless Digest::SHA256.file(archive).hexdigest == metadata.fetch('sha256')
patches = metadata.fetch('patches').map do |entry|
  path = File.join(__dir__, entry.fetch('path'))
  abort "patch hash mismatch: #{path}" unless Digest::SHA256.file(path).hexdigest == entry.fetch('sha256')
  path
end
FileUtils.mkdir_p(destination)
commands = [['tar', '-xzf', archive, '--strip-components=1', '-C', destination]]
patches.each { |path| commands << ['patch', '--batch', '--fuzz=0', '-p1', '-d', destination, '-i', path] }
commands.each do |command|
  out, err, status = Open3.capture3(*command)
  $stdout.write(out)
  $stderr.write(err)
  abort "source preparation failed: #{status.exitstatus}" unless status.success?
end
File.write(destination + '/emberbsd-source.json', JSON.pretty_generate(metadata) + "\n")
puts "Prepared OCCT #{metadata.fetch('version')}: #{destination}"
