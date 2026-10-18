#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Compare real target queries with the host tool.
require 'json'
require 'open3'
require 'shellwords'
require_relative 'llvm-target'

abort 'usage: compare-llvm-config.rb COMPLETED_WORK TARGET_REFERENCE' unless ARGV.length == 2
work, reference = ARGV.map { |p| File.realpath(p) }
r = JSON.parse(File.read("#{work}/receipt.json"))
abort 'reference capture is incomplete' unless File.read("#{reference}/status").strip == 'complete'
abort 'comparison requires an installed/staged prefix, not a development tree' if r.fetch('target_prefix') == r.fetch('target_build')
target_prefix = File.read("#{reference}/prefix").strip
abort 'invalid reference prefix' unless target_prefix.start_with?('/') && !target_prefix.match?(/\s/)
EmberGraphicsLLVM.for_triple(r.fetch('target_triple'))
abort 'reference must match the selected LLVM 23.1.3 NetBSD target exactly' unless File.read("#{reference}/version").strip == '23.1.3' && File.read("#{reference}/host-target").strip == r.fetch('target_triple')
components = %w[bitwriter engine mcdisassembler mcjit core executionengine scalaropts transformutils instcombine native orcjit]
options = %w[version host-target has-rtti assertion-mode targets-built components prefix cppflags cflags cxxflags ldflags shared-mode libs libnames libfiles system-libs]
failed = []
options.each do |option|
  args = if %w[shared-mode libs libnames libfiles system-libs].include?(option)
           ['--link-shared', "--#{option}", *components]
         else
           ["--#{option}"]
         end
  actual, error, status = Open3.capture3("#{work}/bin/llvm-config", *args)
  abort "host query failed (#{option}): #{error}" unless status.success?
  expected = File.read("#{reference}/#{option}").strip
  case option
  when 'prefix'
    expected = r.fetch('target_prefix')
  when 'cppflags', 'cflags', 'cxxflags'
    expected = Shellwords.split(expected).map { |v| v == "-I#{target_prefix}/include" ? "-I#{r.fetch('target_prefix')}/include" : v }
  when 'ldflags'
    abort 'target reference leaks the private build sysroot' if expected.include?(r.fetch('sysroot'))
    expected = Shellwords.split(expected).each_with_index.map do |v, index|
      if index == 0 && v == "-L#{target_prefix}/lib"
        "-L#{r.fetch('target_prefix')}/lib"
      elsif v.start_with?('-L/') && !v.start_with?("-L#{r.fetch('sysroot')}/")
        "-L#{r.fetch('sysroot')}#{v[2..-1]}"
      else
        v
      end
    end
  when 'libfiles'
    expected = Shellwords.split(expected).map do |v|
      abort "reference library outside its prefix: #{v}" unless v.start_with?(target_prefix + '/lib/')
      r.fetch('target_prefix') + v.delete_prefix(target_prefix)
    end
  end
  expected = Shellwords.split(expected) if expected.is_a?(String)
  actual = Shellwords.split(actual)
  if actual == expected
    puts "PASS: #{option} agrees with real target llvm-config"
  else
    warn "FAIL: #{option}\n  expected: #{expected.inspect}\n  actual:   #{actual.inspect}"
    failed << option
  end
end
abort "metadata disagreement: #{failed.join(', ')}" unless failed.empty?
