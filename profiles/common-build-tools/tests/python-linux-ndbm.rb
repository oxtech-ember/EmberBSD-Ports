#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkgsrc NDBM dependency regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

unless ARGV.length == 6
  abort 'Usage: python-linux-ndbm.rb PKGSRC LINUX_MAKECONF NETBSD_MAKECONF OLD_MAKEFILE NEW_MAKEFILE NEW_WORK'
end
pkgsrc, linux_conf, netbsd_conf, old_recipe, new_recipe = ARGV.take(5).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[5])
paths = [pkgsrc, linux_conf, netbsd_conf, old_recipe, new_recipe, work]
abort 'Use absolute portable paths.' unless paths.all? { |p| p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) }
abort 'Output already exists.' if File.exist?(work) || File.symlink?(work)
FileUtils.mkdir(work)
variables = %w[OPSYS DEPENDS BDB_TYPE BUILDLINK_TRANSFORM CONFIGURE_ENV CONFIGURE_ARGS PKG_FAIL_REASON]
bmake = ENV.fetch('BMAKE', 'bmake')
results = {}
commands = []
{ 'linux' => linux_conf, 'netbsd' => netbsd_conf }.each do |platform, config|
  results[platform] = {}
  { 'old' => old_recipe, 'new' => new_recipe }.each do |label, recipe|
    values = {}
    variables.each do |variable|
      argv = [bmake, '-C', "#{pkgsrc}/lang/python315", '-f', recipe,
              "MAKECONF=#{config}", "WRKOBJDIR=#{work}/objects-#{platform}",
              "PACKAGES=#{work}/packages", 'show-var', "VARNAME=#{variable}"]
      out, err, status = Open3.capture3({ 'LC_ALL' => 'C' }, *argv)
      File.write("#{work}/#{platform}-#{label}-#{variable}.txt", out)
      File.write("#{work}/#{platform}-#{label}-#{variable}.err", err)
      commands << { argv: argv, status: status.exitstatus }
      File.write("#{work}/commands.json", JSON.pretty_generate(commands) + "\n")
      abort "Metadata failed for #{platform}/#{label}/#{variable}" unless status.success?
      values[variable] = out.strip
    end
    abort "Invalid configuration: #{values['PKG_FAIL_REASON']}" unless values['PKG_FAIL_REASON'].empty?
    results[platform][label] = values
  end
end
old = results.fetch('linux').fetch('old')
fixed = results.fetch('linux').fetch('new')
abort 'Linux inputs must select Linux.' unless old['OPSYS'] == 'Linux' && fixed['OPSYS'] == 'Linux'
bdb = %r{:\.\./\.\./databases/db[0-9]+\z}
removed = old['DEPENDS'].split.select { |entry| entry.match?(bdb) }
abort 'Baseline does not expose the redundant Berkeley DB dependency.' if removed.empty?
abort 'Linux dependencies changed beyond Berkeley DB.' unless old['DEPENDS'].split.reject { |e| e.match?(bdb) } == fixed['DEPENDS'].split
abort 'The GDBM compatibility dependency is missing.' unless fixed['DEPENDS'].include?(':../../databases/gdbm_compat')
abort 'Linux still selects Berkeley DB.' unless fixed['BDB_TYPE'].empty?
abort 'NDBM link routing is missing.' unless fixed['BUILDLINK_TRANSFORM'].split.include?('l:ndbm:gdbm_compat:gdbm')
%w[CONFIGURE_ENV CONFIGURE_ARGS].each do |variable|
  abort "Linux #{variable} changed." unless old[variable] == fixed[variable]
end
netbsd = results.fetch('netbsd')
abort 'NetBSD input must select NetBSD.' unless netbsd['old']['OPSYS'] == 'NetBSD'
abort 'NetBSD provider metadata changed.' unless netbsd['old'] == netbsd['new']
abort 'NetBSD has no Berkeley DB provider.' if netbsd['new']['BDB_TYPE'].empty?
inputs = paths.take(5).reject { |p| File.directory?(p) }
File.write("#{work}/result.json", JSON.pretty_generate(
  scope: 'Actual pkgsrc metadata only; no dependency installation, compilation or runtime test.',
  inputs: inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
  removed_linux_dependencies: removed, netbsd_provider: netbsd['new']['BDB_TYPE'],
  results: results
) + "\n")
puts 'PASS: Linux retains GDBM NDBM without Berkeley DB; NetBSD metadata is unchanged.'
