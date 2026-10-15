#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Exercise actual source hashes and the host-configure boundary; never build KWin.
require 'tmpdir'
require 'fileutils'
require 'open3'
require 'digest'
abort 'Usage: kwin-scanner-source.rb VERIFIED_DISTFILES HOST_QT' unless ARGV.length == 2
toolkit = File.expand_path('..', __dir__)
distfiles, qt = ARGV.map { |path| File.expand_path(path) }
version_file = 'shared/meta-pkgs/kde/plasma6.mk'
version = File.read(toolkit + '/' + version_file)[/^PLASMAVER\?=\s+(\S+)/, 1]
row = File.readlines(toolkit + '/sources.tsv').map { |line| line.chomp.split("\t") }.select { |a| a[0] == 'x11/plasma6-kwin' }
abort 'FAIL: canonical KWin manifest mismatch' unless row.length == 1 && row[0][1] == "kwin-#{version}.tar.xz"
archive, checksum = row.first.values_at(1, 2)
abort 'FAIL: actual upstream archive is unavailable or corrupt' unless File.file?(distfiles + '/' + archive) && Digest::SHA256.file(distfiles + '/' + archive).hexdigest == checksum
Dir.mktmpdir('ember-kwin-scanner-', '/tmp') do |work|
  fixture = work + '/toolkit'
  FileUtils.mkdir_p([fixture + '/cross', fixture + '/shared/meta-pkgs/kde', work + '/distfiles'])
  FileUtils.cp(toolkit + '/cross/build-kwin-scanner.sh', fixture + '/cross/')
  FileUtils.cp(toolkit + '/' + version_file, fixture + '/' + version_file)
  FileUtils.cp(toolkit + '/sources.tsv', fixture + '/sources.tsv')
  FileUtils.cp(distfiles + '/' + archive, work + '/distfiles/')
  cmake = work + '/cmake'
  File.write(cmake, "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$BOUNDARY_LOG\"\nexit 77\n")
  File.chmod(0755, cmake)
  boundary = work + '/boundary.log'
  env = {'CMAKE' => cmake, 'NINJA' => '/usr/bin/true', 'HOST_CXX' => '/usr/bin/c++', 'BOUNDARY_LOG' => boundary}
  invoke = lambda do |name|
    output = work + '/' + name
    text, status = Open3.capture2e(env, 'sh', fixture + '/cross/build-kwin-scanner.sh', work + '/distfiles', qt, work + '/ecm', output)
    [status, output, text]
  end
  status, output = invoke.call('valid')
  abort 'FAIL: verified current archive did not reach native configure' unless status.exitstatus == 77 && File.file?(boundary)
  args = File.readlines(boundary).map(&:strip)
  abort 'FAIL: configured a foreign source tree' unless args.include?(output + '/source/src/wayland/tools') && File.file?(output + '/source/src/wayland/tools/qtwaylandscanner.cpp')
  File.unlink(boundary)
  File.open(work + '/distfiles/' + archive, 'ab') { |io| io.write('corrupt') }
  status, output, text = invoke.call('bad-hash')
  abort 'FAIL: corrupt archive accepted' if status.success? || File.exist?(boundary) || File.exist?(output) || !text.include?('checksum mismatch')
  FileUtils.cp(distfiles + '/' + archive, work + '/distfiles/' + archive)
  File.open(fixture + '/sources.tsv', 'a') { |io| io.puts(row.first.join("\t")) }
  status, output, text = invoke.call('duplicate')
  abort 'FAIL: duplicate source owner accepted' if status.success? || File.exist?(boundary) || File.exist?(output) || !text.include?('Exactly one canonical KWin source')
  FileUtils.cp(toolkit + '/sources.tsv', fixture + '/sources.tsv')
  File.write(fixture + '/' + version_file, File.read(toolkit + '/' + version_file).sub(/^PLASMAVER\?=.*$/, 'PLASMAVER?= 0.0.0'))
  status, output, text = invoke.call('mixed-version')
  abort 'FAIL: shared Plasma/manifest mismatch accepted' if status.success? || File.exist?(boundary) || File.exist?(output) || !text.include?('manifest differs from the shared Plasma version')
end
puts 'PASS: actual KWin archive/hash/configure boundary; corrupt, duplicate and mixed-version sources fail before work creation'
