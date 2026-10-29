#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); mime-types sorts types whose extensions changed.
require 'digest'
require 'open3'
require 'rbconfig'

abort 'usage: ruby-mime-types-columnar.rb EXPORTED_PKGSRC DISTDIR NEW_WORK' unless ARGV.length == 3
tree, distdir = ARGV.take(2).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[2])
abort 'NEW_WORK must be new' if File.exist?(work) || File.symlink?(work)

def run(*command, **options)
  out, status = Open3.capture2e(*command, **options)
  abort "#{command.join(' ')} failed:\n#{out}" unless status.success?
  out
end

# Extract a gem recipe's distfile after checking it against the recipe's distinfo,
# then apply the recipe patches after checking their SHA1 too. Like pkgsrc,
# the patch SHA1 leaves out the lines with the $NetBSD$ tag.
def extract(tree, distdir, work, pkgpath)
  distinfo = File.read("#{tree}/#{pkgpath}/distinfo")
  gem = distinfo[/^SHA512 \((\S+\.gem)\) = /, 1] or abort "#{pkgpath}: no gem in distinfo"
  sha512 = distinfo[/^SHA512 \(#{Regexp.escape(gem)}\) = (\h+)$/, 1]
  abort "#{gem}: checksum differs" unless Digest::SHA512.file("#{distdir}/#{gem}").hexdigest == sha512
  dir = "#{work}/#{File.basename(gem, '.gem')}"
  Dir.mkdir(dir)
  run('tar', '-xf', "#{distdir}/#{gem}", 'data.tar.gz', chdir: work)
  run('tar', '-xzf', "#{work}/data.tar.gz", '-C', dir)
  File.delete("#{work}/data.tar.gz")
  Dir.glob("#{tree}/#{pkgpath}/patches/patch-*").sort.each do |patch|
    sha1 = distinfo[/^SHA1 \(#{Regexp.escape(File.basename(patch))}\) = (\h+)$/, 1]
    abort "#{patch}: SHA1 differs" unless sha1 && Digest::SHA1.hexdigest(File.readlines(patch).grep_v(/\$NetBSD/).join) == sha1
    run('patch', '-p0', '-N', '-s', '-i', patch, chdir: dir)
  end
  "#{dir}/lib"
end

Dir.mkdir(work)
libs = %w[mail/ruby-mime-types mail/ruby-mime-types-data].map { |pkgpath| extract(tree, distdir, work, pkgpath) }
# heel's MimeMap adds .rb to text/plain; type_for must still sort the result.
check = <<~'RUBY'
  require 'mime/types'
  plain = MIME::Types['text/plain'].first
  plain.add_extensions('rb', 'sorttest')
  types = MIME::Types.type_for('x.rb').map(&:to_s)
  abort "x.rb gives #{types.inspect}" unless types.include?('text/plain') && types.include?('application/x-ruby')
  abort 'sorttest' unless MIME::Types.type_for('a.sorttest').map(&:to_s) == ['text/plain']
  abort 'sort' unless [plain, MIME::Types['image/jpeg'].first].sort.length == 2
  puts MIME::Types::VERSION
RUBY
version = run({ 'RUBYOPT' => nil, 'RUBYLIB' => nil, 'GEM_HOME' => nil, 'GEM_PATH' => nil }, RbConfig.ruby,
              *libs.flat_map { |lib| ['-I', lib] }, '-e', check).strip
puts "PASS: mime-types #{version} sorts types after add_extensions"
