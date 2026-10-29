#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); the consumers of a kept Ruby gem accept it.
require 'open3'
require 'rubygems/package'
require 'tmpdir'

usage = 'usage: ruby-gem-consumers.rb EXPORTED_PKGSRC MAKECONF DISTDIR NEW_WORK (BMAKE, PKG_ADMIN)'
abort usage unless ARGV.length == 4 && ENV['BMAKE'] && ENV['PKG_ADMIN']
tree, makeconf, distdir = ARGV.take(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV[3])
abort 'NEW_WORK must be new' if File.exist?(work) || File.symlink?(work)
Dir.mkdir(work)

def vars(tree, makeconf, pkgpath, *names)
  out, err, status = Open3.capture3({ 'MAKECONF' => makeconf }, ENV['BMAKE'],
                                    *names.flat_map { |name| ['-v', name] }, chdir: "#{tree}/#{pkgpath}")
  abort "#{pkgpath}: bmake failed: #{err}" unless status.success?
  names.zip(out.lines.map(&:strip)).to_h
end

# gem.mk applies OVERRIDE_GEMSPEC to the distfile's gemspec with update-gemspec.rb.
def gem_requirement(tree, distdir, work, distfile, override, gem)
  spec = Gem::Package.new("#{distdir}/#{distfile}").spec
  file = "#{work}/#{spec.full_name}.gemspec"
  File.write(file, spec.to_ruby)
  unless override.empty?
    out, status = Open3.capture2e(RbConfig.ruby, "#{tree}/lang/ruby/files/update-gemspec.rb", file,
                                  *override.split)
    abort "#{distfile}: update-gemspec.rb failed:\n#{out}" unless status.success?
  end
  Gem::Specification.load(file).runtime_dependencies.find { |dep| dep.name == gem }
end

kept = {
  'www/ruby-rouge' => %w[rouge 5.1.0 www/heel www/ruby-jekyll textproc/ruby-review graphics/rabbit www/motyl],
  'mail/ruby-mail' => %w[mail 2.9.1 mail/ruby-actionmailer81 mail/ruby-actionmailbox81 www/ruby-padrino-mailer],
  'devel/ruby-thor' => %w[thor 1.5.0 devel/ruby-approvaltests devel/ruby-jirametrics devel/ruby-protobuf-cucumber
                          devel/ruby-railties81 sysutils/ruby-inspec-core sysutils/ruby-openfact textproc/ruby-haml
                          www/ruby-jquery-rails www/ruby-padrino-core]
}
kept.each do |kept_path, (gem, wanted, *consumers)|
  kept_vars = vars(tree, makeconf, kept_path, 'PKGNAME', 'PKG_FAIL_REASON')
  abort "#{kept_path}: #{kept_vars['PKG_FAIL_REASON']}" unless kept_vars['PKG_FAIL_REASON'].empty?
  version = kept_vars['PKGNAME'][/-([0-9][^-]*)\z/, 1].sub(/nb\d+\z/, '')
  abort "#{kept_path} is #{version}, not #{wanted}" unless version == wanted
  consumers.each do |pkgpath|
    v = vars(tree, makeconf, pkgpath, 'PKG_FAIL_REASON', 'DEPENDS', 'DISTFILES', 'OVERRIDE_GEMSPEC', 'GEM_NAME')
    abort "#{pkgpath}: #{v['PKG_FAIL_REASON']}" unless v['PKG_FAIL_REASON'].empty?
    pattern = v['DEPENDS'].split.map { |dep| dep.split(':') }.find { |_, dir| dir == "../../#{kept_path}" }&.first
    abort "#{pkgpath} does not depend on #{kept_path}" unless pattern
    _, status = Open3.capture2e(ENV['PKG_ADMIN'], 'pmatch', pattern, kept_vars['PKGNAME'])
    abort "#{pkgpath}: #{pattern} rejects #{kept_vars['PKGNAME']}" unless status.success?
    next puts("#{pkgpath}: #{pattern} accepts #{version}") if v['GEM_NAME'].empty?
    dep = gem_requirement(tree, distdir, work, v['DISTFILES'].split.first, v['OVERRIDE_GEMSPEC'], gem)
    abort "#{pkgpath}: gemspec does not list #{gem}" unless dep
    abort "#{pkgpath}: gemspec #{gem} #{dep.requirement} rejects #{version}" unless dep.match?(gem, version)
    puts "#{pkgpath}: #{pattern} and gemspec #{gem} #{dep.requirement} accept #{version}"
  end
end
heel = vars(tree, makeconf, 'www/heel', 'DEPENDS')['DEPENDS'].split.map { |dep| dep.split(':') }
mime = heel.find { |_, dir| dir == '../../mail/ruby-mime-types' }&.first
abort 'www/heel does not depend on mime-types' unless mime
_, status = Open3.capture2e(ENV['PKG_ADMIN'], 'pmatch', mime, mime.sub(/-mime-types.*/, '-mime-types-3.7.0'))
abort "www/heel: #{mime} accepts mime-types 3.7.0 without the sort fix" if status.success?
mt = vars(tree, makeconf, 'mail/ruby-mime-types', 'PKGNAME')['PKGNAME']
_, status = Open3.capture2e(ENV['PKG_ADMIN'], 'pmatch', mime, mt)
abort "www/heel: #{mime} rejects #{mt}" unless status.success?
puts 'PASS: the consumers of rouge, mail and thor accept the kept versions'
