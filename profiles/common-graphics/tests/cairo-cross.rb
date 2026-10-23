#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc Cairo option-selection regression.
require 'digest'
require 'fileutils'
require 'open3'

abort 'usage: cairo-cross.rb PREPARED_PKGSRC CROSS_MAKECONF NEW_WORK' unless ARGV.length == 3
tree, conf = ARGV.first(2).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
abort 'the causal control requires a Darwin host with Quartz.framework' unless File.directory?('/System/Library/Frameworks/Quartz.framework')
source = File.expand_path('../../../pkgsrc/graphics/cairo', __dir__)
options = File.read("#{source}/options.mk")
condition = '.if ${OPSYS} == "Darwin" && exists(/System/Library/Frameworks/Quartz.framework)'
abort 'target-aware Cairo condition is missing' unless options.scan(condition).length == 1
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
    next if entry == 'cairo'
    FileUtils.ln_s("#{tree}/graphics/#{entry}", "#{root}/graphics/#{entry}")
  end
  FileUtils.cp_r(source, "#{root}/graphics/cairo")
  if variant == 'original'
    File.write("#{root}/graphics/cairo/options.mk", options.sub(condition,
      '.if exists(/System/Library/Frameworks/Quartz.framework)'))
  end
end

run = lambda do |variant, mode|
  args = [make, '-C', "#{work}/#{variant}/graphics/cairo", "MAKECONF=#{conf}",
    "WRKOBJDIR=#{work}/objects", *mode, '-V', '${OPSYS}|${PKG_OPTIONS}|${MESON_ARGS}']
  out, status = Open3.capture2e(*args)
  name = "#{variant}-#{mode.empty? ? 'cross' : 'native'}"
  File.write("#{work}/#{name}.log", out)
  abort "recipe parsing failed: #{name}" unless status.success?
  fields = out.strip.split('|', 3)
  abort "unexpected recipe output: #{name}" unless fields.length == 3
  fields
end

original = run.call('original', [])
abort 'original host-Quartz failure did not reproduce' unless original[0] == 'NetBSD' &&
  original[1].split.include?('quartz') && original[2].include?('-Dquartz=enabled')
puts 'RED: original NetBSD cross recipe selects host Quartz and disables X11'

patched = run.call('patched', [])
abort 'cross recipe still selects Quartz or drops its target X11 default' unless patched[0] == 'NetBSD' &&
  !patched[1].split.include?('quartz') && patched[1].split.include?('x11') &&
  patched[2].include?('-Dquartz=disabled') && patched[2].include?('-Dxlib=enabled')
puts 'GREEN: target NetBSD selects its X11 default and explicitly disables Quartz'

original_native = run.call('original', ['USE_CROSS_COMPILE=no'])
patched_native = run.call('patched', ['USE_CROSS_COMPILE=no'])
abort 'native Darwin behavior changed' unless original_native == patched_native &&
  patched_native[0] == 'Darwin' && patched_native[1].split.include?('quartz')
puts 'GREEN: actual native Darwin recipe selection remains unchanged'

paths = [__FILE__, conf, "#{source}/Makefile", "#{source}/options.mk"]
File.write("#{work}/inputs.sha256", paths.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: source-causal package parsing only; compilation and rendering need separate checks'
