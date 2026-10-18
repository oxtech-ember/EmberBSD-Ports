#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); package-owned public access contract.
require 'json'

abort 'Usage: package-access.rb PREFIX' unless ARGV.size == 1
prefix = File.realpath(ARGV.first)
data = %w[include/spnav.h include/spnav_config.h include/spnav_magellan.h lib/libspnav.a share/pkgconfig/spnav.pc share/licenses/libspnav/LICENSE]
files = data + ['lib/libspnav.so.0.4']
directories = %w[include lib share share/pkgconfig share/licenses share/licenses/libspnav]
observed = {}
files.each do |name|
  path = prefix + '/' + name
  abort 'Expected a regular package file: ' + name unless File.file?(path) && !File.symlink?(path)
  mode = File.stat(path).mode & 07777
  observed[name] = mode
  expected = name.end_with?('.so.0.4') ? 0755 : 0644
  abort 'Incorrect public file mode: ' + name unless mode == expected
end
directories.each do |name|
  path = prefix + '/' + name
  abort 'Expected a public package directory: ' + name unless File.directory?(path) && !File.symlink?(path)
  mode = File.stat(path).mode & 07777
  observed[name + '/'] = mode
  abort 'Public directory is not traversable: ' + name unless (mode & 0555) == 0555
end
puts JSON.pretty_generate({ scope: 'Actual package-owned file modes and public directory traversal bits. Private ancestors and execution under a different uid are separate checks.', modes: observed })
