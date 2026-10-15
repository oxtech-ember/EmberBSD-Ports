#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Check the current source manifest against the normal Python recipe and bytes.
require 'digest'
require 'fileutils'
require 'open3'
require 'tmpdir'
class PythonSourceMismatch < StandardError; end

def verify_source(profile, archive)
  recipe = profile + '/recipes/lang/python315'
  version = File.read(recipe + '/dist.mk')[/^PY_DISTVERSION=\s*(\S+)$/, 1]
  raise PythonSourceMismatch, 'current Python recipe version is invalid' unless version&.match?(/\A3\.15\.[0-9]+\z/)
  name = 'Python-' + version + '.tar.xz'
  rows = File.readlines(profile + '/sources.tsv', chomp: true).reject { |l| l.start_with?('#') }.map { |l| l.split("\t", -1) }.select { |r| r.first&.start_with?('Python-') }
  source_pin = File.read(recipe + '/distinfo').scan(/^SHA256 \(#{Regexp.escape(name)}\) = ([0-9a-f]{64})$/).flatten
  expected = [name, source_pin.first, 'https://www.python.org/ftp/python/' + version + '/' + name]
  raise PythonSourceMismatch, 'current Python source missing, duplicated or changed in common manifest' unless source_pin.length == 1 && rows == [expected]
  raise PythonSourceMismatch, 'current Python archive checksum mismatch' unless Digest::SHA256.file(archive).hexdigest == source_pin.first
  sizes = File.read(recipe + '/distinfo').scan(/^Size \(#{Regexp.escape(name)}\) = ([0-9]+) bytes$/).flatten
  raise PythonSourceMismatch, 'current Python archive Size differs from actual pinned bytes' unless sizes == [File.size(archive).to_s]
  [version, name]
end

abort 'Usage: python-source-selection.rb VERIFIED_DISTFILES NORMAL_EXPORTED_PKGSRC' unless ARGV.length == 2
profile = File.expand_path('..', __dir__)
export = File.realpath(ARGV[1])
selected_version = File.read(profile + '/recipes/lang/python315/dist.mk')[/^PY_DISTVERSION=\s*(\S+)$/, 1]
archive = File.realpath(ARGV[0] + '/Python-' + selected_version.to_s + '.tar.xz')
begin
  version, name = verify_source(profile, archive)
rescue PythonSourceMismatch => error
  abort 'FAIL: ' + error.message
end
# Read the normal export without modifying its recipe or package database.
raise 'export selected another Python recipe' unless File.binread(export + '/lang/python315/dist.mk') == File.binread(profile + '/recipes/lang/python315/dist.mk')
raise 'normal export lacks current interpreter selection' unless File.read(export + '/lang/python/pyversion.mk').match?(/^PYTHON_VERSION_DEFAULT\?=\s*315$/)
digest = ENV.fetch('DIGEST')
raise 'supply an absolute native digest executable' unless digest.start_with?('/') && File.executable?(digest)
log, status = Open3.capture2e({'DIGEST' => digest}, 'awk', '-f', export + '/mk/checksum/checksum.awk', '--', profile + '/recipes/lang/python315/distinfo', name, chdir: File.dirname(archive))
raise 'normal pkgsrc archive checksum failed: ' + log unless status.success?
if ENV['BMAKE']
  log, status = Open3.capture2e(ENV.fetch('BMAKE'), '-C', export + '/lang/python315', '-V', '${PKGNAME}', '-V', '${PY_DISTVERSION}')
  lines = log.lines.map(&:strip)
  raise 'normal bmake Python selection differs: ' + log unless status.success? && lines.length == 2 && lines[0].match?(/\Apython315-#{Regexp.escape(version)}(?:nb[0-9]+)?\z/) && lines[1] == version
  puts 'PASS: real native bmake selects the current normal Python recipe; no package phase runs'
end
Dir.mktmpdir('ember-python-source-selection-') do |work|
  fixture = work + '/profile'
  FileUtils.mkdir_p(fixture + '/recipes/lang/python315')
  %w[dist.mk distinfo].each { |f| FileUtils.cp(profile + '/recipes/lang/python315/' + f, fixture + '/recipes/lang/python315/' + f) }
  manifest = File.read(profile + '/sources.tsv')
  original_info = File.read(fixture + '/recipes/lang/python315/distinfo')
  reject = lambda do |reason, candidate_archive = archive|
    begin
      verify_source(fixture, candidate_archive)
    rescue PythonSourceMismatch
      next
    end
    raise 'accepted invalid Python source selection: ' + reason
  end
  File.write(fixture + '/sources.tsv', manifest.lines.reject { |l| l.start_with?('Python-') }.join)
  reject.call('absent current source')
  File.write(fixture + '/sources.tsv', manifest + manifest.lines.find { |l| l.start_with?('Python-') })
  reject.call('duplicate current source')
  File.write(fixture + '/sources.tsv', manifest.sub('Python-' + version, 'Python-3.14.8'))
  reject.call('old source version')
  File.write(fixture + '/sources.tsv', manifest.sub('https://www.python.org/ftp/python/', 'https://example.invalid/'))
  reject.call('foreign source URL')
  File.write(fixture + '/sources.tsv', manifest)
  File.write(fixture + '/recipes/lang/python315/distinfo', original_info.sub(/^Size .*$/, 'Size (' + name + ') = 1 bytes'))
  reject.call('wrong source size')
  File.write(fixture + '/recipes/lang/python315/distinfo', original_info)
  changed = work + '/' + name
  FileUtils.cp(archive, changed); File.open(changed, 'ab') { |f| f.write('changed') }
  reject.call('changed archive', changed)
end
puts 'PASS: current Python source URL/SHA256 and actual Size match; normal pkgsrc checksum passes'
puts 'PASS: missing, duplicate, old/foreign source, wrong Size and changed bytes fail; no target compilation or runtime acceptance'
