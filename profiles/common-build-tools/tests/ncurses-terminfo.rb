#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual staged ncurses packing-list check.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'pathname'

abort 'Usage: ncurses-terminfo.rb PKGSRC MAKECONF INSTALLED_STAGE NEW_WORK' unless ARGV.length == 4
pkgsrc, makeconf, stage = ARGV.take(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[3])
abort 'Use absolute portable paths.' unless [pkgsrc, makeconf, stage, work].all? { |p| p.match?(%r{\A/[A-Za-z0-9_./-]+\z}) }
abort 'Output already exists.' if File.exist?(work) || File.symlink?(work)
profile = File.expand_path('..', __dir__)
patch = File.join(profile, 'patches/pkgsrc-ncurses-terminfo-aliases.patch')
recipe = File.join(pkgsrc, 'devel/ncurses')
abort 'Expected the ncurses 6.6 recipe.' unless File.read("#{recipe}/Makefile").match?(/^DISTNAME=\s+ncurses-6\.6$/)
terminfo = File.join(stage, 'usr/pkg/share/terminfo')
files = Dir.glob("#{terminfo}/**/*").reject { |path| File.directory?(path) && !File.symlink?(path) }
aliases = files.select { |path| File.symlink?(path) }
abort 'Use an actual stage with regular entries and aliases.' if aliases.empty? || files.length == aliases.length
aliases.each do |path|
  target = File.realpath(path)
  abort "Alias does not resolve to a staged entry: #{path}" unless target.start_with?("#{terminfo}/") && File.file?(target)
end
relative_aliases = aliases.map { |p| p.delete_prefix("#{stage}/usr/pkg/") }.sort
FileUtils.mkdir(work)
commands = []
run = lambda do |name, argv, expected|
  output, status = Open3.capture2e({ 'LC_ALL' => 'C' }, *argv)
  File.write("#{work}/#{name}.log", output)
  commands << { name: name, argv: argv, status: status.exitstatus }
  File.write("#{work}/commands.json", JSON.pretty_generate(commands) + "\n")
  abort "Unexpected status for #{name}; see its log." unless status.exitstatus == expected
  output
end
bmake = ENV.fetch('BMAKE', 'bmake')
results = {}
%w[original patched extra missing].each do |variant|
  base = "#{work}/#{variant}"
  obj = "#{base}/work"
  FileUtils.mkdir_p(["#{base}/devel/ncurses", "#{obj}/.destdir/usr/pkg"])
  FileUtils.cp("#{recipe}/Makefile", "#{base}/devel/ncurses/Makefile")
  unless variant == 'original'
    run.call("#{variant}-patch", ['patch', '-f', '-N', '-F', '0', '-p1', '-d', base, '-i', patch], 0)
  end
  make = [bmake, '-C', recipe, '-f', "#{base}/devel/ncurses/Makefile",
          "MAKECONF=#{makeconf}", '_PKGSRC_BARRIER=yes', "WRKDIR=#{obj}",
          "WRKOBJDIR=#{base}/objects", "PACKAGES=#{base}/packages"]
  %w[WRKDIR DESTDIR PLIST ERROR_DIR].each do |variable|
    value = run.call("#{variant}-#{variable}", make + ['show-var', "VARNAME=#{variable}"], 0).strip
    path = Pathname.new(value).cleanpath.to_s
    abort "Non-private #{variable}: #{value}" unless path == obj || path.start_with?("#{obj}/")
  end
  fail_reason = run.call("#{variant}-metadata", make + ['show-var', 'VARNAME=PKG_FAIL_REASON'], 0).strip
  abort "Invalid package configuration: #{fail_reason}" unless fail_reason.empty?
  run.call("#{variant}-pre", make + ['check-files-pre'], 0)
  FileUtils.cp_r("#{stage}/.", "#{obj}/.destdir", preserve: true)
  run.call("#{variant}-install-list", make + ['post-install'], 0)
  run.call("#{variant}-plist", make + ['plist'], 0)
  # Mutate only this new private copy, after normal PLIST generation.
  if variant == 'extra'
    File.write("#{obj}/.destdir/usr/pkg/unlisted-terminfo-control", "unexpected\n")
  elsif variant == 'missing'
    File.unlink("#{obj}/.destdir/usr/pkg/#{relative_aliases.first}")
  end
  run.call("#{variant}-check", make + ['check-files'], variant == 'patched' ? 0 : 1)
  extra = File.readlines("#{obj}/.check_files_extra", chomp: true).map { |p| p.delete_prefix("#{obj}/.destdir/usr/pkg/") }.sort
  missing = File.readlines("#{obj}/.check_files_missing_real", chomp: true).map { |p| p.delete_prefix("#{obj}/.destdir/usr/pkg/") }.sort
  expected_extra = variant == 'original' ? relative_aliases : (variant == 'extra' ? ['unlisted-terminfo-control'] : [])
  expected_missing = variant == 'missing' ? [relative_aliases.first] : []
  abort "Unexpected file-check diagnostic for #{variant}" unless extra == expected_extra && missing == expected_missing
  results[variant] = { extra: extra.length, missing: missing.length,
                       terminfo_entries: File.readlines("#{obj}/PLIST.terminfo").length }
end
inputs = ["#{recipe}/Makefile", "#{recipe}/PLIST", "#{recipe}/distinfo", patch,
          "#{pkgsrc}/mk/check/check-files.mk", "#{pkgsrc}/mk/plist/plist.mk", makeconf]
receipt = {
  scope: 'Actual copied ncurses stage, normal post-install/plist/check-files; no package installation or target execution.',
  inputs: inputs.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] },
  stage: stage,
  terminfo: files.sort.to_h { |path| [path.delete_prefix("#{stage}/"), File.symlink?(path) ? { symlink: File.readlink(path) } : { sha256: Digest::SHA256.file(path).hexdigest }] },
  results: results
}
File.write("#{work}/result.json", JSON.pretty_generate(receipt) + "\n")
puts "PASS: #{relative_aliases.length} actual aliases enter PLIST; unexpected and missing files still fail."
