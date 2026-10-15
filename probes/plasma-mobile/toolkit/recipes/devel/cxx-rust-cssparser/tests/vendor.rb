#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted derived vendor source regression.
require 'tmpdir'
require 'fileutils'
require 'digest'
require 'json'
require 'zlib'
require 'rubygems/package'
helper = File.expand_path('../files/vendor.rb', __dir__)
abort 'FAIL: reproducible vendor helper is missing' unless File.file?(helper)
require helper
def expect_failure(reason)
  begin
    yield
  rescue CssVendor::Error
    return
  end
  abort 'FAIL: accepted ' + reason
end
Dir.mktmpdir('ember-css-vendor-', '/tmp') do |work|
  vendor = work + '/vendor'
  crate = vendor + '/fixture-1.0.0'
  cache = work + '/cache/index'
  FileUtils.mkdir_p([crate + '/src', cache])
  files = {'LICENSE-MIT' => "MIT license fixture\n", 'src/lib.rs' => "pub fn fixture() {}\n"}
  files.each { |name, data| File.write(crate + '/' + name, data) }
  archive = cache + '/fixture-1.0.0.crate'
  Zlib::GzipWriter.open(archive) do |gzip|
    gzip.mtime = 0
    Gem::Package::TarWriter.new(gzip) do |tar|
      files.each do |name, data|
        tar.add_file_simple('fixture-1.0.0/' + name, 0644, data.bytesize) { |io| io.write(data) }
      end
    end
  end
  checksum = Digest::SHA256.file(archive).hexdigest
  packages = [{'name' => 'fixture', 'version' => '1.0.0', 'checksum' => checksum}]
  sums = files.transform_values { |data| Digest::SHA256.hexdigest(data) }
  metadata = {'package' => checksum, 'files' => sums.dup}
  File.write(crate + '/.cargo-checksum.json', JSON.generate(metadata))
  result = CssVendor.audit(vendor, work + '/cache', packages)
  abort 'FAIL: original crate license not retained' unless result.fetch('license_files') == 1
  ENV['SOURCE_DATE_EPOCH'] = '1234'
  CssVendor.pack(vendor, work + '/first.tar')
  abort 'FAIL: caller epoch changed' unless ENV['SOURCE_DATE_EPOCH'] == '1234'
  FileUtils.chmod_R(0700, vendor)
  files.each_key { |name| File.chmod(0600, crate + '/' + name) }
  File.chmod(0600, crate + '/.cargo-checksum.json')
  File.utime(Time.at(1234567), Time.at(1234567), crate + '/src/lib.rs')
  CssVendor.pack(vendor, work + '/second.tar')
  abort 'FAIL: archive depends on metadata or invocation time' unless File.binread(work + '/first.tar') == File.binread(work + '/second.tar')
  File.open(work + '/first.tar', 'rb') do |archive_io|
    Gem::Package::TarReader.new(archive_io) do |tar|
      tar.each do |entry|
        h = entry.header
        abort 'FAIL: noncanonical USTAR metadata' unless h.uid == 0 && h.gid == 0 && h.mtime == 0 && h.magic == 'ustar'
        abort 'FAIL: unstable file modes' unless h.mode == (entry.directory? ? 0755 : 0644)
      end
    end
  end
  abort 'FAIL: host tar cannot read canonical archive' unless system('tar', '-tf', work + '/first.tar', out: File::NULL)
  File.symlink('src/lib.rs', crate + '/link')
  expect_failure('vendor symlink') { CssVendor.audit(vendor, work + '/cache', packages) }
  File.unlink(crate + '/link')
  FileUtils.mkdir_p(vendor + '/foreign-1.0.0')
  expect_failure('foreign crate directory') { CssVendor.audit(vendor, work + '/cache', packages) }
  Dir.rmdir(vendor + '/foreign-1.0.0')
  File.chmod(0755, crate + '/src/lib.rs')
  CssVendor.pack(vendor, work + '/executable.tar')
  File.open(work + '/executable.tar', 'rb') do |io|
    Gem::Package::TarReader.new(io) do |tar|
      tar.each do |entry|
        next unless entry.full_name.end_with?('/src/lib.rs')
        abort 'FAIL: executable bit omitted' unless entry.header.mode == 0755
      end
    end
  end
  File.write(crate + '/unexpected', 'extra')
  expect_failure('unrecorded vendored file') { CssVendor.audit(vendor, work + '/cache', packages) }
  File.unlink(crate + '/unexpected')
  File.write(crate + '/LICENSE-MIT', "changed license\n")
  metadata['files']['LICENSE-MIT'] = Digest::SHA256.file(crate + '/LICENSE-MIT').hexdigest
  File.write(crate + '/.cargo-checksum.json', JSON.generate(metadata))
  expect_failure('license changed together with its local checksum') { CssVendor.audit(vendor, work + '/cache', packages) }
  File.write(crate + '/LICENSE-MIT', files.fetch('LICENSE-MIT'))
  metadata['files']['LICENSE-MIT'] = sums.fetch('LICENSE-MIT')
  File.write(crate + '/.cargo-checksum.json', JSON.generate(metadata))
  File.open(archive, 'ab') { |io| io.write('corrupt') }
  expect_failure('crate archive differs from lock checksum') { CssVendor.audit(vendor, work + '/cache', packages) }
  lock = "version = 4\n[[package]]\nname = \"fixture\"\nversion = \"1.0.0\"\nsource = \"registry+https://github.com/rust-lang/crates.io-index\"\nchecksum = \"#{checksum}\"\n"
  abort 'FAIL: original lock closure not parsed' unless CssVendor.lock_packages(lock) == packages
  expect_failure('unchecksummed registry crate') { CssVendor.lock_packages(lock.sub(/^checksum.*\n/, '')) }
  expect_failure('unreviewed git dependency') { CssVendor.lock_packages(lock.sub('registry+https://github.com/rust-lang/crates.io-index', 'git+https://example.invalid/crate')) }
  expect_failure('duplicate crate identity') { CssVendor.lock_packages(lock + lock.sub(/^version = 4\n/, '')) }
  expect_failure('unsafe archive path') { CssVendor.safe_name('vendor/../escape') }
end
if (archive = ENV['CSSPARSER_UPSTREAM_ARCHIVE'])
  abort 'FAIL: original source archive hash' unless Digest::SHA256.file(archive).hexdigest == CssVendor::SOURCE_SHA
  Zlib::GzipReader.open(archive) do |gzip|
    Gem::Package::TarReader.new(gzip) do |tar|
      found = false
      tar.each do |entry|
        next unless entry.full_name == 'cxx-rust-cssparser-1.1.0/rust/Cargo.lock'
        lock = entry.read
        abort 'FAIL: original lock hash' unless Digest::SHA256.hexdigest(lock) == CssVendor::LOCK_SHA
        manifest = CssVendor.lock_packages(lock).map { |p| [p.fetch('name'), p.fetch('version'), p.fetch('checksum')].join("\t") }.join("\n") + "\n"
        abort 'FAIL: reviewed closure differs from original lock' unless File.binread(File.expand_path('../files/vendor-crates.tsv', __dir__)) == manifest
        found = true
      end
      abort 'FAIL: original lock missing' unless found
    end
  end
  puts 'PASS: actual pinned upstream archive, Cargo.lock and reviewed 61-crate closure'
end
puts 'PASS: locked crate checksums, complete vendor files/licenses and deterministic readable USTAR'
