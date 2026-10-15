#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), exercise the installed upstream Mako CLI.
require 'open3'

abort 'usage: template-consumer.rb HOST_PREFIX NEW_WORK' unless ARGV.length == 2
prefix = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'NEW_WORK must be new and absolute' unless ARGV[1].start_with?('/') && !File.exist?(work)
Dir.mkdir(work)
render = "#{prefix}/bin/mako-render-3.14"
abort 'Mako CLI does not select the shared Python 3.15 interpreter' unless File.readlines(render).first.strip == "#!#{prefix}/bin/python3.15"
%w[py314-mako-1.4.3 py314-markupsafe-3.0.4].each do |package|
  out, err, status = Open3.capture3("#{prefix}/sbin/pkg_info", '-K', "#{prefix}/pkgdb", '-e', package)
  abort "missing selected package #{package}: #{err}" unless status.success? && out.strip == package
end
File.write("#{work}/escape.mako", "% for number in range(3):\n${'<β&>' | h}:${number}\n% endfor\n")
out, err, status = Open3.capture3(render, "#{work}/escape.mako")
File.write("#{work}/render.log", out + err)
abort 'Mako/MarkupSafe UTF-8 escape or loop failed' unless status.success? && err.empty? && out == (0..2).map { |n| "&lt;β&amp;&gt;:#{n}\n" }.join
File.write("#{work}/missing.mako", '${ember_missing}' + "\n")
out, err, status = Open3.capture3(render, "#{work}/missing.mako")
File.write("#{work}/missing.log", out + err)
abort 'Mako swallowed an undefined-template-variable failure' unless status.exitstatus == 1 && out.empty? && err.include?('NameError')
puts 'PASS: installed shared Python/Mako/MarkupSafe, UTF-8 escaping, template loop and real error exit 1'
