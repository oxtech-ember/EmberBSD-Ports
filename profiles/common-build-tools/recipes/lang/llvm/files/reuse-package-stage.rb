#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Verify an explicitly accepted LLVM build.
require 'digest'
require 'fileutils'
require 'find'
require 'json'
require 'open3'

module LLVMStageReuse
  MACHO_MAGIC = %w[cffaedfe cefaedfe feedfacf feedface cafebabe bebafeca cafebabf bfbafeca].map { |h| [h].pack('H*') }.freeze
  module_function

  def check(value, message)
    raise message unless value
  end

  def hash_file(path)
    check(File.file?(path), "Missing input file: #{path}")
    {'path' => File.realpath(path), 'sha256' => Digest::SHA256.file(path).hexdigest, 'mode' => File.stat(path).mode & 0o7777}
  end

  def tree(path, excludes = [])
    check(File.directory?(path) && !File.symlink?(path), "Regular tree required: #{path}")
    result = {}
    Find.find(path) do |entry|
      next if entry == path
      relative = entry.delete_prefix(path + '/')
      Find.prune if excludes.include?(relative)
      stat = File.lstat(entry)
      if stat.symlink?
        result[relative] = ['link', File.readlink(entry)]
      elsif stat.file?
        result[relative] = ['file', stat.mode & 0o7777, Digest::SHA256.file(entry).hexdigest]
      else
        check(stat.directory?, "Unsupported tree entry: #{entry}")
      end
    end
    result.sort.to_h
  end

  def context(path)
    value = JSON.parse(File.binread(path))
    check(value.fetch('schema') == 1, 'Unsupported LLVM input schema')
    target = value.fetch('target')
    arch = target.fetch('arch')
    triple = {'aarch64' => 'aarch64--netbsd', 'x86_64' => 'x86_64--netbsd'}[arch]
    check(target == {'opsys' => 'NetBSD', 'version' => '11.0', 'arch' => arch, 'triple' => triple} && triple,
          'Unsupported LLVM target ABI')
    check(value.fetch('version') == '23.1.3', 'Unsupported LLVM source version')
    check([true, false].include?(value.fetch('install_strip')), 'Explicit CMake install strip mode required')
    check(value.fetch('flags').is_a?(Hash) && !value.fetch('flags').empty?, 'Missing compile contract')
    %w[source build recipe sdk_recipe].each do |key|
      p = value.fetch(key)
      check(p.start_with?('/') && p != '/' && File.directory?(p) && !File.symlink?(p), "Invalid #{key} tree")
    end
    source = value.fetch('source')
    build = value.fetch('build')
    check(build.start_with?(source + '/'), 'Build must belong to the recorded LLVM source')
    %w[compiler native_tools patches target_abi].each do |kind|
      paths = value.fetch('files').fetch(kind)
      check(paths.is_a?(Array) && !paths.empty? && paths.uniq == paths, "Missing or duplicate #{kind} inputs")
      paths.each { |p| check(p.start_with?('/') && File.file?(p), "Invalid #{kind} input") }
    end
    %w[cmake perl tar].each do |key|
      check(value.fetch('files').fetch('native_tools').include?(value.fetch(key)) && File.executable?(value.fetch(key)),
            "#{key} must be an explicit executable native input")
    end
    runtime = value.fetch('runtime')
    check(runtime.fetch('sha256').match?(/\A[0-9a-f]{64}\z/), 'Expected accepted runtime SHA256 required')
    check(hash_file(runtime.fetch('archive')).fetch('sha256') == runtime.fetch('sha256'), 'Runtime archive drift')
    value
  end

  def snapshot(value)
    build = value.fetch('build')
    install_manifest = build + '/install_manifest.txt'
    check(!File.symlink?(install_manifest), 'CMake install manifest must not be a symlink')
    {'files' => value.fetch('files').transform_values { |paths| paths.to_h { |p| [p, hash_file(p)] } },
     'source' => tree(value.fetch('source'), [build.delete_prefix(value.fetch('source') + '/')]),
     # CMake rewrites this one metadata file during --install. It is not an object.
     'build' => tree(build, ['install_manifest.txt']),
     'recipe' => tree(value.fetch('recipe')),
     'sdk_recipe' => tree(value.fetch('sdk_recipe')),
     'manifests' => value.fetch('manifests').transform_values { |p| hash_file(p) },
     'runtime' => hash_file(value.fetch('runtime').fetch('archive'))}
  end

  def run(*command, **options)
    check(system(*command, **options), "Command failed: #{command.first}")
  end

  def validate_full_stage(value, stage)
    lists = value.fetch('manifests')
    check(lists.keys.sort == %w[devel full runtime], 'Three normalized LLVM PLISTs required')
    selector = value.fetch('recipe') + '/files/select-package-stage.pl'
    run(value.fetch('perl'), selector, 'check', stage, lists.fetch('full'), lists.fetch('runtime'),
        lists.fetch('devel'), lists.fetch('full'))
    # The runtime package is accepted separately. Match its complete manifest to
    # the full stage, including symlink targets, before recording SDK hashes.
    archive = value.fetch('runtime').fetch('archive')
    info, error, status = Open3.capture3(value.fetch('tar'), '-xOf', archive, '+BUILD_INFO')
    check(status.success?, "Cannot read runtime metadata: #{error}")
    target = value.fetch('target')
    {'OPSYS' => target.fetch('opsys'), 'OS_VERSION' => target.fetch('version'),
     'MACHINE_ARCH' => target.fetch('arch'), 'OBJECT_FMT' => 'ELF'}.each do |k, v|
      check(info.lines.grep(/^#{k}=/) == ["#{k}=#{v}\n"], "Runtime #{k} mismatch")
    end
    contents, error, status = Open3.capture3(value.fetch('tar'), '-xOf', archive, '+CONTENTS')
    check(status.success?, "Cannot read runtime manifest: #{error}")
    check(!contents.lines.grep(/^@cwd /).empty? && contents.lines.grep(/^@cwd /).all? { |line| line == "@cwd /usr/pkg\n" }, 'Runtime package prefix mismatch')
    check(contents.lines.grep(/^@name /) == ["@name llvm-23.1.3nb1\n"], 'Runtime package identity mismatch')
    expected = File.readlines(lists.fetch('runtime'), chomp: true).reject { |s| s.empty? || s.start_with?('@comment ') }
    actual = []
    lines = contents.lines.map(&:chomp)
    lines.each_with_index do |name, i|
      next if name.empty? || name.start_with?('@') || lines[i - 1] == '@ignore'
      check(expected.include?(name), "Unexpected runtime file: #{name}")
      actual << name
      item = stage + '/' + name
      comment = lines[i + 1]
      if comment&.start_with?('@comment MD5:')
        check(File.file?(item) && !File.symlink?(item) && Digest::MD5.file(item).hexdigest == comment.delete_prefix('@comment MD5:'),
              "Runtime stage bytes differ: #{name}")
      elsif comment&.start_with?('@comment Symlink:')
        check(File.symlink?(item) && File.readlink(item) == comment.delete_prefix('@comment Symlink:'), "Runtime stage link differs: #{name}")
      else
        raise "Missing runtime digest: #{name}"
      end
    end
    check(actual.sort == expected.sort, 'Incomplete runtime stage comparison')
    machine = target.fetch('arch') == 'aarch64' ? 183 : 62
    tree(stage).each do |name, entry|
      next unless entry.first == 'file'
      header = File.binread(stage + '/' + name, 20)
      if header.start_with?("\x7fELF")
        check(header.bytesize == 20 && header.getbyte(4) == 2 && header.getbyte(5) == 1 && header[18, 2].unpack1('v') == machine,
              "Wrong staged ELF ABI: #{name}")
      else
        check(!MACHO_MAGIC.any? { |m| header.start_with?(m.b) }, "Host Mach-O in stage: #{name}")
      end
    end
  end

  def install_full(value, destdir)
    check(destdir.start_with?('/') && destdir != '/' && File.directory?(destdir) && !File.symlink?(destdir), 'Existing private DESTDIR required')
    check(tree(destdir).empty?, 'SDK DESTDIR must be empty')
    check(![value.fetch('source'), value.fetch('build')].any? { |p| destdir == p || destdir.start_with?(p + '/') || p.start_with?(destdir + '/') }, 'SDK DESTDIR overlaps LLVM inputs')
    command = [value.fetch('cmake'), '--install', value.fetch('build'), '--prefix', '/usr/pkg']
    command << '--strip' if value.fetch('install_strip')
    run({'DESTDIR' => destdir}, *command)
    check(tree(destdir).keys.all? { |p| p.start_with?('usr/pkg/') }, 'Install wrote outside the target prefix')
    destdir + '/usr/pkg'
  end

  def record(config, destdir, output)
    check(!File.exist?(output) && !File.symlink?(output), 'Receipt already exists')
    value = context(config)
    before = snapshot(value)
    stage = install_full(value, destdir)
    validate_full_stage(value, stage)
    stage_files = tree(stage)
    validate_full_stage(value, stage)
    check(tree(stage) == stage_files, 'Reference stage changed during validation')
    check(!stage_files.empty?, 'Empty reference stage')
    check(snapshot(value) == before && context(config) == value, 'Inputs changed while recording the stage')
    receipt = {'schema' => 1, 'context' => value, 'inputs' => before, 'stage' => stage_files}
    File.open(output, File::WRONLY | File::CREAT | File::EXCL, 0o600) { |f| f.write(JSON.pretty_generate(receipt) + "\n") }
  end

  def verify(config, receipt_path, expected_hash)
    check(expected_hash.match?(/\A[0-9a-f]{64}\z/), 'Explicit accepted receipt SHA256 required')
    bytes = File.binread(receipt_path)
    check(Digest::SHA256.hexdigest(bytes) == expected_hash, 'Accepted receipt drift')
    receipt = JSON.parse(bytes)
    check(receipt.fetch('schema') == 1, 'Unsupported LLVM receipt schema')
    value = context(config)
    check(value == receipt.fetch('context'), 'Current compile/ABI/source contract differs from the receipt')
    check(snapshot(value) == receipt.fetch('inputs'), 'LLVM source, patch, compiler, tool or object drift')
    receipt
  end

  def install(config, receipt_path, expected_hash, destdir)
    receipt = verify(config, receipt_path, expected_hash)
    value = receipt.fetch('context')
    stage = install_full(value, destdir)
    # Audit the private result before package partitioning. This catches an
    # A-to-B-to-A shared-object mutation which a final input hash cannot detect.
    check(tree(stage) == receipt.fetch('stage'), 'Installed LLVM stage differs from the accepted full stage')
    verify(config, receipt_path, expected_hash)
    puts 'PASS: accepted LLVM objects produced an exact SDK input stage; package checks remain required.'
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    command = ARGV.shift
    case command
    when 'record'
      raise 'record CONFIG EMPTY_REFERENCE_DESTDIR NEW_RECEIPT' unless ARGV.size == 3
      LLVMStageReuse.record(*ARGV)
    when 'verify'
      raise 'verify CONFIG RECEIPT SHA256' unless ARGV.size == 3
      LLVMStageReuse.verify(*ARGV)
    when 'install'
      raise 'install CONFIG RECEIPT SHA256 EMPTY_DESTDIR' unless ARGV.size == 4
      LLVMStageReuse.install(*ARGV)
    else
      raise 'Use record, verify or install'
    end
  rescue StandardError => e
    warn "FAIL: #{e.message}"
    exit 1
  end
end
