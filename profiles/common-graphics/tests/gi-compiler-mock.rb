#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted upstream test compatibility regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

abort 'Usage: gi-compiler-mock.rb BUILD_OUTPUT GNOME_ARCHIVE NATIVE_PYTHON NEW_RESULTS' unless ARGV.size == 4
build, archive, python, results = ARGV
build, archive, python = [build, archive, python].map { |p| File.realpath(p) }
abort 'results already exist' if File.exist?(results) || File.symlink?(results)
FileUtils.mkdir_p(results)
results = File.realpath(results)
abort 'wrong GNOME archive' unless Digest::SHA256.file(archive).hexdigest ==
  '920d1a3fcedeadc32acff95c2e203b319039dd4b4a08dd1a2dfd283d19c0b9ae'
abort 'missing configured scanner extension' if Dir[build + '/giscanner/_giscanner*.so'].empty?
patch = File.expand_path('../../../pkgsrc/devel/gobject-introspection/patches/patch-tests_scanner_test_ccompiler.py', __dir__)
relative = 'tests/scanner/test_ccompiler.py'
commands = []
run = lambda do |name, argv, cwd, env = {}|
  stdout, stderr, status = Open3.capture3(env, *argv, chdir: cwd)
  File.write(results + '/' + name + '.stdout', stdout)
  File.write(results + '/' + name + '.stderr', stderr)
  commands << { name: name, argv: argv, directory: cwd, environment: env,
                status: status.exitstatus, signal: status.termsig }
  File.write(results + '/commands.json', JSON.pretty_generate(commands) + "\n")
  [stdout, stderr, status]
end
%w[baseline patched].each do |variant|
  dir = results + '/' + variant
  Dir.mkdir(dir)
  _, _, status = run.call('extract-' + variant,
    ['tar', '-xJf', archive, '-C', dir, 'gobject-introspection-1.86.0/' + relative], results)
  abort 'extract failed' unless status.success?
end
before = results + '/baseline/gobject-introspection-1.86.0'
after = results + '/patched/gobject-introspection-1.86.0'
_, _, status = run.call('patch', ['patch', '--batch', '--fuzz=0', '-p0', '-i', patch], after)
abort 'patch failed' unless status.success?
configured = File.dirname(build) + '/' + relative
abort 'configured test differs from either verified variant' unless
  [before, after].any? { |p| File.binread(p + '/' + relative) == File.binread(configured) }
env = { 'PYTHONPATH' => build, 'PYTHONDONTWRITEBYTECODE' => '1', 'LC_ALL' => 'C' }
_, _, version_status = run.call('python-version', [python, '--version'], results, env)
abort 'native Python failed' unless version_status.success?
_, old_error, old_status = run.call('baseline-test', [python, '-B', before + '/' + relative], results, env)
_, new_error, new_status = run.call('patched-test', [python, '-B', after + '/' + relative], results, env)
abort 'expected current-setuptools baseline failure was not reproduced' unless
  !old_status.success? && old_error.include?('my-preprocessor') &&
  old_error.include?('FAILED (errors=13, skipped=2, expected failures=2)')
abort 'patched upstream argument tests failed' unless new_status.success? &&
  new_error.include?('Ran 19 tests') && new_error.include?('OK (skipped=2, expected failures=2)')
abort 'baseline test count changed' unless old_error.include?('Ran 19 tests')
inputs = [archive, python, patch, configured, build + '/giscanner/ccompiler.py'] +
  Dir[build + '/giscanner/_giscanner*.so'] +
  Dir[File.dirname(File.dirname(python)) + '/lib/python*/site-packages/setuptools/_distutils/compilers/C/{base,unix}.py']
File.write(results + '/result.json', JSON.pretty_generate({
  scope: 'Actual upstream compiler argument tests against the configured native scanner and current setuptools. No library or package rebuild, target execution or older-distutils run.',
  tests: 19, preserved_skips: 2, preserved_expected_failures: 2,
  baseline_errors: 13, patched_errors: 0,
  inputs: inputs.uniq.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] },
  helper_sha256: Digest::SHA256.file(__FILE__).hexdigest
}) + "\n")
puts 'PASS: all 19 upstream test cases retained; 13 mock failures repaired.'
