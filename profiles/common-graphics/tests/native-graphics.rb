#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real pkgsrc native generator metadata guards.
require 'digest'
require 'fileutils'
require 'open3'
abort 'usage: native-graphics.rb PREPARED_PKGSRC CROSS_MAKECONF NEW_WORK' unless ARGV.length == 3
tree, conf = ARGV.first(2).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
make = ENV.fetch('BMAKE', 'bmake')
run = lambda do |name, package, extra, target, success|
  command = [make, '-C', "#{tree}/#{package}", "MAKECONF=#{conf}", "WRKOBJDIR=#{work}/work", *extra, *target]
  out, status = Open3.capture2e(*command)
  File.write("#{work}/#{name}.log", out)
  abort "unexpected command status: #{name}" unless status.success? == success
  out
end
%w[x11/libdisplay-info sysutils/seatd wayland/wlroots].each do |package|
  name = package.split('/').last
  extra = name == 'wlroots' ? ['EMBERBSD_WLROOTS_PROFILE=drm-gles2'] : []
  run.call("#{name}-guard", package, extra, ['emberbsd-native-graphics-check'], true)
  native = run.call("#{name}-native", package, [*extra, 'USE_CROSS_COMPILE=no'], ['show-vars', 'VARNAMES=MESON_NATIVE_ARGS'], true)
  abort 'native build acquired a cross generator file' if native.include?('.meson-graphics-native')
  puts "PASS: #{name} checks real host metadata; native path remains unchanged"
end
{
  'wrong-version' => ['EMBERBSD_NATIVE_GRAPHICS_PC=hwdata:0.412'],
  'missing-module' => ['EMBERBSD_NATIVE_GRAPHICS_PC=absent-graphics-metadata:0.413']
}.each do |name, extra|
  out = run.call(name, 'x11/libdisplay-info', extra, ['emberbsd-native-graphics-check'], false)
  abort 'wrong metadata was not rejected by the guard' unless out.include?('Native graphics metadata does not match')
  puts "PASS: rejects #{name} through actual pkg-config"
end
host = run.call('host-prefix', 'x11/libdisplay-info', [], ['show-vars', 'VARNAMES=TOOLBASE'], true).strip
clone = "#{work}/relocated-host"
FileUtils.mkdir_p(["#{clone}/bin", "#{clone}/lib/pkgconfig"])
FileUtils.ln_s("#{host}/bin/pkg-config", "#{clone}/bin/pkg-config")
# Preserve the real installed .pc bytes: its embedded prefix must now disagree.
FileUtils.cp("#{host}/lib/pkgconfig/hwdata.pc", "#{clone}/lib/pkgconfig/hwdata.pc")
out = run.call('wrong-prefix', 'x11/libdisplay-info', ["TOOLBASE=#{clone}"], ['emberbsd-native-graphics-check'], false)
abort 'relocated metadata prefix was accepted' unless out.include?('Native graphics metadata does not match')
puts 'PASS: rejects actual metadata with the wrong host prefix'
unsafe = "#{work}/unsafe+prefix"
FileUtils.ln_s(host, unsafe)
out = run.call('unsafe-prefix', 'x11/libdisplay-info', ["TOOLBASE=#{unsafe}"], ['show-vars', 'VARNAMES=PKG_FAIL_REASON'], true)
abort 'unsafe host prefix accepted' unless out.include?('Native graphics tool prefix must be absolute')
puts 'PASS: rejects unsafe host prefix during actual recipe parsing'
paths = [__FILE__, conf, "#{tree}/sysutils/hwdata/native-meson.mk", "#{host}/bin/pkg-config", "#{host}/lib/pkgconfig/hwdata.pc", "#{host}/share/pkgconfig/scdoc.pc"]
File.write("#{work}/inputs.sha256", paths.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts 'PASS: metadata guard checks only; real package configuration and target behavior are separate receipts'
