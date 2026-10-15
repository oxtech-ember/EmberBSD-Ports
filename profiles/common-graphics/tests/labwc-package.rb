#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Inspect the packaged compositor without executing it.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'

def accepted_rpath?(path, sysroot, directory)
  return true if %w[/usr/pkg/lib /usr/pkg/gcc16/lib /usr/lib /lib].include?(directory)

  # Match the accepted Mesa/LLVM package closure's retained Python libdir.
  inherited = %w[/usr/pkg/lib/libgallium-26.2.4.so /usr/pkg/lib/libLLVM.so.23.1]
  return true if inherited.include?(path.delete_prefix(sysroot)) &&
    directory == '/usr/pkg/lib/python3.15/config-3.15'

  # The accepted GCC16 package retains these compiler runtime search paths.
  # They are not permission for consumers to embed arbitrary build paths.
  path.start_with?(sysroot + '/usr/pkg/gcc16/lib/') &&
    %w[/usr/pkg/gcc16/aarch64--netbsd/lib/. /usr/pkg/gcc16/lib/.].include?(directory)
end

if ARGV == ['--rpath-regression']
  root = '/test/sysroot'
  compiler = root + '/usr/pkg/gcc16/lib/libgcc_s.so.1'
  consumer = root + '/usr/pkg/bin/labwc'
  [[compiler, '/usr/pkg/gcc16/aarch64--netbsd/lib/.', true],
   [compiler, '/usr/pkg/gcc16/lib/.', true],
   [consumer, '/usr/pkg/lib', true],
   [root + '/usr/pkg/lib/libgallium-26.2.4.so', '/usr/pkg/lib/python3.15/config-3.15', true],
   [root + '/usr/pkg/lib/libLLVM.so.23.1', '/usr/pkg/lib/python3.15/config-3.15', true],
   [consumer, '/usr/pkg/lib/python3.15/config-3.15', false],
   [consumer, '/usr/pkg/gcc16/aarch64--netbsd/lib/.', false],
   [compiler, '/tmp/build/lib', false],
   [consumer, '/test/sysroot/usr/pkg/lib', false],
   [compiler, '/usr/pkg/gcc16/lib/../../tmp', false]].each do |path, dir, expected|
    abort "wrong RPATH decision: #{path}: #{dir}" unless accepted_rpath?(path, root, dir) == expected
  end
  puts 'PASS: inherited GCC/Mesa/LLVM paths accepted; consumer and build-path leaks rejected'
  exit
end

abort 'Usage: labwc-package.rb PACKAGE SYSROOT READELF BUILT_SOURCE NEW_WORK' unless ARGV.size == 5
package, sysroot, readelf, source = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'new absolute work required' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work + '/payload')
listing, status = Open3.capture2('tar', '-tzf', package)
abort 'unsafe package path' unless status.success? && listing.lines.all? { |l| p = l.strip; !p.start_with?('/') && !p.split('/').include?('..') }
abort 'extract failed' unless system('tar', '-xzf', package, '-C', work + '/payload')
contents = File.read(work + '/payload/+CONTENTS')
abort 'wrong package' unless contents.lines.any? { |l| l.strip == '@name labwc-0.20.2nb2' }
files = Dir.glob(work + '/payload/**/*').reject { |p| File.directory?(p) || File.basename(p).start_with?('+') }
manifest = []
files.each do |p|
  installed = sysroot + '/usr/pkg/' + p.delete_prefix(work + '/payload/')
  if File.symlink?(p)
    abort "different symlink: #{installed}" unless File.symlink?(installed) && File.readlink(p) == File.readlink(installed)
  else
    hash = Digest::SHA256.file(p).hexdigest
    abort "different installed file: #{installed}" unless hash == Digest::SHA256.file(installed).hexdigest
    manifest << "#{hash}  #{installed}\n"
  end
end
required = %w[bin/labwc bin/labnag bin/lab-sensible-terminal bin/startlabwc man/man1/labwc.1 man/man1/labnag.1 share/wayland-sessions/labwc.desktop share/xdg-desktop-portal/labwc-portals.conf share/examples/labwc/rc.xml share/locale/ru/LC_MESSAGES/labwc.mo]
required.each { |p| abort "missing payload: #{p}" unless File.size?(sysroot + '/usr/pkg/' + p) }
configuration = File.read(source + '/output/include/config.h')
%w[NLS RSVG LIBSFDO].each { |f| abort "missing feature: #{f}" unless configuration.match?(/^#define HAVE_#{f} 1$/) }
abort 'unexpected Xwayland feature' unless configuration.match?(/^#define HAVE_XWAYLAND 0$/)
options = JSON.parse(File.read(source + '/output/meson-info/intro-buildoptions.json')).to_h { |o| [o.fetch('name'), o.fetch('value')] }
%w[man-pages svg icon labnag nls].each { |f| abort "not explicitly enabled: #{f}" unless options.fetch(f) == 'enabled' }
abort 'unexpected Xwayland option' unless options.fetch('xwayland') == 'disabled'
abort 'subproject fallback enabled' unless options.fetch('wrap_mode') == 'nofallback'
targets = JSON.parse(File.read(source + '/output/meson-info/intro-targets.json'))
%w[labwc labnag].each { |name| abort "missing installed target #{name}" unless targets.any? { |t| t.fetch('name') == name && t.fetch('installed') } }
scanner_rules = targets.flat_map { |t| t.fetch('target_sources', []) }.flat_map { |s| s.fetch('compiler', []) }.grep(/wayland-scanner$/)
abort 'missing native scanner rules' if scanner_rules.empty?
scanner_rules.uniq.each { |p| abort 'scanner is target ELF' if File.binread(p, 4) == "\x7fELF" }
man_rules = targets.select { |t| t.fetch('name').match?(/\A(?:labwc|labnag)(?:-[a-z]+)?\.[15]\z/) }
abort 'missing six man page targets' unless man_rules.size == 6 && man_rules.all? { |t| t.fetch('installed') }

# Record the ELF closure selected from this sysroot. Runtime loading is a
# separate target check; this inspection never borrows providers from macOS.
search = %w[/usr/pkg/gcc16/lib /usr/pkg/lib /usr/lib /lib].map { |p| sysroot + p }
queue = %w[labwc labnag].map { |p| sysroot + '/usr/pkg/bin/' + p }
seen = {}
needed = []
until queue.empty?
  path = File.realpath(queue.shift)
  next if seen[path]
  seen[path] = true
  abort 'provider escaped sysroot' unless path.start_with?(sysroot + '/')
  header, status = Open3.capture2e(readelf, '-h', path)
  abort "wrong ELF: #{path}" unless status.success? && header.match?(/Machine:.*AArch64/) && header.match?(/Class:.*ELF64/) && header.match?(/Data:.*little endian/)
  dynamic, status = Open3.capture2e(readelf, '-d', path)
  abort 'ELF inspection failed' unless status.success?
  dynamic.scan(/\((?:RPATH|RUNPATH)\).*\[(.*?)\]/).flatten.flat_map { |v| v.split(':') }.each do |dir|
    abort "noncanonical runtime path: #{path}: #{dir}" unless accepted_rpath?(path, sysroot, dir)
  end
  dynamic.scan(/\(NEEDED\).*\[(.*?)\]/).flatten.each do |name|
    abort 'unsafe SONAME' unless name.match?(/\A[A-Za-z0-9._+-]+\z/)
    provider = search.map { |d| d + '/' + name }.find { |p| File.file?(p) } or abort "missing provider #{name}"
    needed << name
    queue << provider
  end
  File.write(work + '/' + File.basename(path) + '.dynamic', dynamic)
  manifest << "#{Digest::SHA256.file(path).hexdigest}  #{path}\n"
end
%w[libwlroots-0.20.so librsvg-2.so.2 libinput.so.10 libEGL.so.1 libGLESv2.so.2].each do |name|
  abort "expected shared provider missing: #{name}" unless needed.include?(name)
end
manifest += [__FILE__, package, source + '/output/build.ninja', source + '/output/include/config.h'].map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }
File.write(work + '/inputs.sha256', manifest.uniq.join)
File.write(work + '/needed.txt', needed.uniq.sort.join("\n") + "\n")
puts "PASS: #{files.size} installed payload files/links, complete selected features, native generator rules, #{seen.size} target ELF files inspected"
puts 'Target execution and a complete Wayland session remain separate acceptance.'
