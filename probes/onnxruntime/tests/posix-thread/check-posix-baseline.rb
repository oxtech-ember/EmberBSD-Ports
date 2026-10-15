#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
abort 'Usage: check-posix-baseline.rb BASELINE_EXECUTABLE' unless ARGV.length == 1
output = IO.popen([File.expand_path(ARGV[0])], err: [:child, :out], &:read)
status = $?
print output
abort "Unexpected baseline exit: #{status}" unless status.exitstatus == 3 && !status.signaled?
expected = [
  /^FAIL default initialized=1 destroyed=0 threw=0 diagnostics_ok=1$/,
  /^FAIL explicit-stack initialized=1 destroyed=0 threw=0 diagnostics_ok=1$/,
  /^FAIL init-failure initialized=0 destroyed=0 threw=1 diagnostics_ok=0$/,
  /^FAIL stack-failure initialized=1 destroyed=0 threw=1 diagnostics_ok=0$/,
  /^FAIL create-failure initialized=1 destroyed=0 threw=1 diagnostics_ok=0$/
]
abort 'Baseline failed for a different reason' unless expected.all? { |pattern| pattern.match?(output) }
puts 'PASS upstream baseline exposes both attribute cleanup and error-code defects'
