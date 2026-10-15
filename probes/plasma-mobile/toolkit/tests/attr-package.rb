#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check the packaged attr manual aliases.
require 'digest'
require 'open3'
require 'tmpdir'

abort 'Usage: attr-package.rb ARCHIVE' unless ARGV.length == 1
archive = File.expand_path(ARGV.first)
tar = ENV.fetch('BSDTAR', 'bsdtar')
def run!(*command)
  output, error, status = Open3.capture3(*command)
  raise "Command failed: #{command.inspect}\n#{output}#{error}" unless status.success?
  output
end
begin
  contents = run!(tar, '-xOf', archive, '+CONTENTS')
  records = {}
  entry = nil
  contents.each_line(chomp: true) do |line|
    if line.start_with?('@comment MD5:', '@comment Symlink:')
      records[entry] = line.delete_prefix('@comment ') if entry
    elsif !line.start_with?('@')
      entry = line
      raise "Duplicate payload entry: #{entry}" if records.key?(entry)
      records[entry] = nil
    end
  end
  names = %w[get set].flat_map { |op| ["man/man3/attr_#{op}f.3", "man/man3/attr_attr_#{op}.3"] }
  Dir.mktmpdir('attr-package-') do |directory|
    run!(tar, '-xf', archive, '-C', directory, *names)
    %w[get set].each do |op|
      member = "man/man3/attr_#{op}f.3"
      target = "attr_attr_#{op}.3"
      path = File.join(directory, member)
      raise "Invalid manual alias: #{member}" unless File.symlink?(path) && File.readlink(path) == target
      raise "Alias metadata mismatch: #{member}" unless records[member] == "Symlink:#{target}"
      page = "man/man3/#{target}"
      path = File.join(directory, page)
      raise "Missing regular manual page: #{page}" unless File.file?(path) && !File.symlink?(path)
      raise "Manual page metadata mismatch: #{page}" unless records[page] == "MD5:#{Digest::MD5.file(path).hexdigest}"
    end
  end
  puts "PASS: attr manual aliases and payload metadata: #{Digest::SHA256.file(archive).hexdigest}"
rescue StandardError => error
  warn error.message
  exit 1
end
