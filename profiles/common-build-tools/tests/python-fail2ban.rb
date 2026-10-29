#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); fail2ban builds for and passes its tests on the one kept Python.
require 'open3'
require 'fileutils'

usage = 'usage: python-fail2ban.rb EXPORTED_PKGSRC MAKECONF DISTDIR NEW_WORK (BMAKE, PYTHON)'
abort usage unless ARGV.length == 4 && ENV['BMAKE'] && ENV['PYTHON']
tree, makeconf, distdir = ARGV.take(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[3])
abort 'NEW_WORK must be new' if File.exist?(work) || File.symlink?(work)
Dir.mkdir(work)

PKGPATH = 'security/fail2ban'
names = %w[PKGNAME PYTHON_VERSION PKG_FAIL_REASON DISTFILES]
out, err, status = Open3.capture3({ 'MAKECONF' => makeconf }, ENV['BMAKE'], *names.flat_map { |n| ['-v', n] },
                                  chdir: "#{tree}/#{PKGPATH}")
abort "#{PKGPATH}: bmake failed: #{err}" unless status.success?
v = names.zip(out.lines.map(&:strip)).to_h
abort "#{PKGPATH}: #{v['PKG_FAIL_REASON']}" unless v['PKG_FAIL_REASON'].empty?
pyver, = Open3.capture2(ENV['PYTHON'], '-c', 'import sys; print("%d%d" % sys.version_info[:2])')
abort "#{PKGPATH} selects Python #{v['PYTHON_VERSION']}, not the kept #{pyver.strip}" unless v['PYTHON_VERSION'] == pyver.strip
version = v['PKGNAME'][/-([0-9][^-]*)\z/, 1].sub(/nb\d+\z/, '')

_, status = Open3.capture2e('tar', '-xzf', "#{distdir}/#{v['DISTFILES']}", '-C', work)
abort "cannot extract #{v['DISTFILES']}" unless status.success?
src = "#{work}/fail2ban-#{version}"
env = { 'HOME' => work, 'TMPDIR' => work, 'PYTHONPATH' => src }
out, status = Open3.capture2e(env, ENV['PYTHON'], 'bin/fail2ban-client', '--version', chdir: src)
abort "fail2ban-client does not run:\n#{out}" unless status.success? && out.include?(version)

args = %w[--fast --no-network]
# Darwin's /bin/sh echo prints "-n"; these command-action tests check shell output, not Python.
if RUBY_PLATFORM.include?('darwin')
  # -i keeps a test that any one regexp misses, so give it a single alternation.
  args += ['-i', 'testExecuteTimeoutWithNastyChildren|testExecuteWithVars|testServerActions_NginxBlockMap']
end
out, status = Open3.capture2e(env, ENV['PYTHON'], 'bin/fail2ban-testcases', *args, chdir: src)
out = out.b
File.write("#{work}/testcases.out", out)
summary = out.lines.grep(/\ARan \d+ tests/).last.to_s.strip
abort "fail2ban #{version} tests fail on Python #{pyver.strip}:\n#{out.lines.last(30).join}" unless status.success?
puts "fail2ban-#{version}: #{summary} on Python #{pyver.strip}"
puts "PASS: fail2ban #{version} selects Python #{pyver.strip} and its test suite passes"
