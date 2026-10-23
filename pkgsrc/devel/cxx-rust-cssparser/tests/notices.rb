#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted original notice installation regression.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'tmpdir'
abort 'Usage: notices.rb ORIGINAL_SOURCE VERIFIED_VENDOR NATIVE_DIGEST PKGSRC_LICENSES' unless ARGV.length == 4
source, vendor, digest, licenses = ARGV.map { |p| File.expand_path(p) }
recipe = File.expand_path('..', __dir__)
manifest = recipe + '/files/notices.sha256'
helper = recipe + '/files/install-notices.sh'
abort 'FAIL: package does not install checked original notices' unless File.file?(manifest) && File.file?(helper)
entries = File.readlines(manifest, chomp: true).map { |l| l.split("\t", -1) }
expected = Dir.glob(vendor + '/**/*', File::FNM_DOTMATCH).select { |p| File.file?(p) && File.basename(p).match?(/\A(?:LICENSE|COPYING|NOTICE)(?:[._-].*)?\z/i) }.map { |p| ['vendor/' + p.delete_prefix(vendor + '/'), p] }.to_h
abort 'FAIL: actual original vendor notice coverage changed' unless expected.length == 103
Dir.glob(source + '/LICENSES/*').each { |p| expected['project/' + p.delete_prefix(source + '/')] = p }
%w[REUSE.toml rust/Cargo.lock].each { |p| expected['project/' + p] = source + '/' + p }
abort 'FAIL: notice manifest omits or invents source files' unless entries.map(&:last).sort == expected.keys.sort
entries.each { |sha, path| abort "FAIL: original notice hash #{path}" unless Digest::SHA256.file(expected.fetch(path)).hexdigest == sha }
metadata = JSON.parse(File.read(recipe + '/files/licenses.json'))
abort 'FAIL: actual target metadata graph differs' unless metadata.fetch('registry_packages').length == 52 && metadata.fetch('target') == 'x86_64-unknown-netbsd'
metadata.fetch('registry_packages').each do |p|
  toml = File.join(vendor, p.fetch('name') + '-' + p.fetch('version'), 'Cargo.toml')
  text = File.read(toml)
  abort 'FAIL: SPDX source evidence changed' unless text[/^license = "([^"]+)"$/, 1] == p.fetch('upstream_spdx') && Digest::SHA256.file(toml).hexdigest == p.fetch('manifest_sha256')
end
attributions = Dir.glob(source + '/**/*', File::FNM_DOTMATCH).select { |p| File.file?(p) }.flat_map { |p| File.read(p).scan(/SPDX-FileCopyrightText:\s*([^\n]+)/).flatten }.reject { |text| text == 'None' }.uniq.sort
abort 'FAIL: original project attribution changed or omitted' unless metadata.fetch('project').fetch('attribution_notices') == attributions
makefile = File.read(recipe + '/Makefile')
metadata.fetch('pkgsrc_license_ids').each { |id| abort 'FAIL: invented pkgsrc license identifier' unless File.file?(File.join(licenses, id)) }
logical_makefile = makefile.gsub(/\\\n\s*/, ' ').gsub(/\s+/, ' ')
abort 'FAIL: component licenses became an all-OR expression' unless logical_makefile.include?(metadata.fetch('pkgsrc_expression'))
plist = File.readlines(recipe + '/PLIST', chomp: true).grep(%r{\Ashare/licenses/cxx-rust-cssparser/}).map { |p| p.delete_prefix('share/licenses/cxx-rust-cssparser/') }.sort
abort 'FAIL: PLIST misses installed notices/provenance' unless plist == (expected.keys + %w[NOTICES.sha256 licenses.json vendor-r1.json]).sort
Dir.mktmpdir('ember-css-notices-', File.realpath('/tmp')) do |work|
  fixture = work + '/source'
  expected.each do |relative, original|
    target = relative.start_with?('vendor/') ? fixture + '/rust/' + relative : fixture + '/' + relative.delete_prefix('project/')
    FileUtils.mkdir_p(File.dirname(target))
    FileUtils.cp(original, target)
  end
  run = lambda do |destination, notice_manifest = manifest|
    Open3.capture2e('sh', helper, fixture, destination, notice_manifest, digest, '/usr/bin/install', '-m', '644')
  end
  output = work + '/installed'
  log, status = run.call(output)
  abort 'FAIL: original notice installation: ' + log unless status.success?
  expected.each { |relative, original| abort 'FAIL: installed notice bytes changed' unless File.binread(output + '/' + relative) == File.binread(original) }
  abort 'FAIL: installed notice count differs' unless Dir.glob(output + '/**/*').count { |p| File.file?(p) } == expected.length
  reject = lambda do |name, candidate_manifest = manifest|
    dest = work + '/rejected-' + name
    log, status = run.call(dest, candidate_manifest)
    abort "FAIL: accepted #{name}: #{log}" if status.success? || File.exist?(dest)
  end
  victim = fixture + '/rust/vendor/' + expected.keys.grep(/^vendor\//).first.delete_prefix('vendor/')
  original = File.binread(victim)
  File.write(victim, original + "changed\n"); reject.call('changed-notice')
  File.unlink(victim); reject.call('missing-notice')
  File.symlink(expected.values.first, victim); reject.call('symlink-notice')
  File.unlink(victim); File.binwrite(victim, original)
  File.rename(fixture + '/rust/vendor', work + '/outside-vendor')
  File.symlink(work + '/outside-vendor', fixture + '/rust/vendor')
  reject.call('symlink-source-directory')
  File.unlink(fixture + '/rust/vendor')
  File.rename(work + '/outside-vendor', fixture + '/rust/vendor')
  File.symlink(work, work + '/destination-alias')
  log, status = run.call(work + '/destination-alias/escaped-output')
  abort 'FAIL: wrote through symlink destination ancestor' if status.success? || File.exist?(work + '/escaped-output')
  bad_manifest = work + '/bad.sha256'
  File.write(bad_manifest, File.read(manifest) + entries.first.first + "\tproject/../../escape\n")
  reject.call('escaping-path', bad_manifest)
  File.write(bad_manifest, File.read(manifest) + File.readlines(manifest).first)
  reject.call('duplicate-path', bad_manifest)
  File.write(bad_manifest, "bad\tproject/LICENSES/BSD-2-Clause.txt\n")
  reject.call('bad-digest', bad_manifest)
  File.write(bad_manifest, File.read(manifest).chomp)
  final_sha, final_path = entries.last
  final_file = final_path.start_with?('vendor/') ? fixture + '/rust/' + final_path : fixture + '/' + final_path.delete_prefix('project/')
  final_bytes = File.binread(final_file)
  File.binwrite(final_file, final_bytes + 'changed')
  reject.call('changed-final-line-without-newline', bad_manifest)
  File.binwrite(final_file, final_bytes)
  log, status = run.call(output)
  abort 'FAIL: overwrote existing notice destination' if status.success?
end
puts 'PASS: actual 103 original registry notices, project licenses and exact source hashes match normal PLIST'
puts 'PASS: original SPDX/target graph and existing pkgsrc IDs; component AND and per-component alternatives retained'
puts 'PASS: complete original notices installed; missing/changed/symlink/path/digest/duplicate inputs fail before output'
