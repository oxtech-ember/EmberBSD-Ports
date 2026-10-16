#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run GdkPixbuf build tools with target modules.
# Shares the validated GI runner contract; the only added modes are loader and MIME queries.
require 'json'
require 'open3'
require 'fileutils'
require 'digest'
require 'shellwords'
require 'tmpdir'

config = JSON.parse(File.read(ENV.fetch('EMBERBSD_GI_QUERY_CONFIG')))
target = config.fetch('target', 'aarch64')
arch, machine = {'aarch64' => ['aarch64', 'AArch64'], 'amd64' => ['x86_64', 'Advanced Micro Devices X86-64']}[target]
abort 'unsupported pixbuf target architecture' unless machine
abort 'configuration differs from recipe target architecture' if ENV.key?('EMBERBSD_GI_TARGET') && ENV['EMBERBSD_GI_TARGET'] != target
absolute = lambda do |key|
  value = config.fetch(key)
  abort "#{key} must be absolute" unless value.is_a?(String) && value.start_with?('/')
  File.realpath(value)
end
base = absolute.call('build_root')
sysroot = absolute.call('sysroot')
cache = absolute.call('cache')
readelf = absolute.call('readelf')
abort 'readelf is not executable' unless File.executable?(readelf)
roots = [base, sysroot]
inside = lambda { |path, root| path == root || path.start_with?(root + '/') }
abort 'build/sysroot overlap' if inside.call(base, sysroot) || inside.call(sysroot, base)
abort 'cache overlaps providers' if inside.call(cache, sysroot) || inside.call(sysroot, cache)
host = config.fetch('ssh')
abort 'invalid SSH destination' unless host.is_a?(String) && host.match?(/\A(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*\z/)
ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'ConnectTimeout=5', '-o', 'ServerAliveInterval=10',
       '-o', 'ServerAliveCountMax=3', host]
if ARGV.first == '--check'
  abort 'usage: --check WORKDIR SYSROOT READELF' unless ARGV.size == 4
  workdir, target, tool = ARGV.drop(1).map { |p| File.realpath(p) }
  abort 'configuration differs from recipe' unless inside.call(workdir, base) && target == sysroot && tool == readelf
  puts 'PASS: GI query configuration matches the selected work, sysroot and readelf'
  exit
end

mode = ARGV.shift
abort 'usage: --loaders QUERY MODULE... | --mime PRINTER CACHE' unless %w[--loaders --mime].include?(mode)
exe = File.realpath(ARGV.shift || abort('binary required'))
abort 'binary outside build root' unless inside.call(exe, base)
expected = mode == '--loaders' ? 'gdk-pixbuf-query-loaders' : 'gdk-pixbuf-print-mime-types'
abort 'unexpected target tool' unless File.basename(exe) == expected
if mode == '--loaders'
  modules = ARGV.map { |p| File.realpath(p) }
  cache_input = nil
else
  abort 'one cache required' unless ARGV.size == 1
  cache_input = File.realpath(ARGV.first)
  abort 'cache outside build root' unless inside.call(cache_input, base)
  modules = File.read(cache_input).scan(/^"(\/[^"\n]+\.so)"$/).flatten.map { |p| File.realpath(p) }
end
abort 'missing target modules' if modules.empty?
abort 'duplicate target modules' unless modules.map { |p| File.basename(p) }.uniq.size == modules.size
modules.each do |p|
  abort 'invalid target module' unless inside.call(p, base) && File.basename(p).match?(/\Alibpixbufloader-[a-z0-9]+\.so\z/)
end
work = Dir.mktmpdir('pixbuf-tool-', cache)
stage = work + '/stage'
FileUtils.mkdir_p([stage + '/lib', stage + '/loaders'])
run = lambda do |name, *command, **opts|
  out, status = Open3.capture2e(*command, **opts)
  File.write(work + '/' + name + '.log', out)
  abort "#{name} failed (#{status.exitstatus}); see #{work}" unless status.success?
  out
end
# Resolve aliases before sysroot mapping. A host /usr/lib is never a provider.
mapdir = lambda do |path|
  if File.directory?(path)
    resolved = File.realpath(path)
    next resolved if roots.any? { |root| inside.call(resolved, root) }
  end
  if roots.any? { |root| inside.call(path, root) }
    path
  elsif path.start_with?('/')
    sysroot + path
  else
    File.expand_path(path, Dir.pwd)
  end
end
# Extra directories may select in-tree target libraries. They do not establish
# sysroot provenance; conflicting selected providers fail.
search = modules.map { |p| File.dirname(p) } + config.fetch('library_dirs', []) + ENV.fetch('LD_LIBRARY_PATH', '').split(':')
search = search.reject(&:empty?).map { |p| mapdir.call(p) }.uniq
defaults = %w[/usr/pkg/gcc16/lib /usr/pkg/lib /usr/lib /lib].map { |p| mapdir.call(p) }
files = {}
pending = [exe] + modules
until pending.empty?
  file = pending.shift
  header, status = Open3.capture2e(readelf, '-h', file)
  abort "not little-endian #{arch} ELF64: #{file}" unless status.success? && header.match?(/Machine:.*#{Regexp.escape(machine)}/) && header.match?(/Class:.*ELF64/) && header.match?(/Data:.*little endian/)
  dyn, status = Open3.capture2e(readelf, '-d', file)
  abort 'readelf failed' unless status.success?
  localdirs = dyn.scan(/\((?:RPATH|RUNPATH)\).*\[(.*?)\]/).flatten.flat_map { |s| s.split(':') }.map do |p|
    mapdir.call(p.gsub('${ORIGIN}', File.dirname(file)).gsub('$ORIGIN', File.dirname(file)))
  end
  dyn.scan(/\(NEEDED\).*\[(.*?)\]/).flatten.each do |name|
    abort 'unsafe SONAME' unless name.match?(/\A[a-zA-Z0-9._+-]+\z/)
    candidate = (search + localdirs + defaults).map { |d| d + '/' + name }.find { |p| File.file?(p) }
    abort "missing provider: #{name}" unless candidate
    candidate = File.realpath(candidate)
    abort 'provider outside target/build roots' unless roots.any? { |r| inside.call(candidate, r) }
    if files[name]
      abort "conflicting #{name}: #{files[name]} versus #{candidate}" unless Digest::SHA256.file(candidate).hexdigest == Digest::SHA256.file(files[name]).hexdigest
    else
      files[name] = candidate
      pending << candidate
    end
  end
end
sources = ([exe] + files.values + modules + [cache_input].compact).uniq.sort.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
FileUtils.cp(exe, stage + '/query')
File.chmod(0755, stage + '/query')
files.each { |name, path| FileUtils.cp(path, stage + '/lib/' + name) }
modules.each { |p| FileUtils.cp(p, stage + '/loaders/' + File.basename(p)) }
entries = Dir.glob(stage + '/**/*').select { |p| File.file?(p) }.sort
manifest = entries.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(stage + '/')}\n" }.join
File.write(stage + '/files.sha256', manifest)
File.write(work + '/files.sha256', manifest)
File.write(work + '/sources.sha256', sources.map { |p, h| "#{h}  #{p}\n" }.join)
run.call('tar', '/usr/bin/env', 'COPYFILE_DISABLE=1', 'tar', '--format=ustar', '--no-xattrs', '-czf', work + '/input.tar.gz', '-C', stage, '.')
remote = nil
begin
  remote = run.call('allocate', *ssh, "test \"$(uname -s)\" = NetBSD && test \"$(uname -p)\" = #{arch.shellescape} && umask 077 && mktemp -d /tmp/ember-pixbuf.XXXXXXXX").strip
  abort 'invalid temporary directory' unless remote.match?(/\A\/tmp\/ember-pixbuf\.[A-Za-z0-9]{8}\z/)
  run.call('transfer', *ssh, "tar -xzf - -C #{remote.shellescape}", stdin_data: File.binread(work + '/input.tar.gz'))
  invocation = [remote + '/query']
  if mode == '--loaders'
    invocation += modules.map { |p| remote + '/loaders/' + File.basename(p) }
  else
    target_cache = File.read(cache_input)
    modules.each { |p| target_cache = target_cache.gsub(p, remote + '/loaders/' + File.basename(p)) }
    hash = Digest::SHA256.hexdigest(target_cache)
    File.write(work + '/mime-cache.sha256', hash + "  loaders.cache\n")
    run.call('cache', *ssh, "cat > #{remote}/loaders.cache && printf '%s\n' '#{hash}  loaders.cache' >> #{remote}/files.sha256", stdin_data: target_cache)
  end
  script = <<~SH
    set -eu
    cd #{remote.shellescape}
    while read hash name; do
      test "$(sha256 -q "$name")" = "$hash" || exit 90
    done < files.sha256
    ulimit -c 0
    ulimit -f 16384
    export LD_LIBRARY_PATH=#{(remote + '/lib').shellescape}
    export GDK_PIXBUF_MODULE_FILE=#{(remote + '/loaders.cache').shellescape}
    unset LD_PRELOAD
    set +e
    timeout -k 5 60 #{invocation.shelljoin} > stdout.log 2> stderr.log
    result=$?
    set -e
    while read hash name; do
      test "$(sha256 -q "$name")" = "$hash" || exit 91
    done < files.sha256
    cat stdout.log
    cat stderr.log >&2
    exit "$result"
  SH
  output, errors, status = Open3.capture3(*ssh, 'sh -s', stdin_data: script)
  File.write(work + '/target.log', output)
  File.write(work + '/target.stderr', errors)
  File.write(work + '/exit.txt', "#{status.exitstatus}\n")
  $stderr.write(errors)
  abort "target query failed (#{status.exitstatus}), #{work}" unless status.success?
ensure
  if remote && remote.match?(/\A\/tmp\/ember-pixbuf\.[A-Za-z0-9]{8}\z/)
    out, status = Open3.capture2e(*ssh, "rm -rf -- #{remote.shellescape}")
    File.write(work + '/cleanup.log', "#{status.exitstatus}\n" + out)
    abort "remote cleanup failed: #{remote}" unless status.success?
  end
end
abort 'source providers changed during query' unless sources.all? { |p, h| Digest::SHA256.file(p).hexdigest == h }
if mode == '--loaders'
  modules.each { |p| output = output.gsub(remote + '/loaders/' + File.basename(p), p) }
  abort 'query output contains remote path' if output.include?(remote)
  abort 'incomplete loader query' unless output.scan(/^"(\/[^"\n]+\.so)"$/).flatten.sort == modules.sort
else
  abort 'invalid MIME query output' unless output.match?(/\A[a-zA-Z0-9.+_-]+\/[a-zA-Z0-9.+_-]+;(?:[a-zA-Z0-9.+_-]+\/[a-zA-Z0-9.+_-]+;)*\z/)
end
$stdout.write(output)
FileUtils.rm_rf(stage)
File.unlink(work + '/input.tar.gz')
