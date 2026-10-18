#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Check actual GCC16 header dependencies.
require 'digest'
require 'fileutils'
require 'json'
require 'shellwords'
require_relative '../cross/llvm-native'

abort 'Usage: HOST_CXX=/absolute/g++ llvm-native-headers.rb TARGET_SYSROOT NEW_WORK' unless ARGV.length == 2
sysroot = File.realpath(ARGV.fetch(0))
work = ARGV.fetch(1)
abort 'Use a new absolute work directory' unless work.start_with?('/') && !File.exist?(work) && !File.symlink?(work)
native = EmberGraphicsLLVMNative
cxx = ENV.fetch('HOST_CXX')
triple = native.capture(cxx, '-dumpmachine').strip
compiler = native.compiler(cxx, triple, [])
roots = [work, *compiler.fetch(:header_roots)]
foreign = "#{sysroot}/usr/include/stdbool.h"
abort 'Actual target stdbool.h is required' unless File.file?(foreign)
FileUtils.mkdir_p("#{work}/include")
File.write("#{work}/native.cpp", "#include <linux/types.h>\n")
before = native.capture(cxx, '-M', '-MT', 'native', "#{work}/native.cpp")
after = native.capture(cxx, '-fno-canonical-system-headers', '-M', '-MT', 'native', "#{work}/native.cpp")
File.write("#{work}/before.d", before)
File.write("#{work}/after.d", after)
dependencies = Shellwords.split(after.gsub("\\\n", ' ').sub(/\Anative:\s*/, ''))
dependencies.each { |path| native.validate_header(path, roots, forbidden: [sysroot]) }
puts 'PASS: real GCC16 UAPI dependencies belong to measured native include roots'
tokens = [[], ['-fno-canonical-system-headers']].map do |flags|
  native.capture(cxx, *flags, '-E', '-P', "#{work}/native.cpp")
end
abort 'Dependency-name option changed actual preprocessed tokens' unless tokens[0] == tokens[1]
puts 'PASS: dependency-name option preserves actual preprocessed tokens'

link = "#{work}/include/target-bool.h"
File.symlink(foreign, link)
File.write("#{work}/foreign.cpp", "#include <target-bool.h>\n")
foreign_dependencies = native.capture(cxx, '-fno-canonical-system-headers', '-M', '-MT', 'foreign',
  '-isystem', "#{work}/include", "#{work}/foreign.cpp")
File.write("#{work}/foreign.d", foreign_dependencies)
paths = Shellwords.split(foreign_dependencies.gsub("\\\n", ' ').sub(/\Aforeign:\s*/, ''))
abort 'GCC did not retain the actual work header link' unless paths.include?(link)
begin
  native.validate_header(link, roots, forbidden: [sysroot])
  abort 'Accepted a work header link into the real target sysroot'
rescue ArgumentError => error
  raise unless error.message.include?('resolves inside a target tree')
end
puts 'PASS: work header link into the actual target sysroot is refused before local classification'
File.write("#{work}/receipt.json", JSON.pretty_generate(scope: 'actual native GCC16 header scan and target-header refusal only',
  compiler: cxx, target_header: foreign, target_header_sha256: Digest::SHA256.file(foreign).hexdigest,
  dependencies: dependencies, refused_work_link: link, checks: 3) + "\n")
