#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Check the complete pkgsrc recipe without compiling or installing packages.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: kwin-runtime-dependencies.rb PREPARED_PKGSRC MAKECONF KWIN_MAKEFILE NEW_OUTPUT' unless ARGV.length == 4
tree, conf, recipe = ARGV.first(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'NEW_OUTPUT must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
make = ENV.fetch('BMAKE', 'bmake')
pkg_admin = ENV.fetch('PKG_ADMIN', 'pkg_admin')

def query(log, command, names)
  output, status = Open3.capture2e(*command, *names.flat_map { |name| ['-V', "${#{name}}"] })
  File.write(log, output)
  abort "pkgsrc query failed: #{log}" unless status.success?
  values = output.lines.map(&:chomp)
  abort "unexpected pkgsrc query output: #{log}" unless values.length == names.length
  names.zip(values).to_h
end

%w[yes no].each do |cross|
  mode = cross == 'yes' ? 'cross' : 'native'
  common = ["MAKECONF=#{conf}", "WRKOBJDIR=#{work}/work", "USE_CROSS_COMPILE=#{cross}"]
  kwin = query("#{work}/#{mode}-kwin.log",
               [make, '-C', "#{tree}/x11/plasma6-kwin", '-f', recipe, *common],
               %w[PKG_FAIL_REASON PKGNAME DEPENDS TOOL_DEPENDS])
  abort "#{mode} KWin recipe rejected: #{kwin['PKG_FAIL_REASON']}" unless kwin['PKG_FAIL_REASON'].empty?
  runtime = Shellwords.split(kwin['DEPENDS']).select { |dep| dep.start_with?('vulkan-loader') }
  abort "#{mode}: missing or ambiguous Vulkan loader runtime dependency" unless runtime.length == 1
  pattern, origin = runtime.first.split(':', 2)
  abort "#{mode}: Vulkan loader must use the common recipe" unless origin == '../../graphics/vulkan-loader'
  tools = Shellwords.split(kwin['TOOL_DEPENDS'])
  abort "#{mode}: Vulkan loader is a runtime dependency, not a host tool" if tools.any? { |dep| dep.start_with?('vulkan-loader') }

  loader = query("#{work}/#{mode}-loader.log",
                 [make, '-C', "#{tree}/graphics/vulkan-loader", *common],
                 %w[PKG_FAIL_REASON PKGNAME])
  abort "#{mode} loader recipe rejected: #{loader['PKG_FAIL_REASON']}" unless loader['PKG_FAIL_REASON'].empty?
  output, status = Open3.capture2e(pkg_admin, 'pmatch', pattern, loader['PKGNAME'])
  File.write("#{work}/#{mode}-match.log", output)
  abort "#{mode}: runtime dependency rejects the common Vulkan loader" unless status.success?
  puts "PASS: #{mode} #{kwin['PKGNAME']} requires #{loader['PKGNAME']} at runtime"
end

inputs = [__FILE__, conf, recipe, "#{tree}/graphics/vulkan-loader/Makefile",
          "#{tree}/graphics/vulkan-headers/Makefile.common"]
File.write("#{work}/inputs.sha256", inputs.map { |path| "#{Digest::SHA256.file(path).hexdigest}  #{path}\n" }.join)
puts 'PASS: pkgsrc dependency selection only; installed Vulkan loading needs a target test'
