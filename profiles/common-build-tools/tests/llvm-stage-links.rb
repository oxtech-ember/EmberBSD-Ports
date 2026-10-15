#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the actual stage selector link lifetime.
require 'fileutils'
require 'find'
require 'open3'
abort 'Usage: llvm-stage-links.rb SELECTOR NEW_OUTPUT' unless ARGV.length == 2
helper = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'new absolute output required' unless ARGV[1].start_with?('/') && !File.exist?(work)
Dir.mkdir(work)
full = %w[lib/runtime.so lib/runtime-alias.so lib/sdk.a lib/sdk-alias.a]
runtime = full.first(2)
sdk = full.last(2)
cases = [
  ['normal-runtime', 'runtime', 'runtime.so', 'runtime.so', true],
  ['sdk-to-runtime', 'devel', 'runtime.so', 'runtime.so', true],
  ['runtime-to-sdk', 'runtime', 'sdk.a', 'runtime.so', false],
  ['runtime-via-sdk', 'runtime', 'sdk-alias.a', 'runtime.so', false],
  ['parent-link', 'runtime', '../lib/runtime.so', 'runtime.so', true],
  ['file-slash', 'runtime', 'runtime.so/', 'runtime.so', false],
  ['absolute-link', 'runtime', '/lib/runtime.so', 'runtime.so', false],
  ['escaping-link', 'runtime', '../../outside', 'runtime.so', false],
  ['missing-link', 'runtime', 'missing.so', 'runtime.so', false],
  ['cyclic-link', 'runtime', 'runtime-alias.so', 'runtime.so', false],
  ['sdk-absolute-link', 'devel', 'runtime.so', '/lib/runtime.so', false]
]
snapshot = lambda do |stage|
  paths = {}
  Find.find(stage) do |path|
    next if File.directory?(path) && !File.symlink?(path)
    paths[path.delete_prefix(stage + '/')] = File.symlink?(path) ? ['link', File.readlink(path)] : ['file', File.binread(path)]
  end
  paths
end
cases.each do |label, part, runtime_link, sdk_link, accepted|
  dir = work + '/' + label
  stage = dir + '/stage'
  FileUtils.mkdir_p(stage + '/lib')
  File.write(stage + '/lib/runtime.so', 'runtime fixture')
  File.write(stage + '/lib/sdk.a', 'SDK fixture')
  File.symlink(runtime_link, stage + '/lib/runtime-alias.so')
  File.symlink(sdk_link, stage + '/lib/sdk-alias.a')
  [full, runtime, sdk, part == 'runtime' ? runtime : sdk].each_with_index do |paths, index|
    File.write(dir + '/' + index.to_s, paths.join("\n") + "\n")
  end
  before = snapshot.call(stage)
  out, status = Open3.capture2e(ENV.fetch('PERL', 'perl'), helper, part, stage, *(0..3).map { |index| dir + '/' + index.to_s })
  File.write(dir + '/result.log', out)
  abort label + ' unexpected status: ' + out unless status.success? == accepted
  after = snapshot.call(stage)
  expected = accepted ? before.select { |name, _| (part == 'runtime' ? runtime : sdk).include?(name) } : before
  abort label + ' changed rejected stage or selected payload' unless after == expected
  puts 'PASS: ' + label
end
puts 'SCOPE: eleven text/symlink fixtures; no target execution'
