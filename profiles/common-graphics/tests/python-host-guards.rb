#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Execute the actual recipe host Python guards.
require 'open3'

abort 'usage: python-host-guards.rb HOST_PYTHON315 OLDER_HOST_PYTHON NEW_WORK' unless ARGV.length == 3
selected, older = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
[[selected, /\APython 3\.15\./], [older, /\APython 3\.14\./]].each do |path, expected|
  out, status = Open3.capture2e(path, '--version')
  abort 'Unexpected actual interpreter: ' + out unless status.success? && out.match?(expected)
end
root = File.expand_path('..', __dir__)
failures = []
{'libdrm' => 'x11/libdrm', 'MesaLib' => 'graphics/MesaLib'}.each do |name, recipe|
  text = File.read(root + '/../../pkgsrc/' + recipe + '/Makefile')
  abort 'Recipe does not select Python315: ' + name unless text.match?(/^PYTHON_VERSION_REQD=\s*315$/)
  commands = text.scan(/^\t\$\{TOOL_PYTHONBIN\} -c '([^']+)'$/).flatten
  abort 'Expected exactly one production guard: ' + name unless commands.length == 1
  code = commands.fetch(0)
  File.write(work + '/' + name + '-guard.txt', code + "\n")
  out, status = Open3.capture2e(selected, '-c', code)
  File.write(work + '/' + name + '-selected.log', out)
  if status.success?
    puts "PASS: #{name} production guard accepts actual Python315 with required imports"
  else
    failures << "#{name} rejects the actual selected Python315: #{out}"
  end
  # Old modules need not be installed for a version-refusal control.
  # Execute the exact production predicate with the real older interpreter.
  predicate = code.split(';', 2).fetch(1).strip
  abort 'Unexpected production version predicate: ' + name unless predicate.start_with?('assert sys.version_info[:2]')
  out, status = Open3.capture2e(older, '-c', 'import sys; ' + predicate)
  File.write(work + '/' + name + '-older.log', out)
  if !status.success? && out.include?('AssertionError') && !out.include?('ModuleNotFoundError')
    puts "PASS: #{name} production version predicate rejects actual older Python314"
  else
    failures << "#{name} does not reject actual Python314 by version: #{out}"
  end
end
abort failures.map { |message| 'FAIL: ' + message }.join("\n") unless failures.empty?
puts 'PASS: host guard execution only; no target package build or execution'
