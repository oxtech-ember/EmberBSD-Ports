#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), verify libX11's real build-host generator.
require 'digest'
require 'open3'
require 'shellwords'

abort 'usage: x11-makekeys.rb PREPARED_PKGSRC CROSS_MAKECONF LIBX11_SOURCE NEW_WORK' unless ARGV.length == 4
tree, conf, source = ARGV.first(3).map { |path| File.realpath(path) }
work = File.expand_path(ARGV.last)
abort 'NEW_WORK must be new and absolute' unless ARGV.last.start_with?('/') && !File.exist?(work)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
base = [make, '-C', "#{tree}/x11/libX11", "MAKECONF=#{conf}", "WRKOBJDIR=#{work}/objects"]
names = %w[PKG_FAIL_REASON NATIVE_CC EMBERBSD_CROSS_BUILD_CC CONFIGURE_ENV CROSS_DESTDIR]
out, status = Open3.capture2e(*base, 'show-vars', "VARNAMES=#{names.join(' ')}")
File.write("#{work}/selection.log", out)
abort 'actual libX11 recipe parse failed' unless status.success? && out.lines.length == names.length
vars = names.zip(out.lines.map(&:chomp)).to_h
abort vars['PKG_FAIL_REASON'] unless vars['PKG_FAIL_REASON'].empty?
# libX11 appends its assignment after the common cross profile. The last
# value must remain the host compiler, rather than clearing CC_FOR_BUILD.
selected = Shellwords.split(vars['CONFIGURE_ENV']).grep(/\ACC_FOR_BUILD=/).last&.delete_prefix('CC_FOR_BUILD=')
abort 'libX11 overrides the selected absolute host compiler' unless selected == vars['NATIVE_CC'] && Shellwords.split(selected).first == vars['EMBERBSD_CROSS_BUILD_CC']
puts 'PASS: actual libX11 recipe preserves the absolute build-host compiler'
out, status = Open3.capture2e(*base, 'NATIVE_CC=/usr/bin/false', 'show-var', 'VARNAME=PKG_FAIL_REASON')
File.write("#{work}/override.log", out)
abort 'recipe accepted a different NATIVE_CC' unless status.success? && out.include?('Cross generators require the selected native build compilers')
puts 'PASS: cross libX11 refuses a conflicting NATIVE_CC override'
out, status = Open3.capture2e(*base, 'USE_CROSS_COMPILE=no', 'show-vars', 'VARNAMES=PKG_FAIL_REASON NATIVE_CC')
File.write("#{work}/native.log", out)
abort 'native tool dependency acquired the cross-only NATIVE_CC override' unless status.success? && out.lines.map(&:chomp) == ['', '']
puts 'PASS: native Darwin tool dependencies preserve their original configuration'
program = "#{source}/src/util/makekeys.c"
headers = %w[keysymdef.h XF86keysym.h Sunkeysym.h DECkeysym.h HPkeysym.h].map { |name| "#{vars['CROSS_DESTDIR']}/usr/pkg/include/X11/#{name}" }
inputs = [program, Shellwords.split(selected).first, *headers]
inputs.each { |path| abort "missing input #{path}" unless File.file?(path) }
File.write("#{work}/inputs.sha256", inputs.map { |path| "#{Digest::SHA256.file(path).hexdigest}  #{path}\n" }.join)
out, status = Open3.capture2e(*Shellwords.split(selected), '-O2', program, '-o', "#{work}/makekeys")
File.write("#{work}/compile.log", out)
abort 'upstream makekeys host compilation failed' unless status.success?
out, err, status = Open3.capture3("#{work}/makekeys", *headers)
File.write("#{work}/ks_tables.h", out)
File.write("#{work}/generate.log", err)
abort 'upstream makekeys did not generate both target keysym tables' unless status.success? && err.empty? && out.include?('hashString[KTABLESIZE]') && out.include?('hashKeysym[VTABLESIZE]')
File.write("#{work}/outputs.sha256", %w[makekeys ks_tables.h].map { |name| "#{Digest::SHA256.file("#{work}/#{name}").hexdigest}  #{name}\n" }.join)
puts 'PASS: upstream makekeys compiles/runs on the host and generates both tables from the target xorgproto headers'
