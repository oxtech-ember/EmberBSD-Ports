#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Exercise the actual pkgsrc provider policy and upstream shared-XS decision.
require 'tmpdir'
require 'open3'
abort 'Usage: texinfo-iconv.rb EXPORTED_GTEXINFO [PREPARED_TEXINFO_SOURCE]' unless (1..2).cover?(ARGV.length)
root = File.expand_path('../../..', __dir__)
recipe = File.read(ARGV.fetch(0) + '/Makefile')
builtin = File.read(root + '/upstream/pkgsrc/converters/libiconv/builtin.mk')
policy = recipe.lines.grep(/^INCOMPAT_ICONV[\s+?=:]/).join
selection = builtin[/^\.if !defined\(USE_BUILTIN.iconv\).*?^MAKEVARS\+=\s+USE_BUILTIN.iconv/m]
abort 'FAIL: pkgsrc builtin policy section changed' unless selection
Dir.mktmpdir('ember-texinfo-iconv-', '/tmp') do |work|
  fixture = work + '/Makefile'
  File.write(fixture, "PREFER.iconv=native\nIS_BUILTIN.iconv=yes\nBUILTIN_PKG.iconv=libiconv-1.99\nH_GLIBC_ICONV=__nonexistent__\nH_CITRUS_ICONV=__nonexistent__\nBUILTIN_LIB_FOUND.iconv=yes\n" + policy + selection + "\nall:\n\t@echo ${USE_BUILTIN.iconv}\n")
  %w[Darwin-27.0-arm64 Darwin-27.0-x86_64 NetBSD-11.0-aarch64 NetBSD-11.0-x86_64 Linux-6.0-x86_64].each do |platform|
    result, status = Open3.capture2(ENV.fetch('BMAKE', 'bmake'), '-f', fixture, 'MACHINE_PLATFORM=' + platform, 'OPSYS=' + platform.split('-').first)
    expected = platform.start_with?('Darwin-') ? 'no' : 'yes'
    abort "FAIL: actual pkgsrc iconv provider for #{platform}: #{result.strip}" unless status.success? && result.strip == expected
  end
end
puts 'PASS: actual bmake Darwin uses packaged iconv; NetBSD targets and foreign platforms keep their provider policy'
if ARGV.length == 2
  source = ARGV.fetch(1)
  configure = File.read(source + '/tta/configure.ac')
  decision = configure[/^use_shared_txi_libraries=no.*?(?=^AM_CONDITIONAL\(\[USE_SHARED_TXI_LIBRARIES\])/m]
  abort 'FAIL: upstream shared-library decision changed' unless decision
  %w[no yes].each do |working|
    script = "am_func_iconv=#{working}\nenable_xs=yes\nenable_additional_tests=no\nwith_swig=no\n" + decision + 'printf "%s\n" "$use_shared_txi_libraries"' + "\n"
    result, status = Open3.capture2('sh', '-eu', stdin_data: script)
    abort 'FAIL: working-iconv gate was bypassed' unless status.success? && result.strip == working
  end
  puts 'PASS: actual upstream configure rejects broken iconv and enables shared XS/C libraries only for working iconv'
end
