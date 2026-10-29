#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); RSpec 3.13 loads and prints diffs with diff-lcs 2.
require 'open3'
require 'rubygems/package'

usage = 'usage: ruby-rspec-diff-lcs.rb EXPORTED_PKGSRC MAKECONF DISTDIR NEW_WORK (BMAKE, PKG_ADMIN)'
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

lcs = vars(tree, makeconf, 'textproc/ruby-diff-lcs', 'PKGNAME', 'PKG_FAIL_REASON')
abort "textproc/ruby-diff-lcs: #{lcs['PKG_FAIL_REASON']}" unless lcs['PKG_FAIL_REASON'].empty?
version = lcs['PKGNAME'][/-([0-9][^-]*)\z/, 1].sub(/nb\d+\z/, '')
abort "textproc/ruby-diff-lcs is #{version}, not 2.x" unless version.start_with?('2.')

# Install the five gems as gem.mk does: the distfile's gemspec with OVERRIDE_GEMSPEC applied.
home = "#{work}/gems"
%w[textproc/ruby-diff-lcs devel/ruby-rspec-support devel/ruby-rspec-core
   devel/ruby-rspec-expectations devel/ruby-rspec-mocks].each do |pkgpath|
  v = vars(tree, makeconf, pkgpath, 'PKG_FAIL_REASON', 'DEPENDS', 'DISTFILES', 'OVERRIDE_GEMSPEC')
  abort "#{pkgpath}: #{v['PKG_FAIL_REASON']}" unless v['PKG_FAIL_REASON'].empty?
  pattern = v['DEPENDS'].split.map { |dep| dep.split(':') }
                        .find { |_, dir| dir == '../../textproc/ruby-diff-lcs' }&.first
  if pattern
    _, status = Open3.capture2e(ENV['PKG_ADMIN'], 'pmatch', pattern, lcs['PKGNAME'])
    abort "#{pkgpath}: #{pattern} rejects #{lcs['PKGNAME']}" unless status.success?
  end
  gem = "#{distdir}/#{v['DISTFILES'].split.first}"
  out, status = Open3.capture2e(RbConfig.ruby, "-rrubygems/gem_runner", "-e", "Gem::GemRunner.new.run(ARGV)", "install", '--local', '--ignore-dependencies',
                                '--no-document', '--install-dir', home, gem)
  abort "#{gem}: gem install failed:\n#{out}" unless status.success?
  next if v['OVERRIDE_GEMSPEC'].empty?
  spec = "#{home}/specifications/#{Gem::Package.new(gem).spec.full_name}.gemspec"
  out, status = Open3.capture2e(RbConfig.ruby, "#{tree}/lang/ruby/files/update-gemspec.rb", spec,
                                *v['OVERRIDE_GEMSPEC'].split)
  abort "#{pkgpath}: update-gemspec.rb failed:\n#{out}" unless status.success?
end

File.write("#{work}/diff_spec.rb", <<~'SPEC')
  RSpec.describe 'diff-lcs 2' do
    it('passes') { expect([1, 2]).to eq([1, 2]) }
    it('diffs strings') { expect("alpha\nbeta\ngamma\n").to eq("alpha\nBETA\ngamma\n") }
    it('diffs hashes') { expect({ a: 1, b: 2 }).to eq({ a: 1, b: 3 }) }
    it 'diffs mock arguments' do
      double = double('service')
      expect(double).to receive(:call).with("one\ntwo\n")
      double.call("one\nthree\n")
    end
  end
SPEC
env = { 'GEM_HOME' => home, 'GEM_PATH' => home }
code = "gem 'rspec-expectations'; gem 'rspec-mocks'; gem 'rspec-core'; " \
       "puts Gem.loaded_specs.values_at('diff-lcs', 'rspec-expectations', 'rspec-mocks').map(&:full_name).join(' '); " \
       "require 'rspec/core'; exit RSpec::Core::Runner.run(['--no-color', ARGV[0]])"
out, status = Open3.capture2e(env, RbConfig.ruby, '-e', code, "#{work}/diff_spec.rb")
File.write("#{work}/rspec.out", out)
abort "RSpec does not load with diff-lcs #{version}:\n#{out}" unless out.start_with?("diff-lcs-#{version} ")
abort "RSpec did not run the examples:\n#{out}" unless status.exitstatus == 1 && out.include?('4 examples, 3 failures')
lines = out.lines.map(&:strip)
['@@ -1,3 +1,3 @@', '-BETA', '+beta', '-:b => 3,', '+:b => 2,', '-two', '+three'].each do |line|
  abort "RSpec output lacks the diff line #{line}:\n#{out}" unless lines.include?(line)
end
puts out.lines.first
puts "PASS: RSpec 3.13 loads diff-lcs #{version} and prints string, hash and mock argument diffs"
