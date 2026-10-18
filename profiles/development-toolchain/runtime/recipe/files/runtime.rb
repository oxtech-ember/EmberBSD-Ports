#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD; AI-assisted host packaging of audited target GCC16 libraries.
require 'digest'
require 'date'
require 'fileutils'
require 'find'
require 'json'
require 'open3'
require 'pathname'
require 'tmpdir'

module GCC16Runtime
  VERSION = '16.2.0'
  NAME = 'gcc16-runtime-16.2.0nb2'
  SOURCE_SHA256 = 'e6738e29597f733270731aa90600f37ffdc045079dfc27ec7e8192cc81085c3e'
  LICENSES = %w[COPYING3 COPYING.RUNTIME].freeze
  CONFLICTS = %w[gcc16-[0-9]* gcc16-libs-[0-9]*].freeze
  LIBRARIES = {
    'libgcc' => 'libgcc_s.so.1', 'libstdc++' => 'libstdc++.so.7',
    'libgomp' => 'libgomp.so.1', 'libatomic' => 'libatomic.so.3'
  }.freeze
  SELECTIONS = %w[libgcc,libstdc++ libgcc,libstdc++,libgomp libgcc,libstdc++,libatomic libgcc,libstdc++,libgomp,libatomic].freeze
  TARGETS = {
    'amd64' => { triplet: 'x86_64--netbsd', machine_arch: 'x86_64', elf_machine: 62 }.freeze,
    'aarch64' => { triplet: 'aarch64--netbsd', machine_arch: 'aarch64', elf_machine: 183 }.freeze
  }.freeze
  class Invalid < StandardError; end

  # Inspect ELF bytes on the build host. Never execute target code.
  class ELF
    def initialize(path)
      @data = File.binread(path)
    end

    def slice(offset, length)
      raise Invalid, 'Truncated ELF' unless offset >= 0 && length >= 0 && offset + length <= @data.bytesize
      @data.byteslice(offset, length)
    end

    def verify(soname, target, runtime_sonames)
      raise Invalid, "Expected ELF64 little-endian #{target.fetch(:machine_arch)} DSO" unless slice(0, 7) == "\x7fELF\x02\x01\x01".b && slice(16, 4).unpack('vv') == [3, target.fetch(:elf_machine)]
      offset = slice(32, 8).unpack1('Q<')
      size, count = slice(54, 4).unpack('vv')
      raise Invalid, 'Invalid ELF program headers' unless size == 56 && count.positive?
      headers = count.times.map { |i| slice(offset + i * size, size).unpack('VVQ<Q<Q<Q<Q<Q<') }
      dynamic = headers.select { |h| h[0] == 2 }
      raise Invalid, 'Expected one ELF dynamic table' unless dynamic.length == 1
      dyn = dynamic.first
      raise Invalid, 'Invalid dynamic table size' unless dyn[5].positive? && dyn[5] % 16 == 0
      entries = slice(dyn[2], dyn[5]).unpack('Q<*').each_slice(2).take_while { |tag, _| tag != 0 }
      values = ->(tag) { entries.select { |t, _| t == tag }.map(&:last) }
      address = values.call(5); lengths = values.call(10)
      raise Invalid, 'Missing ELF string table' unless address.length == 1 && lengths.length == 1
      load = headers.find { |h| h[0] == 1 && address[0] >= h[3] && address[0] + lengths[0] <= h[3] + h[5] }
      raise Invalid, 'ELF string table is not file-backed' unless load
      strings = slice(load[2] + address[0] - load[3], lengths[0])
      string = lambda do |index|
        last = strings.index("\0", index) if index < strings.bytesize
        raise Invalid, 'Invalid ELF string offset' unless last
        strings.byteslice(index, last - index)
      end
      actual = values.call(14).map { |index| string.call(index) }
      raise Invalid, "Runtime SONAME mismatch: #{actual.inspect}" unless actual == [soname]
      needed = values.call(1).map { |index| string.call(index) }
      allowed = %w[libc.so.12 libm.so.0 libpthread.so.1] + runtime_sonames
      raise Invalid, "Foreign runtime dependency: #{needed.inspect}" unless (needed - allowed).empty?
      [15, 29].each do |tag|
        values.call(tag).each do |index|
          paths = string.call(index).split(':', -1)
          raise Invalid, 'Unsafe runtime library path' unless (paths - %w[/usr/pkg/gcc16/lib /usr/lib /lib]).empty?
        end
      end
      { 'soname' => soname, 'needed' => needed, 'machine' => target.fetch(:machine_arch) }
    end
  end

  class Stage
    def initialize(work, pkgsrc, archive, expected_source: SOURCE_SHA256)
      @work = File.realpath(work)
      @pkgsrc = File.expand_path(pkgsrc)
      raise Invalid, 'Missing pkgsrc tree' unless File.directory?(@pkgsrc)
      @archive = File.expand_path(archive)
      @stage = File.join(@work, 'stage')
      @expected_source = expected_source
    rescue SystemCallError => e
      raise Invalid, e.message
    end

    def hash(path)
      Digest::SHA256.file(path).hexdigest
    end

    def relative(path)
      raise Invalid, "Unsafe stage path: #{path}" unless path.start_with?('./usr/pkg/gcc16/') && !path.split('/').include?('..') && path.match?(/\A[A-Za-z0-9_+.\/-]+\z/)
      path.delete_prefix('./')
    end

    def verify
      raise Invalid, 'No completed runtime stage' unless File.read(@work + '/build-success') == "runtime-only-bootstrap\n"
      inputs = File.read(@work + '/inputs.txt')
      claims = %w[scope target triplet].to_h do |key|
        lines = inputs.lines.select { |line| line.start_with?(key + '=') }
        raise Invalid, "Missing or duplicate provenance: #{key}" unless lines.length == 1 && lines[0].end_with?("\n")
        [key, lines[0].delete_prefix(key + '=').delete_suffix("\n")]
      end
      raise Invalid, 'Expected runtime-only bootstrap scope' unless claims.fetch('scope') == 'runtime-only-bootstrap'
      architecture = TARGETS[claims.fetch('target')]
      raise Invalid, 'Unsupported runtime target' unless architecture
      raise Invalid, 'Runtime target/triplet mismatch' unless claims.fetch('triplet') == architecture.fetch(:triplet)
      choices = inputs.lines.select { |line| line.start_with?('runtime_libraries=') }
      raise Invalid, 'Duplicate runtime library selection' unless choices.length <= 1
      raise Invalid, 'Unterminated runtime library selection' unless choices.empty? || choices.first.end_with?("\n")
      # Legacy completed stages contain only the original libgcc/libstdc++ pair.
      selection = choices.empty? ? SELECTIONS.first : choices.first.delete_prefix('runtime_libraries=').delete_suffix("\n")
      raise Invalid, 'Unsupported runtime library selection' unless SELECTIONS.include?(selection)
      runtime_sonames = selection.split(',').map { |name| LIBRARIES.fetch(name) }
      seed = inputs.lines.grep(/^seed_source=/)
      raise Invalid, 'Missing seed source commit' unless seed.length == 1 && seed[0].match?(/\Aseed_source=[0-9a-f]{40}\n\z/)
      raise Invalid, 'GCC source archive mismatch' unless hash(@archive) == @expected_source
      recipe = @pkgsrc + '/lang/gcc16'
      recipe_files = %w[distinfo Makefile Makefile.common].map { |f| recipe + '/' + f } + Dir.glob(recipe + '/patches/*').select { |f| File.file?(f) }
      [@archive, *recipe_files].each do |path|
        matches = inputs.lines.filter_map { |l| m = l.match(/\A([0-9a-f]{64})  (.+)\n?\z/); m[1] if m && m[2].chomp == path }
        raise Invalid, "Source/recipe receipt mismatch: #{path}" unless matches == [hash(path)]
      end
      regular = {}; links = {}
      File.foreach(@work + '/stage.sha256') do |line|
        match = line.match(/\A([0-9a-f]{64})  (.+)\n\z/)
        raise Invalid, 'Invalid stage hash manifest' unless match
        path = relative(match[2])
        raise Invalid, 'Duplicate stage path' if regular.key?(path)
        regular[path] = match[1]
      end
      File.foreach(@work + '/stage.symlinks') do |line|
        path, target = line.chomp.split("\t", -1)
        path = relative(path.to_s)
        raise Invalid, 'Invalid or duplicate symlink' unless target && !target.empty? && !links.key?(path)
        links[path] = target
      end
      actual_regular = []; actual_links = []
      Find.find(@stage) do |path|
        next if path == @stage
        rel = path.delete_prefix(@stage + '/')
        if File.symlink?(path)
          actual_links << rel
          target = File.readlink(path)
          raise Invalid, 'Stage symlink changed or is absolute' unless links[rel] == target && !target.start_with?('/')
          resolved = File.realpath(path)
          raise Invalid, 'Stage symlink escapes runtime prefix' unless resolved.start_with?(@stage + '/usr/pkg/gcc16/')
        elsif File.file?(path)
          actual_regular << rel
          raise Invalid, "Stage file hash mismatch: #{rel}" unless regular[rel] == hash(path)
        elsif !File.directory?(path)
          raise Invalid, 'Special file in stage'
        end
      end
      raise Invalid, 'Stage inventory mismatch' unless actual_regular.sort == regular.keys.sort && actual_links.sort == links.keys.sort
      (regular.keys + links.keys).grep(%r{\Ausr/pkg/gcc16/lib/(?:libgcc_s|libstdc\+\+|libgomp|libatomic)\.so\.[0-9]+(?:\.[0-9]+)*\z}).each do |path|
        raise Invalid, "Unselected or foreign runtime ABI in stage: #{path}" unless runtime_sonames.any? { |name| File.basename(path).match?(/\A#{Regexp.escape(name)}(?:\.[0-9]+)*\z/) }
      end
      selected = (regular.keys + links.keys).select do |path|
        runtime_sonames.any? { |name| path.match?(%r{\Ausr/pkg/gcc16/lib/#{Regexp.escape(name)}(?:\.[0-9]+)*\z}) }
      end.sort
      required = runtime_sonames.map { |name| 'usr/pkg/gcc16/lib/' + name }
      raise Invalid, 'Required runtime DSOs missing' unless (required - selected).empty?
      elf = {}
      selected.each do |path|
        source = @stage + '/' + path
        if File.symlink?(source)
          immediate = File.expand_path(File.readlink(source), File.dirname(source)).delete_prefix(@stage + '/')
          raise Invalid, 'Runtime alias requires an unshipped intermediate link' unless selected.include?(immediate)
        end
        resolved = File.realpath(source)
        resolved_rel = resolved.delete_prefix(@stage + '/')
        raise Invalid, 'Runtime alias points outside the selected payload' unless selected.include?(resolved_rel)
        soname = runtime_sonames.find { |name| File.basename(path).match?(/\A#{Regexp.escape(name)}(?:\.[0-9]+)*\z/) }
        elf[path.delete_prefix('usr/pkg/')] = ELF.new(resolved).verify(soname, architecture, runtime_sonames)
      end
      recipe_digest = Digest::SHA256.hexdigest(recipe_files.sort.map { |p| "#{p.delete_prefix(recipe + "/")} #{hash(p)}\n" }.join)
      @result = {
        files: selected.map { |p| p.delete_prefix('usr/pkg/') },
        metadata: { 'OPSYS' => 'NetBSD', 'OS_VERSION' => '11.0', 'MACHINE_ARCH' => architecture.fetch(:machine_arch),
          'PKGPATH' => 'lang/gcc16-runtime', 'PKGNAME' => NAME, 'LICENSE' => 'gnu-gpl-v3',
          'GCC_VERSION' => VERSION, 'GCC_RUNTIME_SONAME' => 'libstdc++.so.7',
          'GCC_RUNTIME_LIBRARIES' => selection, 'GCC_RUNTIME_SONAMES' => runtime_sonames.join(','),
          'GCC_RUNTIME_TARGET' => claims.fetch('target'), 'GCC_RUNTIME_TRIPLET' => architecture.fetch(:triplet),
          'GCC_RUNTIME_MACHINE_ARCH' => architecture.fetch(:machine_arch),
          'GCC_SOURCE_SHA256' => @expected_source, 'GCC_RECIPE_SHA256' => recipe_digest, 'GCC_RECIPE_DISTINFO_SHA256' => hash(recipe + '/distinfo'),
          'GCC_RUNTIME_INPUTS_SHA256' => hash(@work + '/inputs.txt'), 'GCC_RUNTIME_STAGE_SHA256' => hash(@work + '/stage.sha256'),
          'GCC_RUNTIME_LINKS_SHA256' => hash(@work + '/stage.symlinks'), 'EMBERBSD_SEED_SOURCE' => seed[0].strip.split('=', 2)[1] },
        elf: elf
      }
    rescue SystemCallError => e
      raise Invalid, e.message
    end

    def install(destination)
      result = verify
      prefix = File.join(destination, 'usr/pkg')
      result.fetch(:files).each do |path|
        source = @stage + '/usr/pkg/' + path
        target = prefix + '/' + path
        raise Invalid, "Refusing existing payload: #{target}" if File.exist?(target) || File.symlink?(target)
        FileUtils.mkdir_p(File.dirname(target))
        if File.symlink?(source)
          File.symlink(File.readlink(source), target)
        else
          FileUtils.copy_file(source, target)
          File.chmod(0755, target)
          raise Invalid, 'Runtime changed while copying' unless hash(target) == hash(source)
        end
      end
      LICENSES.each do |name|
        contents, err, status = Open3.capture3('tar', '-xOf', @archive, "gcc-#{VERSION}/#{name}")
        raise Invalid, "Cannot read GCC license #{name}: #{err}" unless status.success? && !contents.empty?
        path = prefix + '/share/licenses/gcc16-runtime/' + name
        FileUtils.mkdir_p(File.dirname(path))
        raise Invalid, 'Refusing existing license' if File.exist?(path) || File.symlink?(path)
        File.write(path, contents)
        File.chmod(0644, path)
      end
      raise Invalid, 'Source archive changed during license extraction' unless hash(@archive) == @expected_source
      raise Invalid, 'Stage changed during packaging' unless verify == result
      result
    end
  end

  def self.plist(result)
    (["@name #{NAME}", *CONFLICTS.map { |p| "@pkgcfl #{p}" }, *result.fetch(:files),
      *LICENSES.map { |f| "share/licenses/gcc16-runtime/#{f}" }].join("\n") + "\n")
  end

  # pkg_create -V reports the pkgtools date, not the pkgsrc package revision.
  def self.validate_pkgtools_version(version)
    valid = version.is_a?(String) && version.match?(/\A[1-9][0-9]{7}\z/) &&
      Date.valid_date?(version[0, 4].to_i, version[4, 2].to_i, version[6, 2].to_i)
    raise Invalid, 'Invalid native pkgtools version' unless valid
    version
  end

  def self.native_pkgtools(pkg_create)
    digest = Digest::SHA256.file(pkg_create).hexdigest
    out, err, status = Open3.capture3(pkg_create, '-V')
    raise Invalid, "Cannot query native pkg_create version: #{err}" unless status.success? && err.empty? && out.match?(/\A[0-9]{8}\n\z/)
    version = validate_pkgtools_version(out.chomp)
    raise Invalid, 'Native pkg_create changed during version query' unless Digest::SHA256.file(pkg_create).hexdigest == digest
    { 'PKGTOOLS_VERSION' => version, 'EMBERBSD_PKG_CREATE_SHA256' => digest }
  rescue SystemCallError => error
    raise Invalid, error.message
  end

def self.audit_package(package, payload, result)
  expected_metadata = result.fetch(:metadata)
  validate_pkgtools_version(expected_metadata['PKGTOOLS_VERSION'])
  raise Invalid, 'Missing native pkg_create digest' unless expected_metadata['EMBERBSD_PKG_CREATE_SHA256'].is_a?(String) && expected_metadata['EMBERBSD_PKG_CREATE_SHA256'].match?(/\A[0-9a-f]{64}\z/)
  listing, error, status = Open3.capture3('tar', '-tf', package)
  raise Invalid, "Cannot list runtime package: #{error}" unless status.success?
  names = listing.lines.map(&:chomp)
  files = result.fetch(:files) + LICENSES.map { |f| "share/licenses/gcc16-runtime/#{f}" }
  allowed_meta = %w[+CONTENTS +COMMENT +DESC +BUILD_INFO +BUILD_VERSION +SIZE_PKG +SIZE_ALL]
  raise Invalid, 'Unexpected runtime package payload' unless names.uniq == names && (names - allowed_meta).sort == files.sort
  Dir.mktmpdir('gcc16-runtime-audit-') do |d|
    _, error, status = Open3.capture3('tar', '-xf', package, '-C', d)
    raise Invalid, "Cannot inspect runtime package: #{error}" unless status.success?
    files.each do |path|
      expected = payload + '/' + path
      actual = d + '/' + path
      if File.symlink?(expected)
        raise Invalid, 'Package symlink changed' unless File.symlink?(actual) && File.readlink(actual) == File.readlink(expected)
      else
        raise Invalid, 'Package bytes changed' unless !File.symlink?(actual) && File.file?(actual) && Digest::SHA256.file(actual).hexdigest == Digest::SHA256.file(expected).hexdigest
      end
    end
    metadata = File.read(d + '/+BUILD_INFO').lines.map(&:chomp)
    raise Invalid, 'Target package metadata changed or duplicated' unless expected_metadata.all? { |k, v| metadata.grep(/^#{Regexp.escape(k)}=/) == ["#{k}=#{v}"] }
    contents = File.read(d + '/+CONTENTS').lines.map(&:chomp)
    raise Invalid, 'Missing runtime conflicts' unless CONFLICTS.all? { |p| contents.include?("@pkgcfl #{p}") }
    raise Invalid, 'Wrong installed prefix' unless contents.include?('@cwd /usr/pkg')
  end
end

  def self.create(stage, pkg_create, output)
    raise Invalid, 'Use an absolute native pkg_create path' unless pkg_create.start_with?('/') && File.executable?(pkg_create)
    raise Invalid, 'Output must be a new absolute directory' unless output.start_with?('/') && !File.exist?(output) && !File.symlink?(output)
    packaging = native_pkgtools(pkg_create)
    FileUtils.mkdir(output)
    begin
      Dir.mktmpdir('gcc16-runtime-package-') do |tmp|
        stage_result = stage.install(tmp + '/payload')
        result = stage_result.merge(metadata: stage_result.fetch(:metadata).merge(packaging))
        File.write(tmp + '/PLIST', plist(result))
        File.write(tmp + '/BUILD_INFO', result.fetch(:metadata).map { |k, v| "#{k}=#{v}" }.join("\n") + "\n")
        File.write(tmp + '/COMMENT', "GCC16 target runtime libraries for EmberBSD\n")
        File.write(tmp + '/DESCR', "GCC 16.2 target shared libraries with the GCC Runtime Library Exception.\nNo compiler, headers, CRT objects or static libraries are installed.\n")
        package = output + '/' + NAME + '.tgz'
        out, err, status = Open3.capture3(pkg_create, '-u', 'root', '-g', 'wheel', '-p', tmp + '/payload/usr/pkg', '-I', '/usr/pkg',
          '-B', tmp + '/BUILD_INFO', '-c', tmp + '/COMMENT', '-d', tmp + '/DESCR', '-f', tmp + '/PLIST', package)
        raise Invalid, "pkg_create failed: #{out}#{err}" unless status.success? && File.file?(package)
        audit_package(package, tmp + '/payload/usr/pkg', result)
        raise Invalid, 'Native pkg_create changed while creating package' unless Digest::SHA256.file(pkg_create).hexdigest == packaging.fetch('EMBERBSD_PKG_CREATE_SHA256')
        raise Invalid, 'Stage changed while creating package' unless stage.verify == stage_result
        File.write(output + '/package.sha256', "#{Digest::SHA256.file(package).hexdigest}  #{NAME}.tgz\n")
        File.write(output + '/provenance.json', JSON.pretty_generate(result) + "\n")
      end
    rescue StandardError
      FileUtils.remove_entry(output)
      raise
    end
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    mode = ARGV.shift
    raise GCC16Runtime::Invalid, 'Usage: runtime.rb check|plist WORK ARCHIVE PKGSRC; install WORK ARCHIVE PKGSRC DESTDIR; create WORK ARCHIVE PKGSRC PKG_CREATE NEW_OUTPUT' unless %w[check fields plist install create].include?(mode)
    expected = { 'check' => 3, 'fields' => 3, 'plist' => 3, 'install' => 4, 'create' => 5 }.fetch(mode)
    raise GCC16Runtime::Invalid, 'Wrong argument count' unless ARGV.length == expected
    work, archive, pkgsrc, *rest = ARGV
    stage = GCC16Runtime::Stage.new(work, pkgsrc, archive)
    case mode
    when 'check' then puts JSON.pretty_generate(stage.verify)
    when 'fields' then stage.verify.fetch(:metadata).each { |k, v| puts "#{k}=#{v}" if k.start_with?('GCC_') || k == 'EMBERBSD_SEED_SOURCE' }
    when 'plist' then puts GCC16Runtime.plist(stage.verify).lines.reject { |line| line.start_with?('@') }.join
    when 'install' then stage.install(rest[0])
    when 'create' then GCC16Runtime.create(stage, *rest)
    end
  rescue GCC16Runtime::Invalid => e
    warn "gcc16-runtime: #{e.message}"
    exit 1
  end
end
