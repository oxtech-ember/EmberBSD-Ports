#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real libXt recipe and generator regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: libxt-cross.rb PREPARED_PKGSRC CROSS_MAKECONF RED_SOURCE GREEN_SOURCE NEW_WORK' unless ARGV.length == 5
tree, conf, red, green = ARGV.first(4).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
abort 'the real ELF refusal control requires macOS' unless RUBY_PLATFORM.include?('darwin')
recipe = File.expand_path('../../../pkgsrc/x11/libXt', __dir__)
stock = File.expand_path('../../../upstream/pkgsrc/x11/libXt', __dir__)
FileUtils.mkdir_p(work)
make = ENV.fetch('BMAKE', 'bmake')
inputs = [__FILE__, conf]

%w[original patched].each do |variant|
  root = "#{work}/#{variant}"
  FileUtils.mkdir_p("#{root}/x11")
  Dir.children(tree).each do |entry|
    next if entry == 'x11'
    FileUtils.ln_s("#{tree}/#{entry}", "#{root}/#{entry}")
  end
  Dir.children("#{tree}/x11").each do |entry|
    next if entry == 'libXt'
    FileUtils.ln_s("#{tree}/x11/#{entry}", "#{root}/x11/#{entry}")
  end
  source = variant == 'original' ? stock : recipe
  FileUtils.cp_r(source, "#{root}/x11/libXt")
  inputs << "#{source}/Makefile"
end

query = lambda do |variant, native|
  args = [make, '-C', "#{work}/#{variant}/x11/libXt", "MAKECONF=#{conf}",
    "WRKOBJDIR=#{work}/objects", *Array(native ? 'USE_CROSS_COMPILE=no' : nil),
    '-V', '${OPSYS}|${CONFIGURE_ENV:MCC_FOR_BUILD=*}|${CONFIGURE_ENV:MCPPFLAGS_FOR_BUILD=*}']
  out, status = Open3.capture2e(*args)
  label = "#{variant}-#{native ? 'native' : 'cross'}"
  File.write("#{work}/#{label}.log", out)
  abort "recipe parsing failed: #{label}" unless status.success?
  fields = out.strip.split('|', -1)
  abort "unexpected parse output: #{label}" unless fields.length == 3
  fields
end
original = query.call('original', false)
patched = query.call('patched', false)
# CONFIGURE_ENV can contain an earlier correct value: the last assignment wins.
original_cc = Shellwords.split(original[1]).last
patched_cc = Shellwords.split(patched[1]).last
abort 'original empty override did not reproduce' unless original[0] == 'NetBSD' && original_cc == 'CC_FOR_BUILD='
abort 'host compiler selection failed' unless patched[0] == 'NetBSD' && patched_cc&.start_with?('CC_FOR_BUILD=/') &&
  File.executable?(Shellwords.split(patched_cc.delete_prefix('CC_FOR_BUILD=')).first)
abort 'target includes still reach the host tool' unless Shellwords.split(patched[2]).last == 'CPPFLAGS_FOR_BUILD='
puts 'RED/GREEN: real cross recipe replaces the empty overriding compiler and excludes target includes'
old_native = query.call('original', true)
new_native = query.call('patched', true)
abort 'native recipe changed' unless old_native == new_native && new_native[0] == 'Darwin'
puts 'GREEN: native Darwin recipe behavior is unchanged'

%w[red green].zip([red, green]).each do |label, source|
  binary = "#{source}/util/makestrs"
  abort "missing #{label} generator" unless File.executable?(binary)
  format, status = Open3.capture2e('file', binary)
  File.write("#{work}/#{label}-format.log", format)
  abort "unexpected #{label} binary format" unless status.success? &&
    format.include?(label == 'red' ? 'ELF 64-bit' : 'Mach-O 64-bit')
  config = File.read("#{source}/util/Makefile")
  cc = config[/^CC_FOR_BUILD = (.*)$/, 1]
  abort 'RED configure did not choose wrapper-PATH gcc' if label == 'red' && cc != 'gcc'
  abort 'GREEN configure did not retain selected host compiler' if label == 'green' && cc != patched_cc.delete_prefix('CC_FOR_BUILD=')
  outdir = "#{work}/#{label}-generated"
  FileUtils.mkdir_p(outdir)
  # Execute the actual binary with the upstream string list and templates.
  # sh's exec makes an ELF format refusal observable without substituting a tool.
  stdout, stderr, result = Open3.capture3('/bin/sh', '-c', 'exec "$@"', 'makestrs',
    binary, '-i', source, stdin_data: File.binread("#{source}/util/string.list"), chdir: outdir)
  File.write("#{outdir}/StringDefs.c", stdout)
  File.write("#{work}/#{label}-execute.log", "exit=#{result.exitstatus}\n#{stderr}")
  if label == 'red'
    abort 'original target generator unexpectedly ran on the host' if result.success?
    abort 'refusal was not an executable-format error' unless stderr.match?(/Exec format|cannot execute|not executable/)
    puts 'RED: actual original NetBSD ELF makestrs is refused on macOS'
  else
    abort 'host generator failed' unless result.success?
    %w[StringDefs.c StringDefs.h Shell.h].each do |name|
      produced = "#{outdir}/#{name}"
      installed = name.end_with?('.c') ? "#{source}/src/#{name}" : "#{source}/include/X11/#{name}"
      abort "generated output differs: #{name}" unless File.size?(produced) &&
        File.binread(produced) == File.binread(installed)
    end
    puts 'GREEN: actual host makestrs reproduces all three package-generated C/header files'
  end
  inputs.concat([binary, "#{source}/util/Makefile", "#{source}/util/makestrs.c",
    "#{source}/util/string.list", "#{source}/config.log"])
end
File.write("#{work}/inputs.sha256", inputs.uniq.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: recipe selection and real build-host generation; no target X11 runtime claim'
