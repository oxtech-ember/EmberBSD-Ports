#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), private root preparation from explicit inputs.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
abort 'usage: prepare-labwc-root.rb SYSROOT BASE_ROOT CLIENT READELF LABWC_PACKAGE NEW_WORK' unless ARGV.size == 6
sysroot, base, client, readelf, package = ARGV.first(5).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
abort 'work overlaps input' if [sysroot, base].any? { |p| work == p || work.start_with?(p + '/') }
FileUtils.mkdir_p(work + '/root')
root = work + '/root'
# Preserve rescue hard links; file-by-file copies inflate the synthetic image.
statuses = Open3.pipeline([{'COPYFILE_DISABLE'=>'1'}, 'tar', '-cf', '-', '-C', base, '.'],
  [{'COPYFILE_DISABLE'=>'1'}, 'tar', '-xpf', '-', '-C', root])
abort 'base copy failed' unless statuses.all?(&:success?)
inputs = [__FILE__, client, readelf, package]
# This checks the known fork shared-libc repair, not the complete base provenance.
libc = '5dff821f1a1b42845e642cedd16375b310b78d04fa624bb21472d33b0fc14130'
[base, sysroot].each do |tree|
  %w[/lib/libc.so /lib/libc.so.12 /usr/lib/libc.so /usr/lib/libc.so.12].each do |p|
    next if tree == base && p != '/usr/lib/libc.so.12' && !File.exist?(tree + p)
    abort "unverified fork libc: #{tree + p}" unless Digest::SHA256.file(tree + p).hexdigest == libc
  end
end
base_manifest = Dir.glob(base + '/**/*', File::FNM_DOTMATCH).select { |p| File.file?(p) && !File.symlink?(p) }.sort.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(base)}\n" }.join
File.write(work + '/base-files.sha256', base_manifest)
listing, status = Open3.capture2('tar', '-tzf', package)
abort 'unsafe package paths' unless status.success? && listing.lines.all? { |l| !l.start_with?('/') && !l.strip.split('/').include?('..') }
FileUtils.mkdir_p(work + '/package')
abort 'extract package' unless system('tar', '-xzf', package, '-C', work + '/package')
abort 'wrong labwc package' unless File.read(work + '/package/+CONTENTS').include?("@name labwc-0.20.2nb2\n")
Dir.glob(work + '/package/**/*').each do |p|
  next if File.directory?(p) || File.basename(p).start_with?('+')
  installed = sysroot + '/usr/pkg/' + p.delete_prefix(work + '/package/')
  matches = if File.symlink?(p)
    File.symlink?(installed) && File.readlink(p) == File.readlink(installed)
  else
    File.file?(installed) && Digest::SHA256.file(p).hexdigest == Digest::SHA256.file(installed).hexdigest
  end
  abort "package/sysroot differ: #{installed}" unless matches
end
copied = {}
copy = nil
copy = lambda do |path|
  abort 'unsafe target path' unless path.start_with?('/') && !path.split('/').include?('..')
  source, destination = sysroot + path, root + path
  abort "missing provider #{source}" unless File.exist?(source) || File.symlink?(source)
  abort 'source escapes sysroot' unless File.realpath(source).start_with?(sysroot + '/')
  return if copied[path]
  copied[path] = true
  FileUtils.mkdir_p(File.dirname(destination))
  abort 'destination escapes root' unless File.realpath(File.dirname(destination)).start_with?(root + '/')
  FileUtils.rm_f(destination)
  if File.symlink?(source)
    target = File.readlink(source)
    abort 'absolute provider symlink' if target.start_with?('/')
    resolved = File.expand_path(target, File.dirname(path))
    abort 'provider escapes system directories' unless resolved.start_with?('/usr/', '/lib/')
    File.symlink(target, destination)
    copy.call(resolved)
  else
    FileUtils.cp(source, destination, preserve: true)
    inputs << source
  end
end
# Full compositor, SVG/MIME and font payloads; other shared providers follow ELF.
%w[labwc-0.20.2nb2 nerd-fonts-Hack-3.5.1 fontconfig-2.18.3 librsvg-2.63.4nb1 gdk-pixbuf2-2.44.8nb2 shared-mime-info-2.5.1].each do |pkg|
  metadata = sysroot + '/usr/pkg/pkgdb/' + pkg + '/+CONTENTS'
  inputs << metadata
  previous = nil
  ignore = false
  File.foreach(metadata) do |line|
    line = line.chomp
    if line == '@ignore'; ignore = true; next; end
    if line.start_with?('@comment MD5:') && previous
      file = sysroot + '/usr/pkg/' + previous
      abort "package checksum: #{file}" unless File.symlink?(file) || Digest::MD5.file(file).hexdigest == line.split(':').last
    end
    next if line.start_with?('@')
    if ignore; ignore = false; next; end
    abort 'unsafe package path' if line.start_with?('/') || line.split('/').include?('..')
    previous = line
    copy.call('/usr/pkg/' + line)
  end
end
FileUtils.mkdir_p(root + '/tests/labwc/config')
FileUtils.mkdir_p(root + '/var/shm')
FileUtils.cp(client, root + '/tests/labwc/client')
queue = Dir.glob(root + '/usr/pkg/bin/*') + [root + '/tests/labwc/client']
seen = {}
search = %w[/usr/pkg/lib /usr/pkg/gcc16/lib /usr/lib /lib]
until queue.empty?
  file = queue.shift
  next unless File.file?(file) && File.binread(file, 4) == "\x7fELF"
  path = File.realpath(file)
  abort 'runtime escaped root' unless path.start_with?(root + '/')
  next if seen[path]
  seen[path] = true
  dynamic, status = Open3.capture2e(readelf, '-d', file)
  abort dynamic unless status.success?
  dynamic.scan(/\(NEEDED\).*\[(.*?)\]/).flatten.each do |name|
    abort 'unsafe SONAME' unless name.match?(/\A[A-Za-z0-9._+-]+\z/)
    target = search.map { |d| d + '/' + name }.find { |p| File.file?(sysroot + p) }
    abort "missing ELF provider #{name}" unless target
    copy.call(target)
    queue << root + target
  end
end
manifest = seen.keys.sort.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(root)}\n" }.join
File.write(root + '/tests/labwc/runtime.sha256', manifest)
File.write(root + '/tests/labwc/fonts.conf', '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig><dir>/usr/pkg/share/fonts/X11/TTF</dir><cachedir>/tmp/fontcache</cachedir></fontconfig>')
File.write(root + '/tests/labwc/config/rc.xml', '<?xml version="1.0"?><labwc_config><core><gap>0</gap></core><focus><followMouse>yes</followMouse></focus><keyboard><keybind key="F10"><action name="ToggleMaximize"/></keybind><keybind key="F11"><action name="ToggleFullscreen"/></keybind></keyboard><mouse><context name="Frame"><mousebind button="A-Left" action="Drag"><action name="Move"/></mousebind></context></mouse></labwc_config>')
boot = File.expand_path('run-labwc-guest.sh', __dir__)
inputs << boot
FileUtils.cp(boot, root + '/etc/rc')
File.chmod(0755, root + '/etc/rc')
File.write(work + '/inputs.sha256', inputs.uniq.sort.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
File.write(work + '/root-files.sha256', Dir.glob(root + '/**/*', File::FNM_DOTMATCH).select { |p| File.file?(p) && !File.symlink?(p) }.sort.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(root)}\n" }.join)
puts "PASS: private root staged; #{seen.size} runtime ELF files guarded; makefs and target execution remain separate"
