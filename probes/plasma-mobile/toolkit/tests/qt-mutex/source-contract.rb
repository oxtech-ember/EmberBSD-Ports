#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted actual-source Qt mutex contract runner.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'Usage: source-contract.rb QTBASE_ARCHIVE NEW_OUTPUT' unless ARGV.length == 2
archive, output = ARGV.map { |path| File.expand_path(path) }
recipe = File.expand_path('../../recipes/x11/qt6-qtbase', __dir__)
distinfo = File.read(File.join(recipe, 'distinfo'))
patches = %w[patch-src_corelib_thread_qmutex__p.h patch-src_corelib_thread_qmutex__unix.cpp]
patches.each do |name|
  expected = distinfo[/^SHA1 \(#{Regexp.escape(name)}\) = (\h+)$/, 1]
  canonical = File.readlines(File.join(recipe, 'patches', name)).reject { |line| line.match?(/\$NetBSD.*/) }.join
  abort "Patch hash mismatch: #{name}" unless expected && Digest::SHA1.hexdigest(canonical) == expected
end
expected = distinfo[/^SHA512 \(qtbase-everywhere-src-6\.12\.0\.tar\.xz\) = (\h+)$/, 1]
abort 'Wrong Qt 6.12.0 archive' unless expected && Digest::SHA512.file(archive).hexdigest == expected
Dir.mkdir(output)
def run(command)
  out, err, status = Open3.capture3(*command)
  raise "#{command.inspect}: #{out}#{err}" unless status.success?
  out
end
def run_case(environment, command)
  Open3.popen3(environment, *command, pgroup: true) do |input, output, errors, waiter|
    input.close
    stdout = Thread.new { output.read }
    stderr = Thread.new { errors.read }
    unless waiter.join(30)
      begin
        Process.kill('TERM', -waiter.pid)
      rescue Errno::ESRCH
      end
      unless waiter.join(2)
        Process.kill('KILL', -waiter.pid)
        waiter.join
      end
      raise "Timed out after 30 seconds: #{command.inspect}"
    end
    [stdout.value, stderr.value, waiter.value]
  end
end
pkgconfig = Shellwords.split(ENV.fetch('PKG_CONFIG', 'pkg-config'))
cxx = Shellwords.split(ENV.fetch('CXX', 'c++'))
version = run(pkgconfig + %w[--modversion Qt6Core]).strip
abort "Host Qt #{version} must match 6.12.0" unless version == '6.12.0'
includes = run(pkgconfig + %w[--variable=includedir Qt6Core]).strip
libdir = run(pkgconfig + %w[--variable=libdir Qt6Core]).strip
private_headers = [File.join(includes, 'QtCore', version), File.join(libdir, 'QtCore.framework/Headers', version)].find do |candidate|
  File.file?(File.join(candidate, 'QtCore/private/qglobal_p.h'))
end
abort 'Matching host Qt private headers are required' unless private_headers
cflags = Shellwords.split(run(pkgconfig + %w[--cflags Qt6Core]))
framework_headers = File.join(libdir, 'QtCore.framework/Headers')
cflags.unshift("-I#{framework_headers}") if File.file?(File.join(framework_headers, 'qglobal.h'))
libs = Shellwords.split(run(pkgconfig + %w[--libs Qt6Core]))
commands = []
%w[baseline fixed fixed-clock].each do |variant|
  root = File.join(output, variant)
  source = File.join(root, 'src/corelib/thread')
  FileUtils.mkdir_p(source)
  %w[qmutex.cpp qmutex_unix.cpp qmutex_p.h].each do |file|
    content = run(['tar', '-xOf', archive, "qtbase-everywhere-src-6.12.0/src/corelib/thread/#{file}"])
    File.write(File.join(source, file), content)
  end
  if variant != 'baseline'
    patches.each do |patch|
      run(['patch', '--batch', '-p0', '-d', root, '-i', File.join(recipe, 'patches', patch)])
    end
  end
  original = File.read(File.join(source, 'qmutex.cpp'))
  constants = original[/^struct FreeListConstants : QFreeListDefaultConstants \{.*?^\};\nQ_CONSTINIT const int FreeListConstants::Sizes.*?^\};/m]
  abort 'Missing actual mutex free-list constants' unless constants
  File.write(File.join(root, 'freelist-constants.h'), constants + "\n")
  args = cxx + %w[-std=c++20 -g -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -pthread]
  args << '-DTEST_FIXED' if variant != 'baseline'
  args << '-DTEST_COND_CLOCK' if variant == 'fixed-clock'
  args += cflags + ["-I#{private_headers}", "-I#{private_headers}/QtCore", "-I#{source}", "-I#{root}", File.join(__dir__, 'contract.cpp'), '-o', File.join(root, 'contract')] + libs
  commands << args
  out, err, status = Open3.capture3(*args)
  File.write(File.join(root, 'build.log'), out + err)
  File.write(File.join(output, 'commands.json'), JSON.pretty_generate(commands) + "\n")
  abort out + err unless status.success?
  cases = variant == 'fixed-clock' ? %w[clock attr_setclock] : variant == 'fixed' ? %w[pool event mutex_init attr_init cond_init attr_destroy wait timedwait signal overflow] : %w[pool]
  cases.each do |name|
    out, err, status = run_case({ 'ASAN_OPTIONS' => 'halt_on_error=1', 'UBSAN_OPTIONS' => 'halt_on_error=1' }, [File.join(root, 'contract'), name])
    File.write(File.join(root, "#{name}.log"), out + err)
    if variant == 'baseline'
      abort 'Baseline did not reproduce descriptor pressure' unless status.exitstatus == 1 && out.match?(/sem_failures=[1-9]/) && err.include?('semFailures == 0')
    elsif %w[pool event clock].include?(name)
      abort out + err unless status.success?
    else
      abort out + err unless status.exitstatus == 42 && err.include?('EXPECTED_FATAL')
    end
    puts "#{variant}/#{name}: expected result"
  end
end
