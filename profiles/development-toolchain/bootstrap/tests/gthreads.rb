#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual upstream gthreads compile/configure.
require 'shellwords'
require_relative '../rebuild-libstdcxx'

abort 'Usage: gthreads.rb TARGET NEW_PKGSRC OLD_PKGSRC GCC_ARCHIVE APP_PREFIX SYSROOT OLD_WORK NEW_WORK PREPARED_FAILED_WORK' unless ARGV.size == 9
args = ARGV.take(8)
reference = File.realpath(ARGV.last)
abort 'Reference must use a simple absolute path.' unless reference.match?(%r{\A/[A-Za-z0-9_./-]+\z})
work = File.expand_path(args.last)
triplet = GCC16Runtime::TARGETS.fetch(args.first).fetch(:triplet)
source = reference + '/src'
builder = GCC16Runtime::LibstdcxxRebuild.new(['--check', *args])
builder.preflight
build = work + '/build/' + triplet + '/libstdc++-v3'
FileUtils.mkdir_p(build)
logfile = reference + '/build/' + triplet + '/libstdc++-v3/config.log'
log = File.read(logfile)
start = log.index('checking for gthreads library') or abort 'Actual gthreads probe is absent.'
tail = log[start..]
line = tail.lines.find { |text| text.match?(/^configure:\d+: /) && text.include?('conftest.cpp') }
abort 'Actual probe command is absent.' unless line
failed = tail.split("configure: failed program was:\n", 2)[1] or abort 'Expected a failed baseline probe.'
probe = failed.lines.take_while { |text| text.start_with?('|') }.map { |text| text.sub(/^\| ?/, '') }.join
abort 'Unexpected probe source.' unless probe.include?('#include "gthr.h"') && probe.include?('__GTHREADS_CXX0X')
File.write(work + '/probe.cpp', probe)
command = Shellwords.split(line.sub(/^configure:\d+: /, '').sub(/ >&5\s*$/, ''))
compiler = builder.compiler_commands.fetch('CXX').split(' ')
abort 'Recorded probe uses a different compiler.' unless command.take(compiler.size) == compiler
abort 'Expected a compile-only probe.' unless command.count('-c') == 1 && command.count('conftest.cpp') == 1
command.map! do |word|
  word == 'conftest.cpp' ? work + '/probe.cpp' : word.sub(reference + '/build/', work + '/build/')
end
configured = JSON.parse(File.read(reference + '/commands.json'))
abort 'Compiler environment differs.' unless builder.compiler_commands.all? { |key, value| configured.fetch('environment').fetch(key) == value }
abort 'A cached gthreads answer is not allowed.' if configured.fetch('environment').keys.any? { |key| key.match?(/gthread/i) }
results = []
run = lambda do |name, env, argv, directory, success|
  out, err, status = Open3.capture3(env, *argv, chdir: directory)
  File.write(work + '/' + name + '.stdout', out)
  File.write(work + '/' + name + '.stderr', err)
  results << { name: name, argv: argv, environment: env, cwd: directory,
               status: status.exitstatus, signal: status.termsig }
  File.write(work + '/commands.json', JSON.pretty_generate(results) + "\n")
  abort "Unexpected status: #{name}" unless status.success? == success
  err
end
err = run.call('before', {}, command + ['-o', work + '/before.o'], work, false)
abort 'Wrong baseline failure.' unless err.include?('gthr-default.h: No such file or directory')
abort 'Baseline produced an object.' if File.exist?(work + '/before.o')
builder.prepare_gthreads(source)
run.call('fixed', {}, command + ['-o', work + '/fixed.o'], work, true)
elf = File.binread(work + '/fixed.o', 20)
machine = GCC16Runtime::TARGETS.fetch(args.first).fetch(:elf_machine)
abort 'Wrong target ELF.' unless elf.byteslice(0, 7) == "\x7fELF\x02\x01\x01".b && elf.byteslice(18, 2).unpack1('v') == machine
run.call('configure', configured.fetch('environment'),
  [source + '/libstdc++-v3/configure', *configured.fetch('configure')], build, true)
header = build + '/config.h'
abort 'Actual configure did not enable threads.' unless File.readlines(header).include?("#define _GLIBCXX_HAS_GTHREADS 1\n")
paths = [logfile, reference + '/commands.json', source + '/config/gthr.m4',
         source + '/libgcc/Makefile.in', source + '/libgcc/gthr-posix.h',
         source + '/libstdc++-v3/configure', work + '/probe.cpp',
         work + '/build/' + triplet + '/libgcc/gthr-default.h', header]
File.write(work + '/result.json', JSON.pretty_generate(
  scope: 'Actual failed upstream probe, repaired target object and fresh configure; no library build or target execution.',
  machine: machine, has_gthreads: 1,
  inputs: paths.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] }) + "\n")
puts 'PASS: real gthreads probe rejects the missing header, then compiles and enables C++ threads.'
