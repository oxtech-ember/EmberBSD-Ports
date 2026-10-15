#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Package the separately required base runtime.
require 'digest'
require 'fiddle'
require 'fileutils'
require 'json'
require 'open3'
require 'tmpdir'
require_relative '../development-toolchain/runtime/recipe/files/runtime'

module InstallerRuntimeBundle
  NAME = GCC16Runtime::NAME
  ARCHIVE = 'runtime-gcc16.tar.xz'
  LIMIT = 64 * 1024 * 1024
  META = %w[+CONTENTS +COMMENT +DESC +BUILD_INFO +BUILD_VERSION +SIZE_PKG +SIZE_ALL].freeze
  def self.check(value, message)
    raise GCC16Runtime::Invalid, message unless value
  end

  def self.run(*args)
    out, err, status = Open3.capture3({ 'COPYFILE_DISABLE' => '1', 'TAR_OPTIONS' => nil, 'LC_ALL' => 'C' }, *args)
    check(status.success?, "Command failed: #{args.first}: #{out}#{err}")
    out
  end

  def self.fingerprint(source)
    names = [NAME + '.tgz', 'package.sha256', 'provenance.json'].sort
    check(Dir.children(source).sort == names, 'Input must be the complete runtime.rb create output')
    names.to_h do |name|
      path = source + '/' + name
      check(File.file?(path) && !File.symlink?(path), "Missing regular runtime input: #{name}")
      [name, Digest::SHA256.file(path).hexdigest]
    end
  end

  def self.receipt(source)
    result = JSON.parse(File.read(source + '/provenance.json'))
    check(result.keys.sort == %w[elf files metadata], 'Invalid runtime provenance schema')
    files = result.fetch('files')
    check(files.is_a?(Array) && !files.empty? && files.uniq == files && files.all? { |p| p.is_a?(String) && p.match?(%r{\Agcc16/lib/(libgcc_s\.so\.1|libstdc\+\+\.so\.7(?:\.[0-9]+)*)\z}) }, 'Unexpected runtime payload selection')
    check((%w[gcc16/lib/libgcc_s.so.1 gcc16/lib/libstdc++.so.7] - files).empty?, 'Missing required runtime libraries')
    metadata = result.fetch('metadata')
    required = { 'OPSYS' => 'NetBSD', 'OS_VERSION' => '11.0', 'MACHINE_ARCH' => 'x86_64', 'PKGPATH' => 'lang/gcc16-runtime',
      'PKGNAME' => NAME, 'LICENSE' => 'gnu-gpl-v3', 'GCC_VERSION' => GCC16Runtime::VERSION,
      'GCC_RUNTIME_SONAME' => 'libstdc++.so.7', 'GCC_SOURCE_SHA256' => GCC16Runtime::SOURCE_SHA256 }
    hashes = %w[GCC_RECIPE_SHA256 GCC_RECIPE_DISTINFO_SHA256 GCC_RUNTIME_INPUTS_SHA256 GCC_RUNTIME_STAGE_SHA256 GCC_RUNTIME_LINKS_SHA256]
    check(metadata.is_a?(Hash) && metadata.keys.sort == (required.keys + hashes + ['EMBERBSD_SEED_SOURCE']).sort, 'Invalid runtime metadata fields')
    check(required.all? { |k, v| metadata[k] == v }, 'Wrong runtime target, source or provider')
    check(hashes.all? { |k| metadata[k].is_a?(String) && metadata[k].match?(/\A[0-9a-f]{64}\z/) } && metadata['EMBERBSD_SEED_SOURCE'].match?(/\A[0-9a-f]{40}\z/), 'Invalid runtime source receipts')
    check(result['elf'].is_a?(Hash) && result['elf'].keys.sort == files.sort, 'Invalid runtime ELF receipts')
    { files: files, metadata: metadata, elf: result['elf'] }
  end

  def self.audit(source, payload, tar)
    package = source + '/' + NAME + '.tgz'
    check(File.read(source + '/package.sha256') == "#{Digest::SHA256.file(package).hexdigest}  #{NAME}.tgz\n", 'Runtime package digest mismatch')
    result = receipt(source)
    files = result.fetch(:files) + GCC16Runtime::LICENSES.map { |f| 'share/licenses/gcc16-runtime/' + f }
    names = run(tar, '-tf', package).lines.map(&:chomp)
    check(names.uniq == names && (names - META).sort == files.sort, 'Unexpected runtime package payload')
    # No parent directory is an archive member. Only the approved DSO aliases may be symlinks.
    listing = run(tar, '-tvf', package).lines
    check(listing.length == names.length && listing.each_with_index.all? { |line, i| line.start_with?('-') || (result[:files].include?(names[i]) && line.start_with?('l')) }, 'Special file or metadata link in runtime package')
    run(tar, '-xf', package, '-C', payload)
    fresh_elf = result.fetch(:files).to_h do |name|
      path = payload + '/' + name
      if File.symlink?(path)
        target = File.readlink(path)
        check(!target.start_with?('/') && result[:files].include?(File.expand_path(target, File.dirname(path)).delete_prefix(payload + '/')), 'Unsafe runtime alias')
      end
      resolved = File.realpath(path)
      check(resolved.start_with?(payload + '/') && result[:files].include?(resolved.delete_prefix(payload + '/')), 'Runtime alias escapes shipped payload')
      soname = name.include?('libstdc++') ? 'libstdc++.so.7' : 'libgcc_s.so.1'
      [name, GCC16Runtime::ELF.new(resolved).verify(soname)]
    end
    check(fresh_elf == result.fetch(:elf), 'Runtime ELF receipt differs from package bytes')
    GCC16Runtime::LICENSES.each do |name|
      path = payload + '/share/licenses/gcc16-runtime/' + name
      check(File.file?(path) && !File.symlink?(path) && File.size(path).positive?, 'Missing runtime license or exception')
    end
    # Use the runtime owner's audit for inventory, metadata, conflicts and installation prefix.
    GCC16Runtime.audit_package(package, payload, result)
    metadata = File.readlines(payload + '/+BUILD_INFO', chomp: true)
    check(result[:metadata].all? { |k, v| metadata.grep(/^#{Regexp.escape(k)}=/) == ["#{k}=#{v}"] }, 'Duplicate or changed runtime metadata')
    # Restrict packing-list directives and verify every payload digest. No install commands are accepted.
    lines = File.readlines(payload + '/+CONTENTS', chomp: true)
    seen = []; conflicts = []; names_seen = []; ignored = []
    until lines.empty?
      line = lines.shift
      case line
      when '@cwd /usr/pkg' then next
      when "@name #{NAME}" then names_seen << line
      when /^@pkgcfl (.+)$/ then conflicts << Regexp.last_match(1)
      when '@ignore'
        entry = lines.shift
        check(META.include?(entry) && entry != '+CONTENTS', 'Unexpected ignored runtime metadata')
        ignored << entry
      else
        check(files.include?(line), 'Unsafe runtime packing-list directive or payload')
        path = payload + '/' + line
        expected = File.symlink?(path) ? "@comment Symlink:#{File.readlink(path)}" : "@comment MD5:#{Digest::MD5.file(path).hexdigest}"
        check(lines.shift == expected, "Runtime payload digest mismatch: #{line}")
        seen << line
      end
    end
    check(seen.sort == files.sort && names_seen.length == 1 && conflicts.sort == GCC16Runtime::CONFLICTS.sort && ignored.uniq == ignored && (names - ['+CONTENTS'] - files).sort == ignored.sort, 'Runtime packing-list inventory mismatch')
    result
  end

  def self.publish(source, destination)
    library = Fiddle::Handle::DEFAULT
    if RUBY_PLATFORM.include?('darwin')
      function = Fiddle::Function.new(library['renamex_np'], [Fiddle::TYPE_VOIDP, Fiddle::TYPE_VOIDP, Fiddle::TYPE_INT], Fiddle::TYPE_INT)
      result = function.call(source, destination, 4) # RENAME_EXCL
    elsif RUBY_PLATFORM.include?('linux')
      function = Fiddle::Function.new(library['renameat2'], [Fiddle::TYPE_INT, Fiddle::TYPE_VOIDP, Fiddle::TYPE_INT, Fiddle::TYPE_VOIDP, Fiddle::TYPE_INT], Fiddle::TYPE_INT)
      result = function.call(-100, source, -100, destination, 1) # AT_FDCWD, RENAME_NOREPLACE
    else
      raise GCC16Runtime::Invalid, 'Atomic no-replace publication requires macOS or Linux'
    end
    raise SystemCallError.new('Cannot publish runtime bundle', Fiddle.last_error) unless result.zero?
  end

  def self.build(source_arg, output_arg)
    source = File.realpath(source_arg)
    output = File.expand_path(output_arg)
    check(!File.exist?(output) && !File.symlink?(output), 'Output already exists')
    parent = File.realpath(File.dirname(output))
    output = parent + '/' + File.basename(output)
    check(!output.start_with?(source + '/'), 'Output must be outside the runtime create output')
    hashes = fingerprint(source)
    tar = ENV.fetch('BSDTAR', 'bsdtar')
    check(run(tar, '--version').include?('libarchive'), 'Use bsdtar/libarchive')
    Dir.mktmpdir('.gcc16-bundle-', parent) do |work|
      snapshot = work + '/source'; Dir.mkdir(snapshot)
      hashes.each_key { |name| FileUtils.cp(source + '/' + name, snapshot + '/' + name) }
      check(fingerprint(snapshot) == hashes, 'Runtime inputs changed while copying')
      inspect = work + '/inspect'; Dir.mkdir(inspect)
      result = audit(snapshot, inspect, tar)
      inner = work + '/inner'; FileUtils.mkdir_p(inner + '/All')
      package = inner + '/All/' + NAME + '.tgz'
      FileUtils.cp(snapshot + '/' + NAME + '.tgz', package)
      File.chmod(0644, package)
      package_hash = Digest::SHA512.file(package).hexdigest
      File.write(inner + '/ROOTS', NAME + "\n")
      File.write(inner + '/PROFILE', "gcc16\n")
      File.write(inner + '/SHA512', "SHA512 (#{NAME}.tgz) = #{package_hash}\n")
      directory = work + '/result'; Dir.mkdir(directory)
      archive = directory + '/' + ARCHIVE
      run(tar, '--no-xattrs', '--no-acls', '--no-fflags', '--format=pax', '--uid', '0', '--gid', '0', '--uname', 'root', '--gname', 'wheel', '-cJf', archive, '-C', inner, 'All', 'ROOTS', 'SHA512', 'PROFILE')
      check(File.size(archive) <= LIMIT, 'Runtime bundle exceeds the 64 MiB installer capacity')
      digest = Digest::SHA512.file(archive).hexdigest
      File.write(directory + '/SHA512', "SHA512 (#{ARCHIVE}) = #{digest}\n")
      provenance = { 'format' => 'emberbsd-installer-gcc16-v1', 'profile' => 'gcc16', 'target' => 'amd64',
        'source_sha256' => hashes, 'runtime_receipt' => result, 'package' => { 'file' => NAME + '.tgz', 'bytes' => File.size(package), 'sha256' => Digest::SHA256.file(package).hexdigest, 'sha512' => package_hash },
        'bundle' => { 'file' => ARCHIVE, 'bytes' => File.size(archive), 'sha512' => digest, 'limit_bytes' => LIMIT },
        'tools_sha256' => [__FILE__, File.expand_path('../development-toolchain/runtime/recipe/files/runtime.rb', __dir__)].to_h { |p| [File.basename(p), Digest::SHA256.file(p).hexdigest] },
        'validation' => 'Fresh payload, metadata, conflicts, licenses and ELF audit. Local receipts are not a source attestation. No target execution.' }
      File.write(directory + '/PROVENANCE.json', JSON.pretty_generate(provenance) + "\n")
      check(fingerprint(source) == hashes && Digest::SHA256.file(package).hexdigest == hashes.fetch(NAME + '.tgz'), 'Runtime source or package changed during preparation')
      publish(directory, output)
      puts "SHA512 (#{ARCHIVE}) = #{digest}"
      puts "Bundle bytes: #{File.size(output + '/' + ARCHIVE)}; installer limit: #{LIMIT}"
    end
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    InstallerRuntimeBundle.check(ARGV.length == 2, 'Usage: bundle-gcc16.rb RUNTIME_CREATE_OUTPUT NEW_OUTPUT')
    InstallerRuntimeBundle.build(*ARGV)
  rescue StandardError => e
    warn "FAIL: #{e.message}"
    exit 1
  end
end
