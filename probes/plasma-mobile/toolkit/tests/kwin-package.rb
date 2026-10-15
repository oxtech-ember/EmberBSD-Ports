#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check KWin's packaged render-node provider.
require 'open3'
require 'digest'
abort 'Usage: kwin-package.rb ARCHIVE PKG_ADMIN' unless ARGV.length == 2
archive, admin = ARGV.map { |path| File.expand_path(path) }
def run!(*command)
  out, err, status = Open3.capture3(*command)
  raise "Failed #{command.inspect}\n#{out}#{err}" unless status.success?
  out
end
begin
  tar = ENV.fetch('BSDTAR', 'tar')
  contents = run!(tar, '-xOf', archive, '+CONTENTS')
  raise 'Expected a KWin package' unless contents.match?(/^@name plasma6-kwin-\S+$/)
  patterns = contents.scan(/^@pkgdep (libudev-bsd\S+)$/).flatten
  raise 'Missing runtime libudev dependency' if patterns.empty?
  { '0.7.0.1' => false, '0.7.0.1nb1' => false,
    '0.7.0.1nb2' => true, '0.7.0.1nb3' => true, '0.7.0.2' => true }.each do |version, expected|
    patterns.each do |pattern|
      out, err, status = Open3.capture3(admin, 'pmatch', pattern, "libudev-bsd-#{version}")
      raise "pkg_admin error: #{out}#{err}" unless [0, 1].include?(status.exitstatus)
      raise "#{pattern} incorrectly #{status.success? ? 'accepts' : 'rejects'} libudev #{version}" unless status.success? == expected
    end
  end
  %w[+INSTALL +DEINSTALL].each do |name|
    script = run!(tar, '-xOf', archive, name)
    raise "Host path in #{name}" if script.match?(%r{/(?:Volumes|Users|private/tmp|opt/homebrew)/})
    sorts = script.scan(/^SORT="([^"]*)"$/).flatten
    raise "Missing target SORT in #{name}" if sorts.empty?
    raise "Incorrect target SORT in #{name}" unless sorts.all? { |value| value == '/usr/bin/sort' }
  end
  puts "PASS: KWin runtime dependency rejects old render providers; target helpers: #{Digest::SHA256.file(archive).hexdigest}"
rescue StandardError => error
  warn error.message
  exit 1
end
