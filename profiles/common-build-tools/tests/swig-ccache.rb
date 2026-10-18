#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); genuine CCache compiler/error-path contract.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'Usage: swig-ccache.rb SWIG_SOURCE CCACHE GCC16_CC NEW_WORK' unless ARGV.size == 4
source, cache, cc = ARGV.take(3).map { |p| File.realpath(p) }
out = File.expand_path(ARGV[3])
abort 'Output exists.' if File.exist?(out) || File.symlink?(out)
FileUtils.mkdir_p(out)
input = source + '/Examples/python/simple/example.c'
abort 'Missing upstream example.' unless File.file?(input)
commands = []
env = { 'LC_ALL' => 'C', 'CCACHE_DIR' => out + '/cache', 'CCACHE_COMPRESS' => '1', 'CCACHE_VERBOSE' => '1' }
record = lambda do |name, argv, stdout, stderr, status|
  File.write(out + '/' + name + '.stdout', stdout)
  File.write(out + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, status: status.exitstatus, signal: status.termsig }
  File.write(out + '/commands.json', JSON.pretty_generate(commands) + "\n")
  abort 'Failed: ' + name unless status.success?
end
argv = [cc, '-dumpfullversion']
stdout, stderr, status = Open3.capture3(env, *argv)
record.call('compiler-version', argv, stdout, stderr, status)
abort 'Use GCC16.' unless stdout.strip.match?(/\A16\./)
argv = [cache, cc, '-O2', '-c', input, '-o', out + '/closed.o']
# The regression closes the real inherited descriptor before the program starts.
# Disable core dumps so a failing baseline does not leave a large artifact.
stdout, status = Open3.capture2(env, *argv, err: :close, rlimit_core: 0)
record.call('closed-stderr', argv, stdout, '', status)
%w[miss hit].each do |name|
  argv = [cache, cc, '-O2', '-c', input, '-o', out + '/' + name + '.o']
  stdout, stderr, status = Open3.capture3(env, *argv)
  record.call(name, argv, stdout, stderr, status)
end
argv = [cache, '-s']
stdout, stderr, status = Open3.capture3(env, *argv)
record.call('statistics', argv, stdout, stderr, status)
abort 'Expected a genuine cache miss and hit.' unless stdout.match?(/^cache hit\s+1$/) && stdout.match?(/^cache miss\s+1$/)
object = Digest::SHA256.file(out + '/closed.o').hexdigest
abort 'Compiler and cache results differ.' unless %w[miss hit].all? { |name| Digest::SHA256.file(out + '/' + name + '.o').hexdigest == object }
File.write(out + '/result.json', JSON.pretty_generate({
  scope: 'Real GCC16 compilation with closed stderr and compressed cache miss/hit; no target or memory acceptance.',
  input_sha256: Digest::SHA256.file(input).hexdigest,
  cache_sha256: Digest::SHA256.file(cache).hexdigest, object_sha256: object, commands: commands
}) + "\n")
puts 'PASS: closed-stderr compiler fallback and genuine compressed cache produce identical objects.'
