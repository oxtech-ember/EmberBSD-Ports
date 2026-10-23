#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run real basu functions with a controlled libc result.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'

abort 'Usage: strerror.rb ORIGINAL_SOURCE PATCHED_SOURCE NEW_OUTPUT' unless ARGV.length == 3
original, patched, work = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(work)
compiler = Shellwords.split(ENV.fetch('CC', 'clang'))
source = File.join(__dir__, 'strerror.c')
FileUtils.cp(source, work)
File.write(File.join(work, 'compiler.txt'), Open3.capture2e(*compiler, '--version').first)

run = lambda do |label, command, expected|
  File.write(File.join(work, label + '.command.json'), JSON.pretty_generate(command) + "\n")
  output, status = Open3.capture2e({ 'ASAN_OPTIONS' => 'detect_leaks=1:halt_on_error=1',
                                   'UBSAN_OPTIONS' => 'halt_on_error=1:print_stacktrace=1' }, *command)
  File.write(File.join(work, label + '.log'), output)
  File.write(File.join(work, label + '.status'), "#{status.exitstatus || 128 + status.termsig}\n")
  if expected == :sanitizer_failure
    abort "#{label}: missing causal sanitizer failure\n#{output}" if status.success? ||
      !output.match?(/AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:.*null pointer/)
  else
    abort "#{label} failed\n#{output}" unless status.success?
  end
end

{ 'original' => original, 'patched' => patched }.each do |kind, tree|
  directory = File.join(work, kind)
  Dir.mkdir(directory)
  file = File.join(tree, 'src/libsystemd/sd-bus/bus-error.c')
  text = File.read(file)
  patterns = [/^static char \*_strerror_r\(.*?^\}/m, /^static void bus_error_strerror\(.*?^\}/m]
  functions = patterns.map do |pattern|
    matches = text.scan(pattern)
    abort "Expected one actual function: #{pattern}" unless matches.length == 1
    start = text.index(matches.first)
    "#line #{text[0...start].count("\n") + 1} #{file.dump}\n#{matches.first}\n"
  end
  File.write(File.join(directory, 'strerror-functions.inc'), functions.join("\n"))
  File.write(File.join(directory, 'source.sha256'), "#{Digest::SHA256.file(file).hexdigest}  #{file}\n")
  executable = File.join(directory, 'strerror-test')
  command = [*compiler, '-std=gnu99', '-g', '-O1', '-fno-omit-frame-pointer',
             '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-Wall', '-Wextra',
             '-DHAVE_REALLOCARRAY=1', '-I' + directory, '-I' + File.join(tree, 'src/systemd'),
             '-I' + File.join(tree, 'src/basic'), source, '-o', executable]
  run.call(kind + '-compile', command, :ok)
  if kind == 'original'
    run.call('original-null-error', [executable, 'error', 'constant'], :sanitizer_failure)
  else
    %w[error range full success native].product(%w[constant dynamic]).each do |mode, ownership|
      run.call("patched-#{mode}-#{ownership}", [executable, mode, ownership], :ok)
    end
  end
end
puts 'PASS: original NULL failure; 10 patched ownership/retry cases with ASan, UBSan and leak checks'
