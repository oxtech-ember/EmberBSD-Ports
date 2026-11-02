#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real cross-profile libc guard.
require 'fileutils'
require 'open3'
abort 'Usage: cross-libc.rb BMAKE NEW_WORK' unless ARGV.size == 2
bmake = File.realpath(ARGV[0])
work = File.expand_path(ARGV[1])
abort 'new absolute work required' unless ARGV[1].start_with?('/') && !File.exist?(work)
source_mk = File.expand_path('../cross/mk.conf', __dir__)
profile = work + '/profile'
cross = profile + '/cross'
FileUtils.mkdir_p(cross)
FileUtils.cp(source_mk, cross + '/mk.conf')
%w[EMBERBSD-NATIVE-TOOLS.MK EMBERBSD-DEFAULTS-MK.CONF EMBERBSD-COMMON-TOOLS-MK.CONF].each do |name|
  File.write(cross + '/' + name, "# fixture include\n")
end
File.write(profile + '/mk.conf', "# fixture common profile\n")
root = cross + '/mk.conf'
sysroot = work + '/sysroot'
FileUtils.mkdir_p(sysroot + '/usr/lib')
FileUtils.mkdir_p(sysroot + '/lib')
mapping = work + '/native-tools.mk'
File.write(mapping, "# fixture mapping\n")
verified = [work, work, 'clang', 'fetch', mapping, '', ''].join('|')
File.write(work + '/Makefile', <<~MAKE)
  BSD_PKG_MK=yes
  PKGPATH=devel/ember-libc-fixture
  EMBERBSD_SDK_SOURCE=#{work}
  EMBERBSD_HOST_PREFIX=#{work}
  EMBERBSD_NATIVE_TOOLSET_MAKECONF=#{mapping}
  EMBERBSD_NATIVE_TOOLSET_VERIFIED=#{verified}
  EMBERBSD_CROSS_TOOLS=#{work}
  EMBERBSD_CROSS_HOST_PREFIX=#{work}
  EMBERBSD_CROSS_SYSROOT=#{sysroot}
  EMBERBSD_CROSS_COMPILER_FAMILY=gcc
  RUN=@
  .include "#{root}"
MAKE
canonical = sysroot + '/lib/libc.so.12.224'
File.write(canonical, "accepted fork libc fixture\n")
aliases = %w[/lib/libc.so /lib/libc.so.12 /usr/lib/libc.so /usr/lib/libc.so.12]
aliases.each { |p| File.symlink(canonical, sysroot + p) }
check = lambda do |name, pass, mode = 'shared', failure = 'Missing or divergent EmberBSD libc alias:'|
  output, status = Open3.capture2e(bmake, '-f', work + '/Makefile',
                                  "EMBERBSD_CROSS_LIBC_MODE=#{mode}", 'pre-extract')
  File.write(work + '/' + name + '.log', output)
  abort "#{name}: unexpected guard result: #{output}" unless status.success? == pass
  abort "#{name}: failed for another reason" if !pass && !output.include?(failure)
end
check.call('consistent-aliases', true)
aliases.each_with_index do |p, index|
  File.unlink(sysroot + p)
  check.call("missing-#{index}", false)
  File.write(sysroot + p, "unrelated upstream libc fixture\n")
  check.call("divergent-#{index}", false)
  File.unlink(sysroot + p)
  File.symlink(canonical, sysroot + p)
end
check.call('restored-aliases', true)
aliases.each { |p| File.unlink(sysroot + p) }
File.write(sysroot + '/usr/lib/libc.a', "static libc fixture\n")
check.call('static-libc', true, 'static')
flags, flag_status = Open3.capture2e(bmake, '-f', work + '/Makefile',
                                     'EMBERBSD_CROSS_LIBC_MODE=static', '-V', 'LDFLAGS')
abort "static link mode failed: #{flags}" unless flag_status.success? && flags.split.include?('-static')
pie, pie_status = Open3.capture2e(bmake, '-f', work + '/Makefile',
                                  'EMBERBSD_CROSS_LIBC_MODE=static', '-V', 'PKGSRC_MKPIE')
abort "static mode still enables PIE: #{pie}" unless pie_status.success? && pie.strip == 'no'
flags, flag_status = Open3.capture2e(bmake, '-f', work + '/Makefile',
                                     'EMBERBSD_CROSS_LIBC_MODE=shared', '-V', 'LDFLAGS')
abort "shared mode unexpectedly forces static link: #{flags}" unless flag_status.success? && !flags.split.include?('-static')
pie, pie_status = Open3.capture2e(bmake, '-f', work + '/Makefile',
                                  'EMBERBSD_CROSS_LIBC_MODE=shared', '-V', 'PKGSRC_MKPIE')
abort "shared mode unexpectedly disables PIE: #{pie}" unless pie_status.success? && pie.strip.empty?
File.symlink(canonical, sysroot + '/lib/libc.so')
check.call('static-with-shared-alias', false, 'static',
           'Unexpected shared libc alias in static-only sysroot:')
puts 'PASS: cross profile checks static libc mode and canonical shared aliases'
