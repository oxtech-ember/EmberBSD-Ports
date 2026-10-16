# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted), 2026-10-16.
# Test the actual importer CLI with a local curl fixture. This does not test
# HTTPS, execute target ELF files, or provide target qualification evidence.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'shellwords'
require 'tmpdir'

def check(condition, message)
  abort 'FAIL: ' + message unless condition
end

def write_json(path, value)
  File.write(path, JSON.pretty_generate(value) + "\n")
end

def read_json(path)
  JSON.parse(File.read(path))
end

def file_record(dir, name)
  path = File.join(dir, name)
  {'name' => name, 'size' => File.size(path), 'sha256' => Digest::SHA256.file(path).hexdigest}
end

def pack_set(input, output)
  text, error, result = Open3.capture3('tar', '-cJf', output, '-C', input, '.')
  check(result.success?, 'fixture tar failed: ' + text + error)
end

def change_manifest(dir)
  path = File.join(dir, 'manifest.json')
  manifest = read_json(path)
  yield manifest
  write_json(path, manifest)
end

def change_profile(dir)
  path = File.join(dir, 'build-profile.json')
  profile = read_json(path)
  yield profile
  write_json(path, profile)
  change_manifest(dir) do |manifest|
    manifest['build_profile'] = profile
    manifest.fetch('files').map! { |file| file['name'] == 'build-profile.json' ? file_record(dir, file['name']) : file }
  end
end

driver = File.expand_path('../fetch-sysroot.rb', __dir__)
Dir.mktmpdir('ember-fetch-sysroot-cli') do |dir|
  revision = 'a' * 40
  tag = "build-#{revision}-aarch64-sysroot"
  prefix = "https://github.com/oxtech-ember/EmberBSD/releases/download/#{tag}/"
  template = File.join(dir, 'served-template')
  base_input, comp_input = %w[base-input comp-input].map { |name| File.join(dir, name) }
  [template, base_input, comp_input].each { |path| Dir.mkdir(path) }
  # Structural headers only. These bytes are not executable target programs.
  elf = "\x7fELF\x02\x01\x01".b.ljust(64, "\0")
  elf[18, 2] = [183].pack('v')
  elf << "fixture bytes\0\xff".b
  FileUtils.mkdir_p(File.join(base_input, 'lib'))
  FileUtils.mkdir_p(File.join(base_input, 'usr/lib'))
  File.binwrite(File.join(base_input, 'lib/libc.so.12.229'), elf)
  File.symlink('libc.so.12.229', File.join(base_input, 'lib/libc.so.12'))
  File.symlink('libc.so.12', File.join(base_input, 'lib/libc.so'))
  File.symlink('/lib/libc.so.12', File.join(base_input, 'usr/lib/libc.so.12'))
  File.symlink('/lib/libc.so', File.join(base_input, 'usr/lib/libc.so'))
  FileUtils.mkdir_p(File.join(comp_input, 'usr/include'))
  FileUtils.mkdir_p(File.join(comp_input, 'usr/lib'))
  %w[stdio.h pthread.h].each { |name| File.write(File.join(comp_input, 'usr/include', name), "/* fixture */\n") }
  %w[crt0.o crti.o crtn.o].each { |name| File.binwrite(File.join(comp_input, 'usr/lib', name), elf) }
  %w[libc.a libpthread.a].each { |name| File.binwrite(File.join(comp_input, 'usr/lib', name), "!<arch>\n") }
  pack_set(base_input, File.join(template, 'base.tar.xz'))
  pack_set(comp_input, File.join(template, 'comp.tar.xz'))
  hashes = %w[base comp].to_h do |set|
    [set, Digest::SHA256.file(File.join(template, set + '.tar.xz')).hexdigest]
  end
  # This intentionally contains only fields consumed by the importer. It is
  # not a publisher-valid release kit, and its check declarations are fixtures.
  profile = {'status' => 'built', 'source_commit' => revision,
    'source_repository' => 'https://github.com/oxtech-ember/EmberBSD',
    'output_sha256' => hashes.to_h { |set, hash| ["release/evbarm-aarch64/binary/sets/#{set}.tar.xz", hash] }}
  write_json(File.join(template, 'build-profile.json'), profile)
  checks = %w[libc_aliases cross_c11 cross_cxx20 target_c11 target_cxx20 base_loader_smoke fork_cas]
  qualification = {'source_commit' => revision, 'checks' => checks.to_h { |name| [name, true] },
    'base_sha256' => hashes.fetch('base'), 'comp_sha256' => hashes.fetch('comp')}
  manifest = {'schema' => 'emberbsd.aarch64.sysroot.v1', 'repository' => 'oxtech-ember/EmberBSD',
    'source_commit' => revision, 'release_tag' => tag, 'architecture' => 'aarch64', 'machine' => 'evbarm',
    'qualification' => qualification, 'build_profile' => profile,
    'files' => %w[base.tar.xz comp.tar.xz build-profile.json].map { |name| file_record(template, name) }}
  write_json(File.join(template, 'manifest.json'), manifest)

  commands = File.join(dir, 'commands')
  Dir.mkdir(commands)
  curl_fixture = File.join(commands, 'curl-fixture.rb')
  File.write(curl_fixture, <<~'RUBY')
    require 'fileutils'
    require 'json'
    expected_options = %w[--fail --location --silent --show-error --proto =https --proto-redir =https --tlsv1.2 --output]
    abort 'Unexpected curl protocol policy' unless ARGV.length == expected_options.length + 2 && ARGV.take(expected_options.length) == expected_options
    destination, url = ARGV.last(2)
    prefix = ENV.fetch('EMBER_FIXTURE_PREFIX')
    name = url.delete_prefix(prefix)
    abort 'Unexpected production URL' unless url.start_with?(prefix) && %w[manifest.json base.tar.xz comp.tar.xz build-profile.json].include?(name)
    abort 'Unexpected download path' unless destination == File.join(ENV.fetch('EMBER_FIXTURE_WORK'), 'downloads', name)
    File.open(ENV.fetch('EMBER_FIXTURE_CALLS'), 'a') { |file| file.puts(JSON.generate({'name' => name, 'url' => url, 'argv' => ARGV})) }
    FileUtils.cp(File.join(ENV.fetch('EMBER_FIXTURE_SERVED'), name), destination)
  RUBY
  curl = File.join(commands, 'curl')
  File.write(curl, "#!/bin/sh\nexec #{Shellwords.escape(RbConfig.ruby)} #{Shellwords.escape(curl_fixture)} \"$@\"\n")
  File.chmod(0755, curl)
  invoke = lambda do |served, work, calls, pin|
    File.write(calls, '')
    environment = {'PATH' => commands + ':' + ENV.fetch('PATH'), 'EMBER_FIXTURE_PREFIX' => prefix,
      'EMBER_FIXTURE_SERVED' => served, 'EMBER_FIXTURE_WORK' => work, 'EMBER_FIXTURE_CALLS' => calls}
    text, error, status = Open3.capture3(environment, RbConfig.ruby, driver, revision, pin, work)
    [text, error, status, File.readlines(calls).map { |line| JSON.parse(line).fetch('name') }]
  end
  digest = Digest::SHA256.file(File.join(template, 'manifest.json')).hexdigest
  work, calls = %w[accepted calls.jsonl].map { |name| File.join(dir, name) }
  text, error, status, fetched = invoke.call(template, work, calls, digest)
  check(status.success?, "valid CLI fixture failed: #{text}#{error}")
  check(fetched == %w[manifest.json base.tar.xz comp.tar.xz build-profile.json], 'valid import skipped or changed downloads')
  receipt = read_json(File.join(work, 'receipt.json'))
  check(receipt.values_at('source_commit', 'manifest_sha256', 'release_url') == [revision, digest, prefix], 'import lost the trusted source identity')
  provider = File.join(work, 'sysroot/lib/libc.so.12.229')
  check(File.binread(provider) == elf, 'CLI changed provider bytes')
  %w[lib/libc.so lib/libc.so.12 usr/lib/libc.so usr/lib/libc.so.12].each do |name|
    check(File.realpath(File.join(work, 'sysroot', name)) == provider, 'CLI failed to bind a libc alias to the target provider')
    check(receipt.fetch('libc_aliases').fetch(name).fetch('sha256') == Digest::SHA256.hexdigest(elf), 'CLI receipt has another libc provider')
  end
  check(read_json(File.join(work, 'sysroot-files.json')).key?('usr/lib/crt0.o'), 'CLI omitted the file inventory')
  puts 'PASS: actual importer CLI creates a pinned local snapshot and receipts (curl fixture only)'

  refuse = lambda do |label, expected, expected_fetches: nil, wrong_pin: nil, &change|
    served = File.join(dir, 'served-' + label)
    FileUtils.cp_r(template, served)
    change.call(served) if change
    # Changed fixtures receive their own trusted unit-test pin so semantic
    # refusal tests reach beyond the initial manifest hash gate.
    pin = wrong_pin || Digest::SHA256.file(File.join(served, 'manifest.json')).hexdigest
    output = File.join(dir, 'rejected-' + label)
    text, error, status, fetched = invoke.call(served, output, File.join(dir, label + '-calls.jsonl'), pin)
    check(!status.success? && expected.match?(error), "#{label} stopped incorrectly: #{text}#{error}")
    check(!File.exist?(File.join(output, 'receipt.json')), label + ' exposed a successful import receipt')
    check(fetched == expected_fetches, label + ' performed unexpected downloads: ' + fetched.inspect) if expected_fetches
    puts 'PASS: refuses ' + label
  end
  refuse.call('wrong-trusted-manifest-pin', /Pinned manifest SHA256 differs/,
    expected_fetches: ['manifest.json'], wrong_pin: '0' * 64)
  refuse.call('changed-set-bytes', /Downloaded asset differs: base.tar.xz/,
    expected_fetches: %w[manifest.json base.tar.xz]) do |served|
    File.open(File.join(served, 'base.tar.xz'), 'ab') { |file| file.write('changed') }
  end
  refuse.call('mixed-manifest-source', /Wrong source/,
    expected_fetches: ['manifest.json']) do |served|
    change_manifest(served) { |m| m['source_commit'] = 'b' * 40 }
  end
  refuse.call('mixed-build-profile-source', /Build provenance differs/) do |served|
    change_profile(served) { |p| p['source_commit'] = 'b' * 40 }
  end
  refuse.call('mixed-qualification-source', /qualification/,
    expected_fetches: ['manifest.json']) do |served|
    change_manifest(served) { |m| m['qualification']['source_commit'] = 'b' * 40 }
  end
  refuse.call('mixed-qualification-set-hash', /Mixed set provenance: comp.tar.xz/) do |served|
    change_manifest(served) { |m| m['qualification']['comp_sha256'] = '0' * 64 }
  end
  refuse.call('mixed-build-set-hash', /Mixed set provenance: base.tar.xz/) do |served|
    change_profile(served) { |p| p['output_sha256']['release/evbarm-aarch64/binary/sets/base.tar.xz'] = '0' * 64 }
  end
  refuse.call('missing-qualification-check', /Incomplete target qualification/,
    expected_fetches: ['manifest.json']) do |served|
    change_manifest(served) { |m| m['qualification']['checks'].delete('target_cxx20') }
  end
  refuse.call('duplicate-set-asset', /Missing or duplicate asset: base.tar.xz/,
    expected_fetches: ['manifest.json']) do |served|
    change_manifest(served) { |m| m['files'] << m['files'].find { |file| file['name'] == 'base.tar.xz' }.dup }
  end
  refuse.call('wrong-manifest-architecture', /Wrong source, schema or architecture/,
    expected_fetches: ['manifest.json']) do |served|
    change_manifest(served) { |m| m['architecture'] = 'amd64' }
  end
  refuse.call('wrong-startup-elf-architecture', /Wrong target ELF architecture/) do |served|
    input = File.join(dir, 'wrong-elf-input')
    FileUtils.cp_r(comp_input, input)
    bytes = elf.dup
    bytes[18, 2] = [62].pack('v') # EM_X86_64, with every provenance hash rebound.
    File.binwrite(File.join(input, 'usr/lib/crt0.o'), bytes)
    pack_set(input, File.join(served, 'comp.tar.xz'))
    hash = Digest::SHA256.file(File.join(served, 'comp.tar.xz')).hexdigest
    change_profile(served) { |p| p['output_sha256']['release/evbarm-aarch64/binary/sets/comp.tar.xz'] = hash }
    change_manifest(served) do |m|
      m['qualification']['comp_sha256'] = hash
      m['files'].map! { |file| file['name'] == 'comp.tar.xz' ? file_record(served, file['name']) : file }
    end
  end
  original_receipt = File.binread(File.join(work, 'receipt.json'))
  text, error, status, fetched = invoke.call(template, work, calls, digest)
  check(!status.success? && error.include?('fresh work directory') && fetched.empty?, "reused output performed a download: #{text}#{error}")
  check(File.binread(File.join(work, 'receipt.json')) == original_receipt, 'reused output changed its accepted receipt')
  puts 'PASS: refuses reused output before any download and preserves its receipt'
end
puts 'PASS: importer CLI provenance and refusal contract; HTTPS and target execution remain outside this fixture'
