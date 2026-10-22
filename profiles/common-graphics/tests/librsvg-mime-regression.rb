#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Reproduce the isolated SVG MIME omission on target.
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'Usage: librsvg-mime-regression.rb PREPARED_CONSUMER NEW_WORK' unless ARGV.size == 2
consumer = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'new absolute work required' unless ARGV[1].start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
source = File.expand_path('librsvg-package.c', __dir__)
text = File.read(source)
normal = 'char *mime_args[] = { "./update-mime-database", "mime", NULL };'
abort 'MIME command changed' unless text.scan(normal).size == 1
# The real packaged utility exits successfully without creating a database.
# Both XDG directories remain private; system MIME data cannot mask the defect.
text = text.sub(normal, 'char *mime_args[] = { "./update-mime-database", "-v", NULL };')
File.write(work + '/missing-mime.c', text)
command = Shellwords.split(File.read(consumer + '/compile.command'))
index = command.index(source) or abort 'unexpected consumer compilation'
abort 'unexpected output option' unless command[-2] == '-o'
command[index] = work + '/missing-mime.c'
command[-1] = work + '/missing-mime'
out, status = Open3.capture2e(*command)
File.write(work + '/compile.log', out)
abort out unless status.success?
runner = File.expand_path('../recipes/devel/gobject-introspection/files/target-query.py', __dir__)
out, status = Open3.capture2e(ENV.fetch('EMBERBSD_GI_PYTHON', 'python3.15'), runner, command[-1])
File.write(work + '/target.log', out)
receipt = out[/target query failed \(1\), (\/[^\n]+)\n/, 1]
abort "wrong failure: #{out}" unless status.exitstatus == 1 && receipt &&
  out.include?('FAIL: dynamic GdkPixbuf SVG loader') &&
  out.include?('(gdk-pixbuf-error-quark:3)')
abort 'remote cleanup failed' unless File.read(receipt + '/cleanup.log').strip == '0'
puts 'PASS: omitting only MIME generation reproduces the SVG format-detection failure; target cleanup succeeded'
