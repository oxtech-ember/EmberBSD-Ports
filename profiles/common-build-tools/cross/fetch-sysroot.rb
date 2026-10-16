#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
require 'json'
require_relative 'sysroot-archive'

begin
  revision, expected_manifest, work = ARGV
  raise 'Usage: fetch-sysroot.rb FULL_SOURCE_COMMIT MANIFEST_SHA256 /absolute/unused-work' unless ARGV.length == 3 &&
    revision.match?(/\A[0-9a-f]{40}\z/) && expected_manifest.match?(/\A[0-9a-f]{64}\z/) && work.start_with?('/') && !work.match?(/\s/)
  work = File.expand_path(work)
  raise 'Use a fresh work directory' if File.exist?(work) || File.symlink?(work)
  Dir.mkdir(work, 0700)
  downloads = work + '/downloads'
  Dir.mkdir(downloads)
  tag = 'build-' + revision + '-aarch64-sysroot'
  base = 'https://github.com/oxtech-ember/EmberBSD/releases/download/' + tag + '/'
  fetch = lambda do |name|
    raise 'Unsafe asset name' unless name.match?(/\A[A-Za-z0-9][A-Za-z0-9._-]*\z/)
    path = downloads + '/' + name
    args = ['curl', '--fail', '--location', '--silent', '--show-error', '--proto', '=https', '--proto-redir', '=https', '--tlsv1.2', '--output', path, base + name]
    raise 'HTTPS download failed: ' + name unless system(*args)
    path
  end
  manifest_path = fetch.call('manifest.json')
  raise 'Pinned manifest SHA256 differs' unless Digest::SHA256.file(manifest_path).hexdigest == expected_manifest
  manifest = JSON.parse(File.read(manifest_path))
  raise 'Wrong source, schema or architecture' unless manifest.values_at('schema', 'repository', 'source_commit', 'release_tag', 'architecture', 'machine') ==
    ['emberbsd.aarch64.sysroot.v1', 'oxtech-ember/EmberBSD', revision, tag, 'aarch64', 'evbarm']
  qualification = manifest.fetch('qualification')
  raise 'Published sysroot has no target qualification' unless qualification.is_a?(Hash) && qualification['source_commit'] == revision
  required_checks = %w[libc_aliases cross_c11 cross_cxx20 target_c11 target_cxx20 base_loader_smoke fork_cas]
  raise 'Incomplete target qualification' unless required_checks.all? { |name| qualification.fetch('checks', {})[name] == true }
  files = manifest.fetch('files')
  raise 'Invalid file manifest' unless files.is_a?(Array) && files.all? { |file| file.is_a?(Hash) }
  %w[base.tar.xz comp.tar.xz build-profile.json].each do |name|
    matches = files.select { |file| file['name'] == name }
    raise 'Missing or duplicate asset: ' + name unless matches.length == 1
    file = matches.first
    raise 'Invalid asset hash or size' unless file['sha256'].is_a?(String) && file['sha256'].match?(/\A[0-9a-f]{64}\z/) &&
      file['size'].is_a?(Integer) && file['size'].positive? && file['size'] < 2**31
    path = fetch.call(name)
    raise 'Downloaded asset differs: ' + name unless File.size(path) == file['size'] && Digest::SHA256.file(path).hexdigest == file['sha256']
  end
  profile = JSON.parse(File.read(downloads + '/build-profile.json'))
  raise 'Build provenance differs' unless profile == manifest['build_profile'] && profile['source_commit'] == revision &&
    profile['status'] == 'built' && profile['source_repository'] == 'https://github.com/oxtech-ember/EmberBSD'
  %w[base comp].each do |set|
    name = set + '.tar.xz'
    hash = files.find { |file| file['name'] == name }.fetch('sha256')
    raise 'Mixed set provenance: ' + name unless profile.fetch('output_sha256').fetch('release/evbarm-aarch64/binary/sets/' + name) == hash &&
      qualification.fetch(set + '_sha256') == hash
  end
  inventory = EmberSysrootArchive.extract(%w[base comp].map { |name| downloads + '/' + name + '.tar.xz' }, work + '/sysroot')
  root = work + '/sysroot'
  aliases = %w[lib/libc.so lib/libc.so.12 usr/lib/libc.so usr/lib/libc.so.12].to_h do |name|
    resolved = File.realpath(root + '/' + name)
    raise 'libc alias escapes sysroot' unless resolved.start_with?(root + '/')
    [name, {'path' => resolved.delete_prefix(root + '/'), 'sha256' => Digest::SHA256.file(resolved).hexdigest}]
  end
  raise 'libc aliases resolve to different bytes' unless aliases.values.map { |value| value['sha256'] }.uniq.length == 1
  %w[usr/include/stdio.h usr/include/pthread.h usr/lib/crt0.o usr/lib/crti.o usr/lib/crtn.o usr/lib/libc.a usr/lib/libpthread.a].each do |name|
    raise 'Missing development input: ' + name unless File.file?(root + '/' + name)
  end
  [root + '/usr/lib/crt0.o', File.realpath(root + '/lib/libc.so.12')].each do |path|
    bytes = File.binread(path, 20)
    raise 'Wrong target ELF architecture' unless bytes.byteslice(0, 6) == "\x7fELF\x02\x01".b && bytes.byteslice(18, 2) == [183].pack('v')
  end
  File.write(work + '/sysroot-files.json', JSON.pretty_generate(inventory) + "\n")
  File.write(work + '/receipt.json', JSON.pretty_generate({'source_commit' => revision, 'manifest_sha256' => expected_manifest,
    'release_url' => base, 'libc_aliases' => aliases, 'entries' => inventory.length,
    'links' => 'Absolute archive symlinks are normalized to relative paths inside this target snapshot. Regular file bytes are unchanged.',
    'scope' => 'OS base/comp only. Cross compiler and GCC16 package headers/runtime are separate inputs.'}) + "\n")
  puts 'PASS: verified AArch64 OS sysroot at ' + root
rescue StandardError => e
  warn 'Sysroot import stopped: ' + e.message
  exit 1
end
