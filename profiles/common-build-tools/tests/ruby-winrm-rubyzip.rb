#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); the chef-winrm gems load and zip files with the one kept rubyzip.
require 'open3'
require 'fileutils'
require 'rubygems/package'

usage = 'usage: ruby-winrm-rubyzip.rb EXPORTED_PKGSRC MAKECONF DISTDIR NEW_WORK (BMAKE, PKG_ADMIN)'
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

KEPT_ZIP = 'archivers/ruby-zip'
# train-winrm 0.4 uses the chef-winrm forks; the original gems are versions.mk redirects.
%w[net/ruby-winrm net/ruby-winrm-fs net/ruby-winrm-elevated textproc/ruby-gyoku].each do |old|
  abort "the export still has #{old}" if File.exist?("#{tree}/#{old}/Makefile")
end
zip = vars(tree, makeconf, KEPT_ZIP, 'PKGNAME', 'PKG_FAIL_REASON')
abort "#{KEPT_ZIP}: #{zip['PKG_FAIL_REASON']}" unless zip['PKG_FAIL_REASON'].empty?
zip_version = zip['PKGNAME'][/-([0-9][^-]*)\z/, 1].sub(/nb\d+\z/, '')

# Walk the Ruby DEPENDS of train-winrm and install every gem as gem.mk does.
home = "#{work}/gems"
queue = ['net/ruby-train-winrm']
seen = {}
until queue.empty?
  pkgpath = queue.shift
  next if seen[pkgpath]
  v = vars(tree, makeconf, pkgpath, 'PKGNAME', 'PKG_FAIL_REASON', 'DEPENDS', 'DISTFILES', 'OVERRIDE_GEMSPEC')
  abort "#{pkgpath}: #{v['PKG_FAIL_REASON']}" unless v['PKG_FAIL_REASON'].empty?
  seen[pkgpath] = v
  v['DEPENDS'].split.each do |dep|
    pattern, dir = dep.split(':')
    dep_path = dir.delete_prefix('../../')
    next unless File.basename(dep_path).start_with?('ruby-')
    if File.basename(dep_path).start_with?('ruby-zip') && dep_path != KEPT_ZIP
      abort "#{pkgpath} depends on #{dep_path}, not the kept #{KEPT_ZIP} (rubyzip #{zip_version})"
    end
    target = vars(tree, makeconf, dep_path, 'PKGNAME')['PKGNAME']
    _, status = Open3.capture2e(ENV['PKG_ADMIN'], 'pmatch', pattern, target)
    abort "#{pkgpath}: #{pattern} rejects #{target}" unless status.success?
    queue << dep_path
  end
end
%w[net/ruby-chef-winrm net/ruby-chef-winrm-fs net/ruby-chef-winrm-elevated textproc/ruby-chef-gyoku
   net/ruby-socksify].each do |pkgpath|
  abort "train-winrm does not pull in #{pkgpath}" unless seen[pkgpath]
end
abort "train-winrm does not pull in #{KEPT_ZIP}" unless seen[KEPT_ZIP]

seen.each do |pkgpath, v|
  gem = "#{distdir}/#{v['DISTFILES'].split.first}"
  pkg = Gem::Package.new(gem)
  unless pkg.spec.extensions.empty?
    # Native extensions (ffi, for Kerberos through gssapi) are not built here;
    # registering their gemspec lets RubyGems activate the gems that need them.
    spec = pkg.spec
    spec.extensions = []
    FileUtils.mkdir_p(["#{home}/specifications", "#{home}/gems/#{spec.full_name}"])
    File.write("#{home}/specifications/#{spec.full_name}.gemspec", spec.to_ruby)
    next
  end
  out, status = Open3.capture2e(RbConfig.ruby, '-rrubygems/gem_runner', '-e', 'Gem::GemRunner.new.run(ARGV)',
                                'install', '--local', '--ignore-dependencies', '--no-document',
                                '--install-dir', home, gem)
  abort "#{gem}: gem install failed:\n#{out}" unless status.success?
  next if v['OVERRIDE_GEMSPEC'].empty?
  spec = "#{home}/specifications/#{Gem::Package.new(gem).spec.full_name}.gemspec"
  out, status = Open3.capture2e(RbConfig.ruby, "#{tree}/lang/ruby/files/update-gemspec.rb", spec,
                                *v['OVERRIDE_GEMSPEC'].split)
  abort "#{pkgpath}: update-gemspec.rb failed:\n#{out}" unless status.success?
end

src = "#{work}/src"
Dir.mkdir(src)
Dir.mkdir("#{src}/sub")
File.write("#{src}/alpha.txt", "alpha\n")
File.write("#{src}/sub/charlie.txt", "charlie\n" * 100)
# Ruby's own gem directory provides the bundled gems (base64, csv, logger, rexml, ...).
env = { 'GEM_HOME' => home, 'GEM_PATH' => [home, Gem.default_dir].join(File::PATH_SEPARATOR) }
code = <<~'RUBY'
  gem 'train-winrm'
  require 'chef-winrm'
  require 'chef-winrm-fs'
  require 'chef-winrm-fs/core/tmp_zip'
  require 'chef-winrm-elevated'
  require 'socksify'
  puts Gem.loaded_specs.values_at('rubyzip', 'chef-winrm', 'chef-winrm-fs', 'chef-winrm-elevated', 'chef-gyoku',
                            'socksify', 'train-winrm')
          .map { |s| s&.full_name }.join(' ')
  tmp = WinRM::FS::Core::TmpZip.new(ARGV[0])
  Zip::File.open(tmp.path.to_s) do |z|
    z.entries.sort_by(&:name).each { |e| puts "#{e.name} #{e.size} #{e.compression_method}" }
    puts z.read('sub/charlie.txt') == "charlie\n" * 100 ? 'content ok' : 'content BAD'
  end
  tmp.unlink
RUBY
out, status = Open3.capture2e(env, RbConfig.ruby, '-e', code, src)
File.write("#{work}/load.out", out)
abort "WinRM does not load or zip with rubyzip #{zip_version}:\n#{out}" unless status.success?
lines = out.lines.map(&:strip)
abort "WinRM did not load rubyzip #{zip_version}:\n#{out}" unless lines.first.start_with?("rubyzip-#{zip_version} ")
['alpha.txt 6 8', 'sub/charlie.txt 800 8', 'content ok'].each do |line|
  abort "TmpZip output lacks #{line}:\n#{out}" unless lines.include?(line)
end
puts lines.first
puts "PASS: chef-winrm, chef-winrm-fs, chef-winrm-elevated, socksify and train-winrm load with rubyzip #{zip_version} and TmpZip writes a deflated zip"
