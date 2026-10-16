#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real pkgsrc MAKECONF phase.
require 'fileutils'
require 'open3'

abort 'usage: cross-makeconf-phase.rb PREPARED_PKGSRC CROSS_MAKECONF NEW_WORK' unless ARGV.length == 3
tree, config = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
profile = File.expand_path('../mk.conf', __dir__)
FileUtils.cp(profile, work + '/graphics.mk.conf')
%w[EMBERBSD-COMMON-GRAPHICS-SOURCES EMBERBSD-COMMON-TOOLS-MK.CONF].each do |name|
  FileUtils.cp(tree + '/' + name, work + '/' + name)
end
text = File.read(config)
include_line = /^\.include "[^"]*\/EMBERBSD-COMMON-GRAPHICS-MK\.CONF"$/
abort 'expected exactly one graphics profile include' unless text.scan(include_line).length == 1
text = text.sub(include_line, ".include \"#{work}/graphics.mk.conf\"\n_EMBER_TEST_EARLY_ARCH:=${MACHINE_ARCH}\n_EMBER_TEST_EARLY_CROSS_ARCH:=${CROSS_MACHINE_ARCH}")
# Queries can create only this test's work paths. Do not use the live WRKOBJDIR.
text += "\nWRKOBJDIR=#{work}/objects\nPACKAGES=#{work}/packages\n"
File.write(work + '/mk.conf', text)
vars = %w[PKG_FAIL_REASON OPSYS CROSS_OPSYS MACHINE_ARCH CROSS_MACHINE_ARCH NATIVE_MACHINE_ARCH _EMBER_TEST_EARLY_ARCH _EMBER_TEST_EARLY_CROSS_ARCH EMBERBSD_COMMON_GRAPHICS _CBBH]
query = lambda do |name, *args|
  cmd = [make, '-C', tree + '/devel/pkgconf', 'MAKECONF=' + work + '/mk.conf', *args, *vars.flat_map { |v| ['-V', '${' + v + '}'] }]
  out, err, status = Open3.capture3(*cmd)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  abort "real pkgsrc query failed: #{name}: #{err}" unless status.success?
  lines = out.lines.map(&:chomp)
  abort "unexpected output: #{name}" unless lines.length == vars.length
  vars.zip(lines).to_h
end
check = lambda do |name, condition|
  abort "FAIL: #{name}" unless condition
  puts "PASS: #{name}"
end
amd = query.call('amd64')
check.call('MAKECONF sees the actual host architecture before the target swap', amd['_EMBER_TEST_EARLY_ARCH'] == amd['NATIVE_MACHINE_ARCH'] && amd['_EMBER_TEST_EARLY_CROSS_ARCH'] == 'x86_64' && amd['NATIVE_MACHINE_ARCH'] != 'x86_64')
check.call('actual amd64 pkgsrc parse has no stale MAKECONF failure', amd['PKG_FAIL_REASON'].empty? && amd['_CBBH'] == 'yes' && amd.values_at('OPSYS', 'CROSS_OPSYS', 'MACHINE_ARCH', 'CROSS_MACHINE_ARCH') == %w[NetBSD NetBSD x86_64 x86_64])
{
  'mixed-machine' => ['MACHINE_ARCH=aarch64', 'cross target must match'],
  'mixed-cross' => ['CROSS_MACHINE_ARCH=aarch64', 'CROSS_MACHINE_ARCH must match'],
  'foreign-machine' => ['MACHINE_ARCH=riscv64', 'supports NetBSD 11/AArch64 and amd64 only'],
  'foreign-os' => ['CROSS_OPSYS=Darwin', 'supports NetBSD 11/AArch64 and amd64 only'],
  'foreign-version' => ['CROSS_OS_VERSION=12.0', 'supports NetBSD 11/AArch64 and amd64 only'],
  'unknown-selection' => ['EMBERBSD_CROSS_TARGET=riscv64', 'Unsupported cross target']
}.each do |name, (arg, reason)|
  result = query.call(name, arg)
  check.call("final pkgsrc values reject #{name}", result['PKG_FAIL_REASON'].include?(reason) && result['_CBBH'] == 'no')
  # This is pkgsrc's actual failure target, attached to bootstrap-depends
  # by can-be-built-here.mk. It cannot fetch, compile or install dependencies.
  out, status = Open3.capture2e(make, '-C', tree + '/devel/pkgconf', 'MAKECONF=' + work + '/mk.conf', arg, '_cbbh')
  File.write(work + '/' + name + '-gate.log', out)
  check.call("normal pkgsrc failure gate exits nonzero for #{name}", !status.success? && out.include?(reason))
end
arm = query.call('aarch64-metadata', 'EMBERBSD_CROSS_TARGET=aarch64')
check.call('AArch64 target metadata retains graphics support independently of missing ARM runtime inputs', arm['MACHINE_ARCH'] == 'aarch64' && !arm['PKG_FAIL_REASON'].include?('common graphics cross target') && !arm['PKG_FAIL_REASON'].include?('common graphics candidate supports'))
host = query.call('native-dependency', 'USE_CROSS_COMPILE=no')
check.call('native tool dependency stays native without graphics opt-in leakage', host['OPSYS'] == 'Darwin' && host['MACHINE_ARCH'] == host['NATIVE_MACHINE_ARCH'] && host['EMBERBSD_COMMON_GRAPHICS'].empty? && host['PKG_FAIL_REASON'].empty?)
puts 'PASS: real pkgsrc phase and refusal contracts only; no target package built or executed'
