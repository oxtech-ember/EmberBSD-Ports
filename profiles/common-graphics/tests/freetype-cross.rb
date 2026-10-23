#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc FreeType link-selection regression.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: freetype-cross.rb PREPARED_PKGSRC CROSS_MAKECONF NEW_WORK' unless ARGV.length == 3
tree, conf = ARGV.first(2).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
abort 'the causal control requires a Darwin host with Carbon.framework' unless File.directory?('/System/Library/Frameworks/Carbon.framework')
source = File.expand_path('../../../pkgsrc/graphics/freetype2', __dir__)
options = File.read("#{source}/Makefile")
condition = '.if ${OPSYS} == "Darwin" && exists(/System/Library/Frameworks/Carbon.framework)'
abort 'target-aware FreeType condition is missing' unless options.scan(condition).length == 1
FileUtils.mkdir_p(work)
make = ENV.fetch('BMAKE', 'bmake')

%w[original patched].each do |variant|
  root = "#{work}/#{variant}"
  FileUtils.mkdir_p("#{root}/graphics")
  Dir.children(tree).each do |entry|
    next if entry == 'graphics'
    FileUtils.ln_s("#{tree}/#{entry}", "#{root}/#{entry}")
  end
  Dir.children("#{tree}/graphics").each do |entry|
    next if entry == 'freetype2'
    FileUtils.ln_s("#{tree}/graphics/#{entry}", "#{root}/graphics/#{entry}")
  end
  FileUtils.cp_r(source, "#{root}/graphics/freetype2")
  if variant == 'original'
    File.write("#{root}/graphics/freetype2/Makefile", options.sub(condition,
      '.if exists(/System/Library/Frameworks/Carbon.framework)'))
  end
end

run = lambda do |variant, mode|
  args = [make, '-C', "#{work}/#{variant}/graphics/freetype2", "MAKECONF=#{conf}",
    "WRKOBJDIR=#{work}/objects", *mode, '-V', '${OPSYS}|${LDFLAGS}|${CONFIGURE_ENV:MCC_BUILD=*}']
  out, status = Open3.capture2e(*args)
  name = "#{variant}-#{mode.empty? ? 'cross' : 'native'}"
  File.write("#{work}/#{name}.log", out)
  abort "recipe parsing failed: #{name}" unless status.success?
  fields = out.strip.split('|', -1)
  abort "unexpected recipe output: #{name}" unless fields.length == 3
  fields
end

original = run.call('original', [])
abort 'original host-Carbon failure did not reproduce' unless original[0] == 'NetBSD' &&
  original[1].include?('-framework Carbon')
puts 'RED: original NetBSD cross recipe links the host Carbon framework'
patched = run.call('patched', [])
abort 'cross recipe still selects Carbon' unless patched[0] == 'NetBSD' &&
  !patched[1].include?('-framework Carbon')
puts 'GREEN: target NetBSD omits the Darwin framework'
abort 'explicit host compiler was not selected' unless patched[2].start_with?('CC_BUILD=/') &&
  File.executable?(Shellwords.split(Shellwords.split(patched[2]).last.delete_prefix('CC_BUILD=')).first)
puts 'GREEN: the common cross native compiler command reaches the actual FreeType CC_BUILD input'
original_native = run.call('original', ['USE_CROSS_COMPILE=no'])
patched_native = run.call('patched', ['USE_CROSS_COMPILE=no'])
abort 'native Darwin behavior changed' unless original_native == patched_native &&
  patched_native[0] == 'Darwin' && patched_native[1].include?('-framework Carbon')
puts 'GREEN: actual native Darwin recipe selection remains unchanged'
paths = [__FILE__, conf, "#{source}/Makefile"]
File.write("#{work}/inputs.sha256", paths.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: source-causal package parsing only; compilation and font rendering need separate checks'
