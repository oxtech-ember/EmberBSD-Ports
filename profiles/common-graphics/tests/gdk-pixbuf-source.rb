#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Prove final patches match the accepted build sources.
require 'digest'
require 'fileutils'
require 'open3'
abort 'Usage: gdk-pixbuf-source.rb ARCHIVE BUILT_SOURCE NEW_WORK' unless ARGV.size == 3
archive, built = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
abort 'wrong upstream archive' unless Digest::SHA256.file(archive).hexdigest == '919f529512961a12e81cd4b4b466a48c3933469e7f9a310c6513cd4fb252ba3c'
FileUtils.mkdir_p(work)
abort 'extract failed' unless system('tar', '-xJf', archive, '-C', work)
source = work + '/gdk-pixbuf-2.44.8'
recipe = File.expand_path('../../../pkgsrc/graphics/gdk-pixbuf2', __dir__)
distinfo = File.read(recipe + '/distinfo')
changed = []
Dir.glob(recipe + '/patches/patch-*').sort.each do |patch|
  data = File.read(patch)
  digest = Digest::SHA1.hexdigest(data.lines.reject { |l| l.include?('$NetBSD') }.join)
  abort 'patch checksum mismatch' unless distinfo.include?("SHA1 (#{File.basename(patch)}) = #{digest}")
  out, status = Open3.capture2e('patch', '-p0', '--fuzz=0', '-i', patch, chdir: source)
  File.write(work + '/' + File.basename(patch) + '.log', out)
  abort 'patch failed' unless status.success? && !out.include?('fuzz')
  changed += data.scan(/^\+\+\+ (\S+)/).flatten
end
changed.uniq.each do |name|
  expected = File.read(source + '/' + name).gsub('@LD_LIBRARY_PATH@', 'LD_LIBRARY_PATH')
  actual = File.read(built + '/' + name)
  if name.end_with?('.py')
    expected = expected.lines.drop(1).join
    actual = actual.lines.drop(1).join
  end
  abort "accepted build differs from final patch: #{name}" unless expected == actual
end
puts "PASS: verified archive, eight patches apply without fuzz, #{changed.uniq.size} patched files match accepted build"
