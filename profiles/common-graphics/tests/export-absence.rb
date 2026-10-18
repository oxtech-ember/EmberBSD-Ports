#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual positive-export absence guard.
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: export-absence.rb EXPORT_TEST NEW_WORK' unless ARGV.size == 2
source = File.read(File.realpath(ARGV[0]))
blocks = source.scan(/# BEGIN libspnav-absence-guard\n(.*?)\s*# END libspnav-absence-guard/m)
abort 'Expected one actual absence guard.' unless blocks.size == 1
out = File.expand_path(ARGV[1])
abort 'Output exists.' if File.exist?(out) || File.symlink?(out)
FileUtils.mkdir_p(out)
script = out + '/actual-guard.sh'
File.write(script, "#!/bin/sh\nset -eu\ntree=$1\n" + blocks.first.first + "\n: reached\n")
commands = []
%w[absent regular directory symlink dangling].each do |kind|
  tree = out + '/' + kind
  FileUtils.mkdir_p(tree + '/x11')
  path = tree + '/x11/libspnav'
  case kind
  when 'regular' then File.write(path, 'present')
  when 'directory' then FileUtils.mkdir(path)
  when 'symlink'
    File.write(tree + '/actual', 'present')
    File.symlink('../actual', path)
  when 'dangling' then File.symlink('../missing', path)
  end
  argv = ['sh', script, tree]
  stdout, stderr, status = Open3.capture3(*argv)
  File.write(out + '/' + kind + '.stdout', stdout)
  File.write(out + '/' + kind + '.stderr', stderr)
  commands << {kind: kind, argv: argv, status: status.exitstatus}
  File.write(out + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort 'Actual export guard accepted the wrong path state.' unless status.success? == (kind == 'absent')
end
File.write(out + '/result.json', JSON.pretty_generate({scope: 'Execute the actual positive-export shell guard against absent, regular, directory, symlink and dangling-symlink paths.', commands: commands}) + "\n")
puts 'PASS: actual export guard rejects every present libspnav path.'
