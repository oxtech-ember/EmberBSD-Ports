#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Read-only audit of the actual installer bootstrap ELF closure.
require 'digest'
require 'json'
require 'open3'

module InstallerBootstrap
  ROOTS = %w[/bin/sh /bin/tar /usr/bin/tar /usr/bin/sha512 /usr/bin/cmp /usr/bin/id /usr/sbin/pkg_add /usr/sbin/pkg_info].freeze
  BASE = %w[/bin/ /sbin/ /usr/bin/ /usr/sbin/ /lib/ /libexec/ /usr/lib/ /usr/libexec/].freeze
  class Invalid < StandardError; end
  def self.check(value, message)
    raise Invalid, message unless value
  end

  class Audit
    def initialize(destdir, readelf)
      @root = File.realpath(destdir)
      @readelf = File.realpath(readelf)
      InstallerBootstrap.check(readelf.start_with?('/') && File.executable?(@readelf), 'Use an absolute host cross-readelf path')
      @files = {}; @links = {}
      @hints = []
    end

    def loader_hints
      config = @root + '/etc/ld.so.conf'
      return nil unless File.exist?(config) || File.symlink?(config)
      InstallerBootstrap.check(!File.symlink?(@root + '/etc') && File.file?(config) && !File.symlink?(config), 'Loader hints must be a regular DESTDIR file')
      contents = File.read(config)
      @hints = contents.lines.filter_map do |line|
        path = line.split('#', 2).first.to_s.strip
        next if path.empty?
        InstallerBootstrap.check(path.start_with?('/'), 'Loader hint mappings are unsupported for the bootstrap gate')
        base(File.expand_path(path) + '/')
      end
      Digest::SHA256.hexdigest(contents)
    end

    def base(path)
      InstallerBootstrap.check(path.match?(%r{\A/[A-Za-z0-9_./+\-]+\z}) && BASE.any? { |p| path.start_with?(p) } && !path.split('/').include?('..'), "Non-base dependency path: #{path}")
      path
    end

    # Resolve absolute target links inside DESTDIR, never against the build host root.
    def resolve(path)
      path = base(path)
      40.times do
        components = path.split('/').reject(&:empty?)
        expanded = false
        components.each_index do |i|
          prefix = '/' + components.take(i + 1).join('/')
          file = @root + prefix
          InstallerBootstrap.check(File.exist?(file) || File.symlink?(file), "Missing bootstrap dependency: #{prefix}")
          next unless File.symlink?(file)
          target = File.readlink(file)
          @links[prefix] = target
          path = base(File.expand_path(([target] + components.drop(i + 1)).join('/'), File.dirname(prefix)))
          expanded = true
          break
        end
        return path unless expanded
      end
      raise Invalid, "Bootstrap symlink cycle: #{path}"
    end

    def inspect_elf(path)
      file = @root + path
      InstallerBootstrap.check(File.file?(file) && !File.symlink?(file), "Not a regular ELF file: #{path}")
      before = Digest::SHA256.file(file).hexdigest
      out, err, status = Open3.capture3({ 'LC_ALL' => 'C' }, @readelf, '-hW', '-lW', '-dW', file)
      InstallerBootstrap.check(status.success? && err.empty?, "Cannot read bootstrap ELF #{path}: #{err}")
      InstallerBootstrap.check(out.match?(/^\s*Class:\s+ELF64\s*$/) && out.match?(/^\s*Data:\s+2's complement, little endian\s*$/) && out.match?(/^\s*Machine:\s+Advanced Micro Devices X86-64\s*$/) && out.match?(/^\s*Type:\s+(EXEC|DYN)\b/) && out.match?(/^\s*LOAD\s/), "Foreign or non-loadable bootstrap ELF: #{path}")
      needed = out.scan(/\(NEEDED\).*?\[([^\]]+)\]/).flatten
      sonames = out.scan(/\(SONAME\).*?\[([^\]]+)\]/).flatten
      InstallerBootstrap.check((needed + sonames).all? { |n| n.match?(/\A[A-Za-z0-9_.+\-]+\z/) && !n.start_with?('libstdc++.so') }, "Forbidden bootstrap shared runtime: #{path}: #{(needed + sonames).inspect}")
      search_tags = out.scan(/\((?:RPATH|RUNPATH)\).*?\[([^\]]*)\]/).flatten
      InstallerBootstrap.check(search_tags.length <= 1, "Ambiguous bootstrap library path tags: #{path}")
      paths = search_tags.flat_map { |s| s.split(':', -1) }
      directories = paths.map do |p|
        expanded = p.gsub('${ORIGIN}', File.dirname(path)).gsub('$ORIGIN', File.dirname(path))
        InstallerBootstrap.check(expanded.start_with?('/') && !expanded.include?('$'), "Unsafe bootstrap library path: #{p}")
        base(File.expand_path(expanded) + '/')
      end
      interpreters = out.scan(/\[Requesting program interpreter: ([^\]]+)\]/).flatten
      InstallerBootstrap.check(interpreters.length <= 1, "Ambiguous bootstrap interpreter: #{path}")
      dependencies = needed.to_h do |name|
        # NetBSD rtld searches global hints, the referring object's paths, then base defaults.
        candidates = (@hints + directories + %w[/lib/ /usr/lib/]).uniq.map { |dir| dir + name }
        candidate = candidates.find { |p| File.exist?(@root + p) || File.symlink?(@root + p) }
        InstallerBootstrap.check(candidate, "Unresolved bootstrap dependency: #{path}: #{name}")
        [name, resolve(candidate)]
      end
      interpreters.each { |p| dependencies['PT_INTERP'] = resolve(p) }
      InstallerBootstrap.check(Digest::SHA256.file(file).hexdigest == before, "Bootstrap ELF changed while reading: #{path}")
      { 'sha256' => before, 'bytes' => File.size(file), 'needed' => dependencies }
    end

    def run
      config_hash = loader_hints
      pending = ROOTS.map do |path|
        resolved = resolve(path)
        InstallerBootstrap.check((File.stat(@root + resolved).mode & 0111).positive?, "Bootstrap program is not executable: #{path}")
        resolved
      end
      until pending.empty?
        path = pending.shift
        next if @files.key?(path)
        @files[path] = inspect_elf(path)
        pending.concat(@files[path].fetch('needed').values)
      end
      @links.each { |p, target| InstallerBootstrap.check(File.symlink?(@root + p) && File.readlink(@root + p) == target, "Bootstrap link changed: #{p}") }
      @files.each { |p, result| InstallerBootstrap.check(Digest::SHA256.file(@root + p).hexdigest == result.fetch('sha256'), "Bootstrap file changed: #{p}") }
      InstallerBootstrap.check(loader_hints == config_hash, 'Bootstrap loader hints changed during inspection')
      { 'format' => 'emberbsd-installer-bootstrap-v1', 'target' => 'amd64', 'destdir' => @root, 'roots' => ROOTS,
        'readelf_sha256' => Digest::SHA256.file(@readelf).hexdigest, 'files' => @files, 'symlinks' => @links,
        'ld_so_conf_sha256' => config_hash,
        'validation' => 'Actual ELF64 x86_64 PT_INTERP and recursive DT_NEEDED closure inside base DESTDIR; no target execution' }
    end
  end
end

if $PROGRAM_NAME == __FILE__
  begin
    InstallerBootstrap.check(ARGV.length == 2, 'Usage: audit-bootstrap.rb DESTDIR ABSOLUTE_CROSS_READELF')
    puts JSON.pretty_generate(InstallerBootstrap::Audit.new(*ARGV).run)
  rescue StandardError => e
    warn "FAIL: #{e.message}"
    exit 1
  end
end
