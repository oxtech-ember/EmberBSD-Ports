#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Keep Cargo's original dependency closure intact.
require 'digest'

abort 'Usage: librsvg-inputs.rb ORIGINAL_SOURCE PATCHED_SOURCE DISTDIR' unless ARGV.size == 3
original, patched, distdir = ARGV.map { |p| File.realpath(p) }
recipe = File.expand_path('../../../pkgsrc/graphics/librsvg', __dir__)
lock = File.binread(original + '/Cargo.lock')
abort 'Cargo.lock changed during packaging' unless lock == File.binread(patched + '/Cargo.lock')
expected = lock.split(/^\[\[package\]\]\n/).drop(1).map do |block|
  fields = block.scan(/^(name|version|source|checksum) = "([^"]+)"$/).to_h
  next unless fields['source']
  abort 'unexpected non-registry source' unless fields['source'] == 'registry+https://github.com/rust-lang/crates.io-index'
  name = fields.fetch('name') + '-' + fields.fetch('version')
  path = distdir + '/' + name + '.crate'
  abort "archive differs from upstream lock: #{name}" unless Digest::SHA256.file(path).hexdigest == fields.fetch('checksum')
  abort "vendor source missing: #{name}" unless File.file?(File.dirname(patched) + '/vendor/' + name + '/Cargo.toml')
  name
end.compact.sort
declared = File.read(recipe + '/cargo-depends.mk').scan(/^CARGO_CRATE_DEPENDS\+=\s+(\S+)$/).flatten.sort
abort 'Cargo recipe differs from upstream closure' unless declared == expected && expected.size == 357
patches = File.read(recipe + '/distinfo').scan(/^SHA1 \((patch-[^)]+)\) = ([a-f0-9]+)$/).to_h
abort 'patch inventory differs' unless Dir[recipe + '/patches/patch-*'].map { |p| File.basename(p) }.sort == patches.keys.sort
patches.each do |name, sha|
  content = File.binread(recipe + '/patches/' + name).lines.reject { |l| l.include?('$NetBSD') }.join
  abort "patch checksum differs: #{name}" unless Digest::SHA1.hexdigest(content) == sha
end
puts "PASS: unchanged upstream Cargo.lock; all #{expected.size} archive hashes and vendor sources; #{patches.size} checksummed patches"
