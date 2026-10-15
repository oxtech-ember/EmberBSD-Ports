#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), immutable accepted-Mesa runtime migration.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'rubygems/package'
require 'zlib'

# This is one reviewed package revision transition, not an ABI compatibility claim.
# The accepted LLVM23 ELF inspection records these exact NEEDED/RPATH values.
class MesaRuntimeRebind
  LLVM = '/usr/pkg/lib/libLLVM.so.23.1'.freeze
  POLICY = {
    from: 'llvm-23.1.2', to: 'llvm-23.1.2nb1',
    old_dso: '42231ed6dbaf213a3a391dff50eb51986b0c8fbb8cff8821c42fa07fbc84b1e6',
    package: 'e677db8bb4a579fc697651025ad3cbdcb27345f56a062f64cac88ac3d259397c',
    new_dso: '59486085a768044e0f1940a067f24be4149c420078ae496972bbea303b7b2eb7',
    needed: %w[libedit.so.3 librt.so.1 libexecinfo.so.0 libpthread.so.1 libz.so.1 libzstd.so.1 libxml2.so.16 libstdc++.so.7 libm.so.0 libgcc_s.so.1 libc.so.12],
    rpath: %w[/usr/pkg/gcc16/lib /usr/pkg/lib /usr/pkg/lib/python3.15/config-3.15]
  }.freeze
  SEARCH = %w[/usr/pkg/gcc16/lib /usr/pkg/lib /usr/lib /lib].freeze
  ALLOWED = (SEARCH + %w[/usr/pkg/gcc16/aarch64--netbsd/lib /usr/pkg/lib/python3.15/config-3.15]).freeze

  def fail!(message)
    raise ArgumentError, message
  end

  def sha(path)
    Digest::SHA256.file(path).hexdigest
  end

  def relative!(path)
    fail!("unsafe path: #{path}") unless path.match?(%r{\A[A-Za-z0-9_+.,@%=-]+(?:/[A-Za-z0-9_+.,@%=-]+)*\z}) &&
      path.split('/').none? { |part| %w[. ..].include?(part) }
    path
  end

  def target!(path)
    fail!("unexpected installed path: #{path}") unless path.start_with?('/usr/pkg/')
    relative!(path.delete_prefix('/usr/pkg/'))
    path
  end

  def manifest(path, installed: false)
    result = {}
    File.foreach(path) do |line|
      match = /\A([0-9a-f]{64})  (\S+)\n\z/.match(line)
      fail!("invalid manifest: #{path}") unless match
      name = match[2]
      installed ? target!(name) : relative!(name)
      fail!("duplicate manifest path: #{name}") if result.key?(name)
      result[name] = match[1]
    end
    fail!("empty manifest: #{path}") if result.empty?
    result
  end

  def inventory(root)
    files = Dir.glob("#{root}/**/*", File::FNM_DOTMATCH).reject { |p| %w[. ..].include?(File.basename(p)) }
    files.reject { |p| File.directory?(p) && !File.symlink?(p) }.to_h do |path|
      fail!("nonregular bundle artifact: #{path}") unless File.lstat(path).file?
      name = path.delete_prefix(root + '/')
      relative!(name)
      [name, sha(path)]
    end
  end

  # Reject directory symlinks and escaping leaf links before hashing any target.
  def installed(path, leaf_link: true)
    relative!(path.delete_prefix('/'))
    parts = path.delete_prefix('/').split('/')
    cursor = @sysroot
    parts.each_with_index do |part, index|
      cursor += '/' + part
      fail!("symlink in installed path: #{path}") if File.symlink?(cursor) && (index < parts.length - 1 || !leaf_link)
    end
    real = File.realpath(cursor)
    fail!("installed path escapes sysroot: #{path}") unless real.start_with?(@sysroot + '/')
    fail!("not an installed regular file: #{path}") unless File.file?(real)
    cursor
  end

  def contents!(text, payload)
    directories = text.lines.grep(/^@cwd /)
    fail!('package identity/prefix mismatch') unless text.lines.grep(/^@name /) == ["@name #{@policy.fetch(:to)}\n"] &&
      !directories.empty? && directories.all? { |line| line == "@cwd /usr/pkg\n" }
    names = []
    ignore = false
    text.each_line do |line|
      line = line.chomp
      if ignore
        fail!('unsafe ignored package entry') unless line.match?(/\A\+[A-Z_]+\z/)
        ignore = false
      elsif line == '@ignore'
        ignore = true
      elsif line.start_with?('@')
        fail!('unsupported package directive') unless line.match?(/\A@(cwd|name|blddep|pkgdep|comment) /)
      else
        relative!(line)
        fail!('duplicate +CONTENTS path') if names.include?(line)
        names << line
      end
    end
    fail!('+CONTENTS payload mismatch') if ignore || names.sort != payload.keys.sort
  end

  def package_payload
    payload, contents, seen = {}, nil, {}
    Zlib::GzipReader.open(@package) do |gzip|
      Gem::Package::TarReader.new(gzip) do |tar|
        tar.each do |entry|
          if entry.header.typeflag == 'x'
            # Accept inert pkgsrc timestamp/charset metadata, never path overrides.
            fail!('oversized PAX record') if entry.header.size > 65536
            pax = entry.read
            until pax.empty?
              length = pax[/\A[0-9]+/].to_i
              record = pax.byteslice(0, length)
              fail!('unsupported PAX metadata') unless length > 0 && length <= pax.bytesize &&
                record.match?(/\A[0-9]+ (?:(?:mtime|atime|ctime)=[0-9.-]+|hdrcharset=BINARY)\n\z/)
              pax = pax.byteslice(length..-1)
            end
            next
          end
          name = entry.full_name.sub(%r{\A\./}, '').sub(%r{/\z}, '')
          relative!(name)
          fail!("duplicate archive path: #{name}") if seen[name]
          seen[name] = true
          if name.start_with?('+')
            fail!('invalid package metadata') unless entry.file? && !name.include?('/') && entry.header.size <= 16 * 1024 * 1024
            contents = entry.read if name == '+CONTENTS'
            next
          end
          next if entry.directory?
          path = '/usr/pkg/' + name
          if entry.header.typeflag == '2'
            link = entry.header.linkname
            fail!("unsafe package symlink: #{name}") if link.start_with?('/') || link.match?(/[\s\x00]/)
            resolved = File.expand_path(link, File.dirname(path))
            target!(resolved)
            target = installed(path)
            fail!("package symlink mismatch: #{name}") unless File.symlink?(target) && File.readlink(target) == link
            payload[name] = { 'link' => link, 'resolved' => resolved.delete_prefix('/usr/pkg/') }
          elsif entry.file?
            digest = Digest::SHA256.new
            digest.update(entry.read(65536)) until entry.eof?
            target = installed(path, leaf_link: false)
            fail!("package file mismatch: #{name}") unless sha(target) == digest.hexdigest
            payload[name] = { 'sha256' => digest.hexdigest }
          else
            fail!("unsupported package entry: #{name}")
          end
        end
      end
    end
    fail!('missing +CONTENTS') unless contents
    contents!(contents, payload)
    databases = %w[/usr/pkg/pkgdb /var/db/pkg].map { |base| "#{base}/#{@policy.fetch(:to)}/+CONTENTS" }
    databases.select! { |path| File.exist?(@sysroot + path) || File.symlink?(@sysroot + path) }
    fail!('missing/ambiguous installed LLVM package registration') unless databases.length == 1
    registered = installed(databases.first, leaf_link: false)
    fail!('installed LLVM +CONTENTS mismatch') unless File.binread(registered) == contents
    # Every package link must terminate in another verified package payload file.
    payload.each do |name, record|
      visited = [name]
      value = record
      while value['link']
        next_name = value.fetch('resolved')
        fail!("unowned/cyclic package link: #{name}") if visited.include?(next_name) || !payload.key?(next_name)
        visited << next_name
        value = payload.fetch(next_name)
      end
      record['sha256'] = value.fetch('sha256')
    end
    [payload, contents]
  end

  def dynamic(path)
    header = File.binread(path, 20)
    fail!("not an AArch64 ELF64 provider: #{path}") unless header.length >= 20 && header.byteslice(0, 6) == "\x7fELF\x02\x01" &&
      [2, 3].include?(header.byteslice(16, 2).unpack1('v')) && header.byteslice(18, 2).unpack1('v') == 183
    out, err, status = Open3.capture3(@readelf, '-d', path)
    fail!("readelf failed: #{err}") unless status.success?
    needed = out.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten
    fail!('invalid NEEDED name') unless needed.all? { |name| name.match?(/\Alib[A-Za-z0-9_.+-]+\z/) }
    paths = out.scan(/\((?:RUNPATH|RPATH)\).*\[([^\]]+)\]/).flatten.flat_map { |p| p.split(':', -1) }
    fail!('relative/traversing ELF search path') unless paths.all? { |p| p.start_with?('/') && !p.split('/').include?('..') }
    paths.map! { |p| File.expand_path(p) }
    fail!("unsupported ELF search path: #{path}: #{paths.join(':')}") unless paths.all? { |p| ALLOWED.include?(p) }
    { 'needed' => needed, 'rpath' => paths, 'soname' => out.scan(/\(SONAME\).*\[([^\]]+)\]/).flatten }
  end

  def closure(runtime)
    queue, checked = [LLVM], {}
    until queue.empty?
      path = queue.shift
      next if checked.key?(path)
      file = installed(path)
      real = File.realpath(file).delete_prefix(@sysroot)
      if path.start_with?('/usr/pkg/')
        [path, real].each do |name|
          fail!("expanded package dependency closure: #{name}") unless runtime[name] == sha(@sysroot + name)
        end
      else
        fail!('foreign base provider') unless [path, real].all? { |p| p.start_with?('/usr/lib/', '/lib/') }
      end
      info = dynamic(file)
      if path == LLVM
        fail!('LLVM NEEDED changed') unless info['needed'].sort == @policy.fetch(:needed).sort
        fail!('LLVM SONAME/RPATH changed') unless info['soname'] == ['libLLVM.so.23.1'] && info['rpath'] == @policy.fetch(:rpath)
      end
      checked[path] = info.merge('sha256' => sha(file), 'realpath' => real)
      info['needed'].each do |name|
        found = (info['rpath'] + SEARCH).uniq.map { |dir| dir + '/' + name }.find { |p| File.exist?(@sysroot + p) || File.symlink?(@sysroot + p) }
        fail!("unresolved dependency: #{name}") unless found
        queue << found
      end
    end
    checked
  end

  def run(bundle, package, sysroot, readelf, work, policy: POLICY)
    @bundle, @package, @sysroot, @readelf = [bundle, package, sysroot, readelf].map { |p| File.realpath(p) }
    @policy = policy
    fail!('readelf is not executable') unless File.executable?(@readelf)
    fail!('NEW_WORK must be absolute') unless work.start_with?('/')
    work = File.expand_path(work)
    fail!('NEW_WORK must be a new absolute path') if File.exist?(work) || File.symlink?(work)
    fail!('NEW_WORK parent must be canonical') unless File.realpath(File.dirname(work)) == File.dirname(work)
    fail!('NEW_WORK overlaps an input') if [@bundle, @sysroot, @package, @readelf].any? { |p| work == p || work.start_with?(p + '/') || p.start_with?(work + '/') }
    before = inventory(@bundle)
    expected = manifest(@bundle + '/artifacts.sha256')
    fail!('bundle inventory/hash mismatch') unless before.reject { |name, _| name == 'artifacts.sha256' } == expected
    fail!('runner differs from canonical verifier') unless sha(@bundle + '/run-mesa-package-tests.sh') == sha(File.join(__dir__, 'run-mesa-package-tests.sh'))
    runtime = manifest(@bundle + '/runtime-libraries.sha256', installed: true)
    fail!('unsupported old LLVM runtime') unless runtime[LLVM] == policy.fetch(:old_dso)
    fail!('unsupported LLVM package hash') unless sha(@package) == policy.fetch(:package)
    tool_sha = sha(@readelf)
    payload, contents = package_payload
    fail!('unsupported new LLVM DSO') unless payload.fetch(LLVM.delete_prefix('/usr/pkg/'), {})['sha256'] == policy.fetch(:new_dso)
    updated, changed = runtime.dup, []
    mesa = manifest(@bundle + '/mesa-package-files.sha256', installed: true)
    runtime.each do |path, old_hash|
      owned = payload[path.delete_prefix('/usr/pkg/')]
      if owned
        fail!('package overlaps Mesa payload') if mesa.key?(path)
        updated[path] = owned.fetch('sha256')
        changed << path if old_hash != updated[path]
      else
        fail!("unchanged runtime drift: #{path}") unless sha(installed(path)) == old_hash
      end
    end
    fail!('LLVM DSO did not change') unless changed.include?(LLVM)
    dependencies = closure(updated)
    # Perform all input checks before publishing a new bundle. No source links are edited.
    fail!('input changed during verification') unless before == inventory(@bundle) && sha(@package) == policy.fetch(:package) && sha(@readelf) == tool_sha
    Dir.mkdir(work)
    destination = work + '/candidate'
    FileUtils.cp_r(@bundle, destination)
    File.write(destination + '/runtime-libraries.sha256', updated.sort.map { |path, hash| "#{hash}  #{path}\n" }.join)
    receipt_dir = destination + '/runtime-rebind'
    fail!('bundle was already rebound') if File.exist?(receipt_dir)
    Dir.mkdir(receipt_dir)
    FileUtils.cp(@bundle + '/runtime-libraries.sha256', receipt_dir + '/original-runtime-libraries.sha256')
    FileUtils.cp(@bundle + '/artifacts.sha256', receipt_dir + '/original-artifacts.sha256')
    File.write(work + '/llvm.CONTENTS', contents)
    File.write(work + '/llvm-payload.json', JSON.pretty_generate(payload) + "\n")
    File.write(work + '/dependency-closure.json', JSON.pretty_generate(dependencies) + "\n")
    receipt = { transition: [policy.fetch(:from), policy.fetch(:to)], package_sha256: policy.fetch(:package),
      original_artifacts_sha256: before.fetch('artifacts.sha256'), old_dso_sha256: policy.fetch(:old_dso),
      new_dso_sha256: policy.fetch(:new_dso), changed_runtime_paths: changed.sort,
      full_payload_sha256: sha(work + '/llvm-payload.json'), contents_sha256: sha(work + '/llvm.CONTENTS'),
      closure_sha256: sha(work + '/dependency-closure.json'), readelf_sha256: tool_sha, helper_sha256: sha(__FILE__),
      scope: 'Filesystem and ELF dependency verification only; target runtime acceptance is still required.' }
    File.write(receipt_dir + '/receipt.json', JSON.pretty_generate(receipt) + "\n")
    artifacts = inventory(destination).reject { |name, _| name == 'artifacts.sha256' }
    File.write(destination + '/artifacts.sha256', artifacts.sort.map { |path, hash| "#{hash}  #{path}\n" }.join)
    out, err, status = Open3.capture3('sh', destination + '/run-mesa-package-tests.sh', '--verify-sysroot', destination, @sysroot)
    File.write(work + '/verify-sysroot.log', out + err)
    fail!('final canonical sysroot verification failed') unless status.success?
    fail!('accepted bundle changed') unless before == inventory(@bundle)
    File.rename(destination, work + '/bundle')
    destination = work + '/bundle'
    puts "PASS: rebound #{changed.length} provider paths; #{payload.length} full-package files/links verified"
    puts "#{sha(destination + '/artifacts.sha256')}  #{destination}/artifacts.sha256"
    destination
  end
end

if $PROGRAM_NAME == __FILE__
  abort 'usage: rebind-mesa-runtime.rb ACCEPTED_BUNDLE LLVM_PACKAGE SYSROOT READELF NEW_WORK' unless ARGV.length == 5
  begin
    MesaRuntimeRebind.new.run(*ARGV)
  rescue ArgumentError, KeyError, SystemCallError, Zlib::Error, Gem::Package::TarInvalidError => error
    abort error.message
  end
end
