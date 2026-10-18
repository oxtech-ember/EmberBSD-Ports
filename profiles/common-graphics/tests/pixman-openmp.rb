#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted actual configured-graph regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'find'
require 'shellwords'

abort 'Usage: pixman-openmp.rb ARCHIVE BASELINE_OUTPUT CURRENT_OUTPUT READELF NEW_RESULTS' unless ARGV.size == 5
archive, before, after, readelf = ARGV.first(4).map { |p| File.realpath(p) }
results = File.join(File.realpath(File.dirname(ARGV.last)), File.basename(ARGV.last))
abort 'results overlap configured sources' if [before, after].any? { |d| results == File.dirname(d) || results.start_with?(File.dirname(d) + '/') }
abort 'results already exist' if File.exist?(results) || File.symlink?(results)
abort 'wrong pixman archive' unless Digest::SHA256.file(archive).hexdigest ==
  'a098c33924754ad43f981b740f6d576c70f9ed1006e12221b1845431ebce1239'
abort 'same configured graph' if before == after
FileUtils.mkdir_p(results)
inputs = [archive, readelf]
read = lambda do |path|
  inputs << path
  File.binread(path)
end
load_json = ->(dir, name) { JSON.parse(read.call(dir + '/meson-info/intro-' + name + '.json')) }
# Compare every archived source file, excluding only the generated build output.
source_count = 0
stdout, stderr, status = Open3.capture3('tar', '-xJf', archive, '-C', results)
File.write(results + '/extract.stdout', stdout)
File.write(results + '/extract.stderr', stderr)
abort 'archive extraction failed' unless status.success?
pristine = results + '/pixman-0.46.4'
Find.find(pristine) do |original|
  next if File.directory?(original) && !File.symlink?(original)
  relative = original.delete_prefix(pristine + '/')
  [before, after].each do |dir|
    path = File.dirname(dir) + '/' + relative
    if File.symlink?(original)
      abort 'source link changed: ' + path unless File.symlink?(path) && File.readlink(path) == File.readlink(original)
    else
      abort 'source bytes changed: ' + path unless File.file?(path) && !File.symlink?(path) && read.call(path) == File.binread(original)
    end
  end
  source_count += 1
end
options = [before, after].map { |d| load_json.call(d, 'buildoptions').to_h { |o| [o['name'], o['value']] } }
abort 'OpenMP feature selection differs' unless options[0]['openmp'] == 'disabled' && options[1]['openmp'] == 'auto'
abort 'unrelated feature selection changed' unless options[0].reject { |k, _| k == 'openmp' } == options[1].reject { |k, _| k == 'openmp' }
[before, after].each do |dir|
  machine = load_json.call(dir, 'machines')['host']
  compiler = load_json.call(dir, 'compilers')['host']['c']
  abort 'expected actual GCC16 AArch64 NetBSD graph' unless
    machine.values_at('system', 'cpu_family') == %w[netbsd aarch64] &&
    compiler.values_at('id', 'version') == %w[gcc 16.2.0]
  config = read.call(dir + '/pixman/pixman-config.h')
  %w[USE_ARM_A64_NEON USE_GCC_INLINE_ASM].each do |name|
    abort 'missing enabled feature ' + name unless config.include?("#define #{name} 1\n")
  end
  abort 'wrong OpenMP define' unless config.include?("#define USE_OPENMP 1\n") == (dir == after)
end
normalize = ->(object, dir) { JSON.generate(object).gsub(File.dirname(dir), '@SOURCE@') }
tests = [before, after].map { |d| load_json.call(d, 'tests') }
abort 'upstream test graph changed' unless normalize.call(tests[0], before) == normalize.call(tests[1], after)
targets = [before, after].map do |d|
  load_json.call(d, 'targets').map { |t| t.slice('name', 'type', 'filename', 'build_by_default', 'installed') }
end
abort 'default target graph changed' unless normalize.call(targets[0], before) == normalize.call(targets[1], after)
commands = [before, after].map do |d|
  rows = JSON.parse(read.call(d + '/compile_commands.json'))
  abort 'compile database directory differs' unless rows.all? { |c| c['directory'] == d }
  rows
end
strip_openmp = lambda do |rows|
  rows.map { |c| [c['file'], c['output'], Shellwords.split(c['command']).reject { |a| a == '-fopenmp' }] }
end
abort 'unrelated compiler arguments changed' unless strip_openmp.call(commands[0]) == strip_openmp.call(commands[1])
abort 'baseline already used OpenMP' if commands[0].any? { |c| Shellwords.split(c['command']).include?('-fopenmp') }
openmp = commands[1].select { |c| Shellwords.split(c['command']).include?('-fopenmp') }
abort 'missing test OpenMP or changed rendering flags' unless !openmp.empty? && openmp.all? { |c| c['file'].start_with?('../test/') }
elf = []
targets[1].select { |t| t['build_by_default'] }.each do |target|
  target['filename'].each do |path|
    abort 'default build output missing: ' + path unless File.file?(path)
    next if target['type'] == 'static library'
    stdout, stderr, status = Open3.capture3({ 'LC_ALL' => 'C' }, readelf, '-h', '-d', '-W', path)
    File.write(results + '/' + target['name'] + '.readelf', stdout + stderr)
    abort 'invalid target ELF' unless status.success? && stderr.empty? && stdout.match?(/Machine:\s+AArch64/)
    inputs << path
    elf << { name: target['name'], sha256: Digest::SHA256.file(path).hexdigest,
             needed: stdout.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten }
  end
end
abort 'test programs do not link real libgomp' unless elf.any? { |e| e[:needed].include?('libgomp.so.1') }
abort 'unexpected library OpenMP dependency' if elf.find { |e| e[:name] == 'pixman-1' }.fetch(:needed).include?('libgomp.so.1')
File.write(results + '/result.json', JSON.pretty_generate({
  scope: 'Pinned upstream bytes and actual normal target configure/build graphs. No target test execution or package installation.',
  source_entries: source_count, tests: tests[1].size, default_targets: targets[1].count { |t| t['build_by_default'] },
  compile_commands: commands[1].size, openmp_test_commands: openmp.size, elf: elf,
  inputs: inputs.uniq.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
  helper_sha256: Digest::SHA256.file(__FILE__).hexdigest
}) + "\n")
puts 'PASS: automatic OpenMP, unchanged sources/test graph, NEON/GNU assembly and actual target outputs.'
