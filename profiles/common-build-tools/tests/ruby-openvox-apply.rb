#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); the one kept Puppet (OpenVox) and Facter (OpenFact) run on the kept Ruby.
require 'json'
require 'open3'
require 'fileutils'
require 'rubygems/package'

usage = 'usage: ruby-openvox-apply.rb EXPORTED_PKGSRC MAKECONF DISTDIR NEW_WORK (BMAKE, PKG_ADMIN, PATCH)'
abort usage unless ARGV.length == 4 && ENV['BMAKE'] && ENV['PKG_ADMIN'] && ENV['PATCH']
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

PUPPET = 'sysutils/openvox'
FACTER = 'sysutils/ruby-openfact'
# pkgsrc/versions.mk redirects the old names; the export must not ship them.
%w[sysutils/puppet sysutils/ruby-facter devel/ruby-concurrent-ruby11].each do |old|
  abort "the export still has #{old}" if File.exist?("#{tree}/#{old}")
end

# Walk the Ruby DEPENDS of OpenVox and install every gem from its distfile.
home = "#{work}/gems"
queue = [PUPPET]
seen = {}
until queue.empty?
  pkgpath = queue.shift
  next if seen[pkgpath]
  abort "#{pkgpath} is not in the export" unless File.exist?("#{tree}/#{pkgpath}/Makefile")
  v = vars(tree, makeconf, pkgpath, 'PKGNAME', 'PKG_FAIL_REASON', 'DEPENDS', 'DISTFILES', 'OVERRIDE_GEMSPEC',
           'RUBY_SUFFIX', 'PATCHDIR', 'SUBST_FILES.sufx')
  abort "#{pkgpath}: #{v['PKG_FAIL_REASON']}" unless v['PKG_FAIL_REASON'].empty?
  seen[pkgpath] = v
  v['DEPENDS'].split.each do |dep|
    pattern, dir = dep.split(':')
    dep_path = dir.delete_prefix('../../')
    next unless File.basename(dep_path).start_with?('ruby-')
    target = vars(tree, makeconf, dep_path, 'PKGNAME')['PKGNAME']
    _, status = Open3.capture2e(ENV['PKG_ADMIN'], 'pmatch', pattern, target)
    abort "#{pkgpath}: #{pattern} rejects #{target}" unless status.success?
    queue << dep_path
  end
end
abort "#{PUPPET} does not pull in #{FACTER}" unless seen[FACTER]

suffix = seen[PUPPET]['RUBY_SUFFIX']
bindir = "#{work}/bin"
seen.each do |pkgpath, v|
  gem = "#{distdir}/#{v['DISTFILES'].split.first}"
  spec = Gem::Package.new(gem).spec
  abort "#{pkgpath}: #{spec.full_name} has a native extension" unless spec.extensions.empty?
  # gem.mk installs with --format-executable, which names puppet and facter after the Ruby suffix.
  out, status = Open3.capture2e(RbConfig.ruby, '-rrubygems/gem_runner', '-e', 'Gem::GemRunner.new.run(ARGV)',
                                'install', '--local', '--ignore-dependencies', '--no-document', '--format-executable',
                                '--install-dir', home, '--bindir', bindir, gem)
  abort "#{gem}: gem install failed:\n#{out}" unless status.success?
  dir = "#{home}/gems/#{spec.full_name}"
  # The recipe patches and the RUBY_SUFFIX substitution, as the package build applies them.
  Dir.glob("#{v['PATCHDIR']}/patch-*").sort.each do |patch|
    out, status = Open3.capture2e(ENV['PATCH'], '-p0', '-N', '-s', '-V', 'none', '-d', dir, '-i', patch)
    abort "#{pkgpath}: #{File.basename(patch)} does not apply to #{spec.full_name}:\n#{out}" unless status.success?
  end
  v['SUBST_FILES.sufx'].split.each do |file|
    path = "#{dir}/#{file}"
    File.write(path, File.read(path).gsub('@RUBY_SUFFIX@', suffix))
  end
  next if v['OVERRIDE_GEMSPEC'].empty?
  out, status = Open3.capture2e(RbConfig.ruby, "#{tree}/lang/ruby/files/update-gemspec.rb",
                                "#{home}/specifications/#{spec.full_name}.gemspec", *v['OVERRIDE_GEMSPEC'].split)
  abort "#{pkgpath}: update-gemspec.rb failed:\n#{out}" unless status.success?
end

puppet = "#{bindir}/puppet#{suffix}"
facter = "#{bindir}/facter#{suffix}"
[puppet, facter].each { |bin| abort "#{bin} was not installed" unless File.executable?(bin) }
# Ruby's own gem directory provides the bundled gems (base64, getoptlong, ostruct, racc, ...).
env = { 'HOME' => "#{work}/home", 'GEM_HOME' => home,
        'GEM_PATH' => [home, Gem.default_dir].join(File::PATH_SEPARATOR) }
Dir.mkdir(env['HOME'])
run = lambda do |*cmd|
  out, err, status = Open3.capture3(env, RbConfig.ruby, *cmd)
  abort "#{File.basename(cmd.first)} #{cmd.drop(1).join(' ')} failed:\n#{out}#{err}" unless status.success?
  out
end

facts = JSON.parse(run.call(facter, '--json', 'ruby', 'kernel', 'os.family'))
abort "facter reports Ruby #{facts['ruby']&.dig('version')}, not #{RUBY_VERSION}" unless
  facts.dig('ruby', 'version') == RUBY_VERSION
abort "facter reports no kernel: #{facts}" if facts['kernel'].to_s.empty?
puts "facter#{suffix}: ruby.version=#{facts.dig('ruby', 'version')} kernel=#{facts['kernel']}"

version = run.call(puppet, '--version').strip
wanted = seen[PUPPET]['PKGNAME'][/-([0-9][^-]*)\z/, 1].sub(/nb\d+\z/, '')
abort "puppet#{suffix} --version is #{version}, not #{wanted}" unless version == wanted
target = "#{work}/x"
run.call(puppet, 'apply', '--color=false', '-e', "file { '#{target}': content => 'ok' }")
abort "puppet#{suffix} apply did not write #{target}" unless File.exist?(target) && File.read(target) == 'ok'
puts "puppet#{suffix} #{version}: apply wrote the file"
puts "PASS: #{File.basename(facter)} prints facts and #{File.basename(puppet)} applies a manifest on Ruby #{RUBY_VERSION}"
