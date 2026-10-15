#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
require 'open3'
output, status = Open3.capture2e(ARGV.fetch(0), '--fail-map')
print output
abort 'Baseline did not expose the exact mmap failure handling defect' unless
  status.exitstatus == 3 && output.lines.map(&:strip).include?('FAIL mapping failure reached mprotect')
