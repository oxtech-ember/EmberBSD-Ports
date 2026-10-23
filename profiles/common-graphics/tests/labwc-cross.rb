#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check selected-feature failures using real Meson.
require 'digest'
require 'fileutils'
require 'open3'
abort 'Usage: labwc-cross.rb ARCHIVE HOST_PREFIX NEW_WORK' unless ARGV.size == 3
archive, host = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
abort 'wrong archive' unless Digest::SHA256.file(archive).hexdigest == 'fae023b6fe022f7057556707a17cdb2d98e0138c5dffaedaa1dade975699f9e8'
FileUtils.mkdir_p([work, work + '/empty', work + '/bin'])
abort 'extract failed' unless system('tar', '-xzf', archive, '-C', work)
source = work + '/labwc-0.20.2'
original = File.readlines(source + '/meson.build').find { |l| l.start_with?('svg = dependency(') } or abort 'missing upstream selection'
recipe = File.expand_path('../../../pkgsrc/wayland/labwc', __dir__)
distinfo = File.read(recipe + '/distinfo')
Dir.glob(recipe + '/patches/*').sort.each do |p|
  hash = Digest::SHA1.hexdigest(File.read(p).lines.reject { |l| l.include?('$NetBSD') }.join)
  abort 'patch checksum mismatch' unless distinfo.include?("SHA1 (#{File.basename(p)}) = #{hash}")
  out, status = Open3.capture2e('patch', '-p0', '--fuzz=0', '-i', p, chdir: source)
  File.write(work + '/' + File.basename(p) + '.log', out)
  abort 'patch failed' unless status.success? && !out.include?('fuzz')
end
patched = File.readlines(source + '/meson.build').find { |l| l.start_with?('svg = dependency(') }
File.write(work + '/bin/pkg-config', "#!/bin/sh\nif [ \"$1\" = --version ]; then echo 3.0.7; exit 0; fi\nexit 1\n")
File.chmod(0755, work + '/bin/pkg-config')
File.write(work + '/native.ini', "[binaries]\nc = '/usr/bin/cc'\npkg-config = '#{work}/bin/pkg-config'\ncmake = '/usr/bin/false'\n")
[[original, 'original', 'enabled', true], [patched, 'required', 'enabled', false],
 [patched, 'disabled', 'disabled', true]].each do |line, name, option, expected|
  src = work + '/' + name + '-source'
  FileUtils.mkdir_p(src)
  File.write(src + '/meson.build', "project('labwc-svg-guard', 'c')\n" + line)
  File.write(src + '/meson.options', "option('svg', type: 'feature', value: 'enabled')\n")
  out, status = Open3.capture2e({'CC' => nil, 'CFLAGS' => nil, 'LDFLAGS' => nil},
    host + '/bin/meson', 'setup', work + '/' + name, src, '--native-file', work + '/native.ini',
    '--wrap-mode=nofallback', '-Dsvg=' + option)
  File.write(work + '/' + name + '.log', out)
  abort "unexpected #{name} result: #{out}" unless status.success? == expected
  abort 'wrong missing-provider error' if !expected && !out.include?('librsvg-2.0')
end
File.write(work + '/inputs.sha256', [__FILE__, archive, recipe + '/Makefile', recipe + '/options.mk', recipe + '/distinfo'].map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: pinned source and patches; original silently drops SVG, corrected enabled SVG fails, disabled SVG remains valid'
