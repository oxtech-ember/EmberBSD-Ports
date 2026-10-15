#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
require 'json'
require 'open3'
require 'shellwords'

abort 'usage: mesa-python-guard.rb RECIPE PYTHON SELECTED_VERSION NEW_OUTPUT' unless ARGV.size == 4
recipe, interpreter, version, output = ARGV.map { |value| value.dup }
abort 'invalid selected Python version' unless version.match?(/\A3\.[0-9]+\z/)
abort 'output exists' if File.exist?(output)
line = File.readlines(recipe).find { |entry| entry.include?('import sys, mako, packaging, yaml; assert') }
abort 'missing actual recipe guard' unless line
args = Shellwords.split(line.strip)
abort 'unexpected guard command' unless args[0] == '${TOOL_PYTHONBIN}' && args[1] == '-c' && args.size == 3
code = args[2].gsub('${PYVERSSUFFIX}', version)
baseline = code.sub(/tuple\(map\(int, "[0-9.]+"\.split\("\."\)\)\)/, '(3, 14)')
abort 'missing selected-version comparison' if baseline == code
abort 'this regression requires the current Python 3.15 selection' unless version == '3.15'
cases = [
  ['old-guard-rejects-current-interpreter', baseline, false],
  ['selected-interpreter-and-real-modules', code, true],
  ['mismatched-version-is-rejected', code.sub('"3.15"', '"3.14"'), false]
]
results = cases.map do |name, program, succeeds|
  stdout, stderr, status = Open3.capture3(interpreter, '-c', program)
  valid = status.success? == succeeds && (succeeds || stderr.include?('AssertionError'))
  {name: name, command: [interpreter, '-c', program], status: status.exitstatus,
   stdout: stdout, stderr: stderr, pass: valid}
end
File.write(output, JSON.pretty_generate(results) + "\n")
abort 'Python guard regression failed; see output' unless results.all? { |entry| entry[:pass] }
puts 'PASS: real recipe accepts selected Python and modules, rejects the obsolete or mismatched version'
