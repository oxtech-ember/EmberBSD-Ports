#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted gettext compiler-discovery regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: gettext-go-detection.rb ORIGINAL_GOCOMP_M4 PATCHED_GOCOMP_M4 NEW_WORK' unless ARGV.size == 3
original, patched = ARGV.first(2).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'Output must be a new absolute directory' unless ARGV.last == work && !File.exist?(work) && !File.symlink?(work)
Dir.mkdir(work)
records = []
run = lambda do |name, directory, environment, argv|
  out, err, status = Open3.capture3(environment, *argv, chdir: directory)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  records << { name: name, argv: argv, status: status.exitstatus, signal: status.termsig }
  File.write(work + '/commands.json', JSON.pretty_generate(records) + "\n")
  abort "#{name} failed: #{err}" unless status.success?
  out
end
autoconf = ENV.fetch('AUTOCONF', 'autoconf')
version = run.call('autoconf-version', work, {}, [autoconf, '--version'])
{ 'before' => original, 'after' => patched }.each do |name, input|
  directory = work + '/' + name
  Dir.mkdir(directory)
  FileUtils.cp(input, directory + '/gocomp.m4')
  File.write(directory + '/configure.ac', <<~M4)
    AC_INIT([gettext-go-detection-test], [1])
    m4_include([gocomp.m4])
    gt_GOCOMP
    AC_CONFIG_FILES([choice])
    AC_OUTPUT
  M4
  File.write(directory + '/choice.in', "GO=@GO@\nFLAGS=@GOCOMPFLAGS@\n")
  run.call(name + '-autoconf', directory, {}, [autoconf])
end
fixtures = work + '/fixtures'
Dir.mkdir(fixtures)
{
  'wrong' => "echo 'board game'\nexit 0",
  'failed' => "echo 'go version go1.27.1 linux/amd64'\nexit 1",
  'valid' => "echo 'go version go1.27.1 linux/amd64'",
  'gcc' => "echo 'go version go1.23.2 gccgo (GCC) 16.2.0'"
}.each do |name, body|
  Dir.mkdir(fixtures + '/' + name)
  file = fixtures + '/' + name + '/' + (name == 'gcc' ? 'go-16' : 'go')
  File.write(file, "#!/bin/sh\n# Discovery fixture. This is not a Go compiler.\n[ \"${1-}\" = version ] || exit 2\n" + body + "\n")
  File.chmod(0o755, file)
end
# Give the absent-compiler check real configure utilities, without a Go tool.
utilities = fixtures + '/utilities'
Dir.mkdir(utilities)
%w[awk basename cat chmod cp dirname expr grep ls mkdir mv rm rmdir sed sleep sort tr uname].each do |name|
  provider = ENV.fetch('PATH').split(File::PATH_SEPARATOR).map { |dir| File.join(dir, name) }.find { |path| File.file?(path) && File.executable?(path) }
  abort "Missing host utility: #{name}" unless provider
  File.symlink(File.realpath(provider), utilities + '/' + name)
end
cases = [
  ['baseline-name-only', 'before', [fixtures + '/wrong', utilities], [], fixtures + '/wrong/go'],
  ['no-compiler', 'after', [utilities, fixtures + '/wrong'], [], ''],
  ['wrong-before-valid', 'after', [fixtures + '/wrong', fixtures + '/valid', utilities], [], fixtures + '/valid/go'],
  ['failed-before-valid', 'after', [fixtures + '/failed', fixtures + '/valid', utilities], [], fixtures + '/valid/go'],
  ['gcc-preference', 'after', [fixtures + '/valid', fixtures + '/gcc', utilities], ['--enable-go=gcc'], fixtures + '/gcc/go-16'],
  ['golang-preference', 'after', [fixtures + '/gcc', fixtures + '/valid', utilities], [], fixtures + '/valid/go'],
  ['explicit-provider', 'after', [utilities], ['GO=' + fixtures + '/valid/go'], fixtures + '/valid/go']
]
results = cases.map do |name, variant, path, args, expected|
  directory = work + '/' + name
  Dir.mkdir(directory)
  environment = { 'PATH' => path.join(File::PATH_SEPARATOR), 'GO' => nil, 'ac_cv_path_GO' => nil }
  run.call(name, directory, environment, [work + '/' + variant + '/configure', *args])
  actual = File.read(directory + '/choice').lines.first.chomp.delete_prefix('GO=')
  abort "#{name}: #{actual.inspect} != #{expected.inspect}" unless actual == expected
  { name: name, selected: actual, expected: expected }
end
File.write(work + '/result.json', JSON.pretty_generate(
  inputs: [original, patched].to_h { |path| [path, Digest::SHA256.file(path).hexdigest] },
  autoconf_version: version.lines.first.chomp, checks: results,
  scope: 'Actual Autoconf discovery only. Positive fixtures do not compile Go.'
) + "\n")
puts "PASS: #{results.size} before/after Go compiler-discovery checks"
