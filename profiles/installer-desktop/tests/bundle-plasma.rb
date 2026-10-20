#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Native pkgtools fixtures, no target execution.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rbconfig'
require 'rubygems/package'
require 'stringio'
abort 'Usage: bundle-plasma.rb NEW_WORK' unless ARGV.length == 1
work = File.expand_path(ARGV.first)
Dir.mkdir(work)
create = ENV.fetch('PKG_CREATE', 'pkg_create')
info = ENV.fetch('PKG_INFO', 'pkg_info')
admin = ENV.fetch('PKG_ADMIN', 'pkg_admin')
tar = ENV.fetch('BSDTAR', 'bsdtar')
python = ENV.fetch('PYTHON', 'python3')
sdk = ENV.fetch('EMBERBSD_SDK_SOURCE')
environment = { 'PKG_INFO' => info, 'PKG_ADMIN' => admin, 'BSDTAR' => tar }
bundler = File.expand_path('../bundle-plasma.rb', __dir__)
auditor = File.expand_path('../../../probes/plasma-mobile/toolkit/cross/prepare-package-set.py', __dir__)
run = lambda do |*command|
  output, error, status = Open3.capture3(*command)
  raise "Command failed: #{command.inspect}\n#{output}#{error}" unless status.success?
  output
end
fixture = lambda do |name, options = {}|
  area = File.join(work, name)
  payload = File.join(area, 'payload')
  cache = File.join(area, 'cache')
  database = File.join(area, 'pkgdb')
  FileUtils.mkdir_p([File.join(payload, 'bin'), cache, database])
  File.write(File.join(area, 'comment'), "Plasma bundle fixture\n")
  File.write(File.join(area, 'description'), "Header-only ELF fixtures; not target executables.\n")
  File.write(File.join(area, 'build-info'), "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=x86_64\nOBJECT_FMT=ELF\n")
  packages = { 'plasma-fixture-leaf-1.0' => %w[Xwayland dbus-run-session],
               'plasma-fixture-root-1.0' => %w[startplasma-wayland kwin_wayland plasmashell] }
  packages.each do |package, programs|
    files = programs.reject { |program| program == options[:missing] }.map do |program|
      header = "\0".b * 64
      header[0, 7] = "\x7fELF\x02\x01\x01".b
      header[18, 2] = [options[:foreign] == program ? 183 : 62].pack('v')
      File.binwrite(File.join(payload, "bin/#{program}"), header)
      File.chmod(options[:not_executable] == program ? 0644 : 0755, File.join(payload, "bin/#{program}"))
      "bin/#{program}"
    end
    if options[:symlink] && programs.include?('startplasma-wayland')
      File.rename(File.join(payload, 'bin/startplasma-wayland'), File.join(payload, 'bin/plasma-launcher'))
      File.symlink('plasma-launcher', File.join(payload, 'bin/startplasma-wayland'))
      files << 'bin/plasma-launcher'
    end
    plist = File.join(area, 'plist')
    File.write(plist, files.join("\n") + "\n")
    command = [create, '-p', payload, '-I', '/usr/pkg', '-f', plist, '-c', File.join(area, 'comment'),
               '-d', File.join(area, 'description'), '-B', File.join(area, 'build-info')]
    command += ['-P', 'plasma-fixture-leaf>=1.0'] if package.include?('-root-')
    archive = File.join(cache, "#{package}.tgz")
    run.call(*command, archive)
    installed = File.join(database, package)
    Dir.mkdir(installed)
    run.call(tar, '-tf', archive).lines.map(&:chomp).grep(/^\+/).each do |entry|
      File.binwrite(File.join(installed, entry), run.call(tar, '-xOf', archive, entry))
    end
  end
  source = File.join(area, 'source-set')
  index = File.join(area, 'archives.txt')
  archives = Dir[File.join(cache, '*.tgz')].sort
  File.write(index, archives.join("\n") + "\n")
  if options[:foreign]
    FileUtils.mkdir_p(File.join(source, 'packages'))
    archives.each { |path| FileUtils.cp(path, File.join(source, 'packages')) }
    File.write(File.join(source, 'install-order.txt'), packages.keys.map { |pkg| "#{pkg}.tgz\n" }.join)
    File.write(File.join(source, 'roots.txt'), "plasma-fixture-root-1.0\n")
    File.write(File.join(source, 'target.txt'), "OPSYS=NetBSD\nOS_VERSION=11.0\nMACHINE_ARCH=x86_64\nOBJECT_FMT=ELF\n")
    File.write(File.join(source, 'packages.sha256'), archives.map do |path|
      "#{Digest::SHA256.file(path).hexdigest}  packages/#{File.basename(path)}\n"
    end.join)
  else
    run.call(environment, python, '-B', '-I', '-S', auditor, '--sdk-source', sdk, '--target', 'amd64', database, index, source, 'plasma-fixture-root-1.0')
  end
  source
end
count = 0
check = lambda do |name, source, expected = nil, destination = nil|
  destination ||= File.join(work, "bundle-#{name}")
  before = Dir[File.join(source, '**/*')].select { |path| File.file?(path) }.to_h { |path| [path, Digest::SHA256.file(path).hexdigest] }
  output, error, status = Open3.capture3(environment, RbConfig.ruby, bundler, source, destination)
  File.write(File.join(work, "#{name}.log"), output + error)
  if expected
    raise "#{name} did not reject #{expected}: #{output}#{error}" if status.success? || !(output + error).include?(expected)
    raise 'Failed bundle published output' if File.exist?(destination) && !%w[existing-output symlink-output].include?(name)
  else
    raise "#{name} failed: #{output}#{error}" unless status.success?
    archive = File.join(destination, 'desktop-plasma.tar.xz')
    raise 'Wrong Plasma marker' unless run.call(tar, '-xOf', archive, 'PROFILE') == "plasma\n"
    raise 'Wrong root package names' unless run.call(tar, '-xOf', archive, 'ROOTS') == File.read(File.join(source, 'roots.txt'))
    hashes = run.call(tar, '-xOf', archive, 'SHA512')
    Dir[File.join(source, 'packages/*.tgz')].each do |path|
      package_filename = File.basename(path)
      raise 'Bundle changed archive bytes' unless run.call(tar, '-xOf', archive, "All/#{package_filename}").b == File.binread(path)
      raise 'Wrong inner digest' unless hashes.include?("SHA512 (#{package_filename}) = #{Digest::SHA512.file(path).hexdigest}\n")
    end
    provenance = JSON.parse(File.read(File.join(destination, 'PROVENANCE.json')))
    raise 'Wrong archive size receipt' unless provenance.fetch('bundle').fetch('bytes') == File.size(archive)
    raise 'Wrong installer capacity boundary' unless provenance.fetch('installer_capacity') ==
      { 'limit_bytes' => 512 * 1024 * 1024, 'fits_current_limit' => true }
    raise 'Missing source byte provenance' unless provenance.fetch('source_sha256').fetch('target.txt') == Digest::SHA256.file(File.join(source, 'target.txt')).hexdigest
    raise 'Wrong outer checksum' unless File.read(File.join(destination, 'SHA512')) == "SHA512 (desktop-plasma.tar.xz) = #{Digest::SHA512.file(archive).hexdigest}\n"
    raw = run.call(tar, '-cf', '-', '--format=pax', "@#{archive}")
    Gem::Package::TarReader.new(StringIO.new(raw.b)) do |reader|
      reader.each do |entry|
        next if %w[x g].include?(entry.header.typeflag)
        raise 'Archive retained host ownership' unless entry.header.uid.zero? && entry.header.gid.zero? && entry.header.uname == 'root' && entry.header.gname == 'wheel'
        raise 'Archive retained Apple metadata' if entry.full_name.split('/').any? { |part| part.start_with?('._') || part == '__MACOSX' }
      end
    end
  end
  raise 'Bundler changed source input' unless before.all? { |path, hash| Digest::SHA256.file(path).hexdigest == hash }
  retained = Dir[File.join(File.dirname(destination), ".#{File.basename(destination)}-*")]
  if name == 'foreign-elf'
    raise 'Failed auditor workspace was removed' unless retained.length == 1 &&
      error.include?("Retained incomplete auditor workspace: #{retained.first}")
  else
    raise 'Bundler left temporary staging' unless retained.empty?
  end
  count += 1
  puts "PASS: #{name}"
  destination
end
valid = fixture.call('valid')
check.call('valid', valid)
check.call('symlink-program', fixture.call('symlink-program', symlink: true))
foreign = fixture.call('foreign', foreign: 'Xwayland')
check.call('foreign-elf', foreign, 'Wrong ELF machine')
check.call('missing-program', fixture.call('missing', missing: 'plasmashell'), 'Missing Plasma program')
check.call('not-executable', fixture.call('not-executable', not_executable: 'kwin_wayland'), 'Plasma program is not executable')
%w[wrong-target digest roots].each do |name|
  source = File.join(work, name)
  FileUtils.cp_r(valid, source)
  expected = case name
             when 'wrong-target'
               File.write(File.join(source, 'target.txt'), File.read(File.join(source, 'target.txt')).sub('x86_64', 'aarch64'))
               'Target receipt mismatch'
             when 'digest'
               File.open(Dir[File.join(source, 'packages/*.tgz')].first, 'ab') { |file| file.write('corrupt') }
               'SHA256 mismatch'
             else
               File.write(File.join(source, 'roots.txt'), "missing-root-1.0\n")
               'Invalid, missing or duplicate root'
             end
  check.call(name, source, expected)
end
existing = File.join(work, 'existing')
Dir.mkdir(existing)
File.write(File.join(existing, 'sentinel'), 'preserve')
check.call('existing-output', valid, 'Output already exists', existing)
raise 'Existing output changed' unless File.read(File.join(existing, 'sentinel')) == 'preserve'
link = File.join(work, 'output-link')
File.symlink(File.join(work, 'missing-output'), link)
check.call('symlink-output', valid, 'Output already exists', link)
raise 'Output symlink changed' unless File.readlink(link) == File.join(work, 'missing-output')
check.call('nested-output', valid, 'Output must be outside the source package set', File.join(valid, 'output'))
# Create the destination after validation starts. Publishing must not replace it
# or move temporary files into the existing directory.
race = File.join(work, 'race-output')
Open3.popen3(environment, RbConfig.ruby, bundler, valid, race) do |input, output, error, process|
  input.close
  deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + 10
  until Dir[File.join(work, '.race-output-*')].any?
    raise 'Bundle ended before publication race' unless process.alive?
    raise 'Timed out waiting for bundle staging' if Process.clock_gettime(Process::CLOCK_MONOTONIC) > deadline
    sleep 0.01
  end
  Dir.mkdir(race)
  File.write(File.join(race, 'sentinel'), 'preserve-race')
  text = output.read + error.read
  raise "Concurrent destination was accepted: #{text}" if process.value.success? || !text.include?('Cannot publish bundle output')
end
raise 'Concurrent output changed' unless Dir.children(race) == ['sentinel'] && File.read(File.join(race, 'sentinel')) == 'preserve-race'
raise 'Publication race left staging' unless Dir[File.join(work, '.race-output-*')].empty?
count += 1
puts 'PASS: concurrent-output-preserved'
puts "PASS: #{count} native package and tar fixtures; no target code or install scripts executed"
