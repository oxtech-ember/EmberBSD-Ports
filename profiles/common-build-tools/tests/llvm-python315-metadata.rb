#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), actual pkgsrc recipe selection checks.
require 'fileutils'
require 'open3'
abort 'Usage: llvm-python315-metadata.rb EXPORTED_PKGSRC NEW_OUTPUT' unless ARGV.size == 2
tree, out = ARGV.map { |path| File.expand_path(path) }
Dir.mkdir(out)
make = ENV.fetch('BMAKE', 'bmake')
base = %w[PKG_OPTIONS.clang=-tests PKG_OPTIONS.lld=-tests]
%w[PKG_INFO PKG_ADMIN PKG_DBDIR].each { |key| base << "#{key}=#{ENV.fetch(key)}" if ENV.key?(key) }
%w[lang/clang devel/lld devel/py-llvm-lit].each do |pkg|
  values = %w[PKGNAME PYTHONBIN DEPENDS CONFLICTS PKG_FAIL_REASON]
  query = values.flat_map { |name| ['-V', "${#{name}}"] }
  output, status = Open3.capture2e(make, '-C', File.join(tree, pkg), *query, *base, 'PYTHON_VERSION_REQD=315')
  File.write(File.join(out, "#{pkg.tr('/', '-')}.txt"), output)
  abort output unless status.success?
  lines = output.lines.map(&:chomp)
  abort "Unexpected pkgsrc diagnostics: #{pkg}: #{output}" unless lines.size == values.size && lines.last.empty?
  abort 'Wrong Python target' unless lines[1] == '/usr/pkg/bin/python3.15'
  abort 'Old runtime ABI selected' if lines[2].match?(/(?:python314|py314-)/)
  if pkg == 'devel/py-llvm-lit'
    abort 'Wrong lit selection' unless lines[0] == 'py315-llvm-lit-23.1.3nb1'
    abort 'Missing unique-provider conflict' unless lines[3].split.include?('py[0-9]*-llvm-lit-[0-9]*')
  else
    abort 'Missing current lit dependency' unless lines[2].include?('py315-llvm-lit>=23.1.3nb1:')
    abort 'Missing explicit Python runtime' if pkg == 'lang/clang' && !lines[2].match?(/python315>=3\.15[^:]*:/)
  end
  rejected, _ = Open3.capture2e(make, '-C', File.join(tree, pkg), '-V', '${PKG_FAIL_REASON}', *base, 'PYTHON_VERSION_REQD=314')
  File.write(File.join(out, "#{pkg.tr('/', '-')}-old.txt"), rejected)
  abort "Old Python override was accepted: #{pkg}" unless rejected.match?(/No valid Python version|[Ii]ncompatible|[Nn]ot.*support|[Nn]ot.*accept|requires Python|PYTHON_VERSION_REQD/)
end
puts 'PASS: current recipe selectors, explicit Clang runtime, lit provider conflict and old ABI rejection.'
