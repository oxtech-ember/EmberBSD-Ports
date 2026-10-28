#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Query real pkgsrc and generate its D-Bus rc script.
require 'fileutils'
require 'open3'
abort 'Usage: cross-rcd-path.rb DBUS_PACKAGE_DIRECTORY MAKECONF NEW_OUTPUT' unless ARGV.length == 3
package, config, output = ARGV.map { |p| File.expand_path(p) }
Dir.mkdir(output)
profile = File.expand_path('../cross/mk.conf', __dir__)
make = ENV.fetch('BMAKE', 'bmake')
vars = %w[RCD_SCRIPTS_DIR SYSCONFBASE PKG_SYSCONFBASE INIT_SYSTEM RCD_SCRIPTS]
invoke = lambda do |cfg, name, *args|
  out, err, status = Open3.capture3(make, '-C', package, "MAKECONF=#{cfg}", "WRKOBJDIR=#{output}/#{name}", *args)
  File.open("#{output}/commands.log", 'a') { |f| f.write("#{name} #{args.inspect}\nexit=#{status.exitstatus}\n#{out}#{err}\n") }
  abort "bmake failed: #{out}#{err}" unless status.success?
  out
end
query = lambda do |cfg, name, *overrides|
  invoke.call(cfg, name, *overrides, *vars.flat_map { |v| ['-V', "${#{v}}"] }).lines.map(&:strip)
end
generate = lambda do |cfg, name, sysconf, *overrides|
  invoke.call(cfg, name, *overrides, 'generate-rcd-scripts')
  path = invoke.call(cfg, name, *overrides, '-V', '${RCD_SCRIPT_WRK.dbus}').strip
  script = File.read(path)
  abort "Wrong base rc.subr in #{name}" unless script.include?("$_rc_subr_loaded . #{sysconf}/rc.subr\n")
  abort "Wrong rc.conf instructions in #{name}" unless script.include?("#{sysconf}/rc.conf")
  abort "Unexpanded substitution in #{name}" if script.match?(/@[A-Z_]+@/)
  abort "Shell syntax error in #{name}" unless system('/bin/sh', '-n', path)
  script
end
actual = query.call(config, 'default')
abort "Wrong cross defaults: #{actual.inspect}" unless actual == ['/etc/rc.d', '/etc', '/usr/pkg/etc', 'rc.d', 'dbus']
fixed = generate.call(config, 'default', '/etc')
abort 'Cross script contains a build-host path' if fixed.match?(%r{/(?:Volumes|Users|private/tmp|opt/homebrew)/})
abort 'Wrong target interpreter' unless fixed.start_with?("#!/bin/sh\n")
[
  ['rc-override', 'RCD_SCRIPTS_DIR=/etc/custom-rc.d', ['/etc/custom-rc.d', *actual[1..]]],
  ['base-override', 'CROSS_SYSCONFBASE=/etc/custom-base', [actual[0], '/etc/custom-base', *actual[2..]]],
  ['package-override', 'PKG_SYSCONFBASE=/usr/pkg/etc/custom-package', [*actual[0..1], '/usr/pkg/etc/custom-package', *actual[3..]]]
].each do |name, override, expected|
  abort "Explicit override was lost: #{name}" unless query.call(config, name, override) == expected
  generate.call(config, name, expected[1], override)
end
source = File.read(profile)
old = source.sub(/^CROSS_SYSCONFBASE\?=\/etc$/, 'CROSS_SYSCONFBASE=/usr/pkg/etc')
abort 'No profile mutation point' if source == old
File.write("#{output}/old-profile.mk", old)
cfg = File.read(config)
abort 'MAKECONF must include the tested cross profile' unless cfg.include?(profile)
File.write("#{output}/old.mk.conf", cfg.gsub(profile, "#{output}/old-profile.mk"))
baseline = query.call("#{output}/old.mk.conf", 'old')
abort "Baseline did not expose the wrong base directory: #{baseline.inspect}" unless baseline == [actual[0], '/usr/pkg/etc', *actual[2..]]
generate.call("#{output}/old.mk.conf", 'old', '/usr/pkg/etc')
# Retain the original service-directory regression as a separate causal control.
File.write("#{output}/old-rc-profile.mk", old.sub(/^RCD_SCRIPTS_DIR\?=\/etc\/rc\.d\n/, ''))
File.write("#{output}/old-rc.mk.conf", cfg.gsub(profile, "#{output}/old-rc-profile.mk"))
abort 'Old service-directory failure disappeared' unless query.call("#{output}/old-rc.mk.conf", 'old-rc')[0] == '/usr/pkg/etc/rc.d'
native = query.call(config, 'native', 'USE_CROSS_COMPILE=no')
old_native = query.call("#{output}/old.mk.conf", 'old-native', 'USE_CROSS_COMPILE=no')
abort 'Native configuration changed' unless native == old_native
native_script = generate.call(config, 'native', native[1], 'USE_CROSS_COMPILE=no')
old_native_script = generate.call("#{output}/old.mk.conf", 'old-native', old_native[1], 'USE_CROSS_COMPILE=no')
abort 'Native rc script changed' unless native_script == old_native_script
File.write("#{output}/queries.txt", "baseline=#{baseline.inspect}\nfixed=#{actual.inspect}\nnative=#{native.inspect}\n")
puts 'PASS: actual bmake defaults, generated D-Bus rc.subr, three overrides, two causal controls and native independence'
