#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Read-only resource validation; no guest launch.
require_relative 'resources'
checks = 0
abort 'Default RAM changed' unless QueryVmResources.ram_mib == 1024
checks += 1
[1024, 4096, 8192].each do |value|
  [value, value.to_s].each do |input|
    abort 'Valid RAM rejected or altered' unless QueryVmResources.ram_mib(input) == value
    checks += 1
  end
end
[nil, true, false, 1024.0, 1023, 8193, -1, 0, '', ' ', '1023', '8193',
 '4096.0', '1_024', '+1024', '-1024', ' 1024', "1024\n", '4096m'].each do |input|
  begin
    QueryVmResources.ram_mib(input)
  rescue ArgumentError => error
    raise unless error.message == 'RAM must be an integer from 1024 to 8192 MiB'
    checks += 1
    next
  end
  abort "Invalid RAM accepted: #{input.inspect}"
end
puts "PASS: #{checks} resource checks; no filesystem mutation or guest execution"
