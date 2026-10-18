#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run actual upstream source before and after the fix.
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'usage: check-stacktrace.rb ORIGINAL_SOURCE PATCHED_SOURCE GENERATED_INCLUDE NEW_WORK' unless ARGV.size == 4
original, patched, headers, work = ARGV.map { |path| File.expand_path(path) }
abort 'work exists' if File.exist?(work) || File.symlink?(work)
FileUtils.mkdir_p(work)
compiler = Shellwords.split(ENV.fetch('CXX', 'c++'))
flags = %w[-std=c++17 -O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined -fno-sanitize-recover=all -Wall -Wextra]
test = File.join(__dir__, 'stacktrace.cxx')
results = []
{before: original, after: patched}.each do |name, source|
  binary = work + '/' + name.to_s
  unit = source + '/src/FoundationClasses/TKernel/Standard/Standard_StackTrace.cxx'
  command = [*compiler, *flags, '-I'+headers, unit, test, '-o', binary]
  output, error, status = Open3.capture3(*command)
  File.write(work + '/' + name.to_s + '-build.log', output + error)
  abort "#{name} compile failed" unless status.success?
  %w[unterminated capacity overflow skip-overflow exhausted valid].each do |mode|
    out, err, st = Open3.capture3({'ASAN_OPTIONS'=>'detect_leaks=1:halt_on_error=1', 'UBSAN_OPTIONS'=>'halt_on_error=1'}, binary, mode)
    File.write(work + '/' + name.to_s + '-' + mode + '.log', out + err)
    causal = mode != 'valid'
    if name == :before && causal
      diagnostic = mode == 'capacity' ? /declared capacity contract violated/ : /AddressSanitizer|runtime error: signed integer overflow/
      abort "#{mode}: baseline did not expose the defect" unless !st.success? && (out+err).match?(diagnostic)
    else
      abort "#{name} #{mode} failed: #{st.exitstatus}" unless st.success?
    end
    results << {version: name, case: mode, exit: st.exitstatus, signal: st.termsig, causal_negative: name == :before && causal}
  end
end
File.write(work + '/results.json', JSON.pretty_generate({compiler: compiler, flags: flags, results: results}) + "\n")
puts 'Actual OCCT stack trace: five causal failures before; six cases pass after.'
