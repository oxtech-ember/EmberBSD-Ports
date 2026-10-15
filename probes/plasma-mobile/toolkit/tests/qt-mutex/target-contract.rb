#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted target Qt mutex compile and ABI check.
require 'json'
require 'fileutils'
require 'open3'
require 'digest'
abort 'Usage: target-contract.rb CROSS_TOOLS SYSROOT SOURCE_CONTRACT_OUTPUT NEW_OUTPUT' unless ARGV.length == 4
tools, sysroot, sources, output = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(output)
qt = File.join(sysroot, 'usr/pkg/qt6')
cxx = File.join(tools, 'bin/aarch64--netbsd-g++')
nm = File.join(tools, 'bin/aarch64--netbsd-nm')
FileUtils.mkdir_p(File.join(output, 'include/global'))
FileUtils.cp(File.join(qt, 'include/QtCore/qglobal.h'), File.join(output, 'include/global/qglobal.h'))
flags = ["--sysroot=#{sysroot}", '-std=c++20', '-fPIC', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
         '-DQT_BUILD_CORE_LIB', '-DQT_BUILDING_QT', '-DNDEBUG', '-fvisibility=hidden', '-fvisibility-inlines-hidden']
flags += [File.join(output, 'include'), File.join(qt, 'include'), File.join(qt, 'include/QtCore'),
          File.join(qt, 'include/QtCore/6.12.0'), File.join(qt, 'include/QtCore/6.12.0/QtCore'),
          File.join(qt, 'include/QtCore/6.12.0/QtCore/private'), File.join(qt, 'mkspecs/netbsd-g++')].map { |p| "-I#{p}" }
commands = []
def run(command, log)
  stdout, stderr, status = Open3.capture3(*command)
  File.write(log, stdout + stderr)
  abort stdout + stderr unless status.success?
  stdout
end
symbols = {}
%w[baseline fixed].each do |variant|
  source = File.join(sources, variant, 'src/corelib/thread/qmutex.cpp')
  command = [cxx, *flags, '-c', source, '-o', File.join(output, "#{variant}.o")]
  commands << {directory: output, arguments: command, file: source}
  run(command, File.join(output, "#{variant}.log"))
  text = run([nm, '-g', '--defined-only', File.join(output, "#{variant}.o")], File.join(output, "#{variant}-symbols.txt"))
  symbols[variant] = text.lines.filter_map { |line| line.split.last if line.match?(/_ZN(?:11QBasicMutex|6QMutex|15QRecursiveMutex)/) }.sort
  File.write(File.join(output, "#{variant}-public-symbols.txt"), symbols[variant].join("\n") + "\n")
end
File.write(File.join(output, 'compile_commands.json'), JSON.pretty_generate(commands) + "\n")
abort 'Public mutex symbols differ or are absent' unless symbols['baseline'] == symbols['fixed'] && symbols['fixed'].length >= 10
clock = File.join(output, 'clock.cpp')
File.write(clock, <<~CPP)
  #include <QtCore/private/qcore_unix_p.h>
  #include <QtCore/qmutex.h>
  static_assert(QT_CONFIG(pthread_condattr_setclock));
  static_assert(QWaitConditionClockId == CLOCK_MONOTONIC);
  static_assert(sizeof(QBasicMutex) == sizeof(void *));
  static_assert(sizeof(QMutex) == sizeof(void *));
CPP
command = [cxx, *flags, '-c', clock, '-o', File.join(output, 'clock.o')]
run(command, File.join(output, 'clock.log'))
File.write(File.join(output, 'clock-command.json'), JSON.pretty_generate(command) + "\n")
puts "PASS: target monotonic clock, public sizes, #{symbols['fixed'].length} public mutex symbols"
