#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Query the actual cross recipe and framework.
require 'fileutils'
require 'open3'
abort 'Usage: cross-rcd-path.rb PACKAGE_DIRECTORY MAKECONF NEW_OUTPUT' unless ARGV.length == 3
package, config, output = ARGV.map { |p| File.expand_path(p) }
Dir.mkdir(output)
profile = File.expand_path('../cross/mk.conf', __dir__)
make = ENV.fetch('BMAKE', 'bmake')
query = lambda do |cfg, *overrides|
  args = [make, '-C', package, "MAKECONF=#{cfg}", *overrides]
  %w[RCD_SCRIPTS_DIR SYSCONFBASE INIT_SYSTEM RCD_SCRIPTS].each { |v| args += ['-V', "${#{v}}"] }
  out, err, status = Open3.capture3(*args)
  abort "bmake failed: #{err}" unless status.success?
  out.lines.map(&:strip)
end
actual = query.call(config)
abort "Wrong cross defaults: #{actual.inspect}" unless actual == ['/etc/rc.d', '/usr/pkg/etc', 'rc.d', 'x11_runtime']
override = query.call(config, 'RCD_SCRIPTS_DIR=/etc/custom-rc.d')
abort 'Explicit service directory was lost' unless override == ['/etc/custom-rc.d', *actual[1..-1]]
source = File.read(profile)
old = source.sub(/^RCD_SCRIPTS_DIR\?=\/etc\/rc\.d\n/, '')
abort 'No profile mutation point' if source == old
File.write("#{output}/old-profile.mk", old)
cfg = File.read(config)
abort 'MAKECONF must include the tested cross profile' unless cfg.include?(profile)
File.write("#{output}/old.mk.conf", cfg.gsub(profile, "#{output}/old-profile.mk"))
baseline = query.call("#{output}/old.mk.conf")
abort "Baseline did not expose the old rc path: #{baseline.inspect}" unless baseline == ['/usr/pkg/etc/rc.d', *actual[1..-1]]
File.write("#{output}/queries.txt", "baseline=#{baseline.inspect}\nfixed=#{actual.inspect}\noverride=#{override.inspect}\n")
puts 'PASS: actual bmake cross default, package sysconf, explicit override and causal old-profile control'
