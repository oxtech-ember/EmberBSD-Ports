#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), installed common text/image stack acceptance.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require 'rubygems/package'
require 'zlib'

abort 'usage: prepare-text-render.rb CROSS_TOOLS SYSROOT HOST_PKG_CONFIG DRM_BUNDLE PANGO_ARCHIVE FONT_LICENSE NEW_WORK PACKAGE...' unless ARGV.size >= 8
tools, sysroot, pkgconfig, base, source, license = ARGV.first(6).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[6])
abort 'NEW_WORK must be new and absolute' unless ARGV[6].start_with?('/') && !File.exist?(work) && !File.symlink?(work)
packages = ARGV.drop(7).map { |p| File.realpath(p) }
required = %w[pango-1.58.2nb2 glib2-2.90.1 pcre2-10.49nb1 fribidi-1.0.18 png-1.6.59 freetype2-2.14.3nb1 fontconfig-2.18.4 harfbuzz-14.6.0 cairo-1.18.6]
names = packages.map { |p| File.basename(p, '.tgz') }
abort 'missing current text package or duplicate input' unless (required - names).empty? && names.uniq == names
abort 'Pango fixture source mismatch' unless Digest::SHA256.file(source).hexdigest == '342385b6ca3b7c73455d7c80a13b7dbe4489e00bc3bd4c5bd6ed4dce421e374a'
abort 'DejaVu license mismatch' unless Digest::SHA256.file(license).hexdigest == '7a083b136e64d064794c3419751e5c7dd10d2f64c108fe5ba161eae5e5958a93'
owner = File.dirname(File.realpath(__FILE__))
cc, readelf = %w[gcc readelf].map { |n| tools + '/bin/aarch64--netbsd-' + n }
verifier = base + '/run-mesa-package-tests.sh'
abort 'base bundle/sysroot verification failed' unless system('sh', verifier, '--verify-sysroot', base, sysroot)
inputs = [__FILE__, owner + '/text-render.c', owner + '/run-text-render.sh',
          source, license, cc, readelf, pkgconfig, verifier, base + '/artifacts.sha256',
          *%w[mesa-package-files.sha256 mesa-package-links.tsv runtime-libraries.sha256].map { |n| base + '/' + n }, *packages]
hashes = inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
bundle = work + '/bundle'
FileUtils.mkdir_p([bundle + '/bin', bundle + '/source', bundle + '/fixtures'])
FileUtils.cp(verifier, bundle)
FileUtils.cp(owner + '/run-text-render.sh', bundle)
FileUtils.cp(owner + '/text-render.c', bundle + '/source')
FileUtils.cp(license, bundle + '/fixtures/DejaVu-LICENSE')
font, err, status = Open3.capture3('tar', '-xJOf', source, 'pango-1.58.2/tests/fonts/DejaVuSans.ttf')
abort "font extraction failed: #{err}" unless status.success? && font.bytesize > 100_000
File.binwrite(bundle + '/fixtures/DejaVuSans.ttf', font)
File.write(bundle + '/fixtures/fonts.conf', "<?xml version=\"1.0\"?><!DOCTYPE fontconfig SYSTEM \"urn:fontconfig:fonts.dtd\"><fontconfig></fontconfig>\n")
File.write(bundle + '/source/fixture-provenance.txt', <<~TEXT)
  Font: unmodified tests/fonts/DejaVuSans.ttf from Pango 1.58.2 release archive
  https://download.gnome.org/sources/pango/1.58/pango-1.58.2.tar.xz
  Archive SHA256: #{Digest::SHA256.file(source).hexdigest}
  Font SHA256: #{Digest::SHA256.hexdigest(font)}
  Full unchanged font license:
  https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/version_2_37/LICENSE
  License SHA256: #{Digest::SHA256.file(license).hexdigest}
TEXT
files = File.readlines(base + '/mesa-package-files.sha256').to_h { |l| h,p=l.chomp.split(/  /,2); [p,h] }
links = File.readlines(base + '/mesa-package-links.tsv').to_h { |l| l.chomp.split("\t",2) }
runtime = File.readlines(base + '/runtime-libraries.sha256').to_h { |l| h,p=l.chomp.split(/  /,2); [p,h] }
packages.each do |archive|
  identity = File.basename(archive, '.tgz')
  identified = false
  Zlib::GzipReader.open(archive) do |gzip|
    Gem::Package::TarReader.new(gzip) do |tar|
      tar.each do |entry|
        next if entry.directory? || entry.header.typeflag == 'x'
        name = entry.full_name
        if name.start_with?('+')
          if %w[+CONTENTS +BUILD_INFO].include?(name)
            data = entry.read
            if name == '+CONTENTS'
              abort 'package identity mismatch' unless data.include?("@name #{identity}\n")
              identified = true
            end
            File.write(bundle + '/source/' + identity + '.' + name.delete_prefix('+'), data)
          end
          next
        end
        abort 'unsafe package member' if name.start_with?('/') || name.split('/').include?('..')
        target = '/usr/pkg/' + name
        installed = sysroot + target
        if entry.file?
          hash = Digest::SHA256.hexdigest(entry.read)
          abort "installed file mismatch: #{target}" unless File.file?(installed) && Digest::SHA256.file(installed).hexdigest == hash
          files[target] = hash
          runtime[target] = hash if File.binread(installed, 4) == "\x7fELF"
        elsif entry.header.typeflag == '2'
          abort "installed link mismatch: #{target}" unless File.symlink?(installed) && File.readlink(installed) == entry.header.linkname
          links[target] = entry.header.linkname
          if File.file?(installed)
            hash = Digest::SHA256.file(installed).hexdigest
            files[target] = hash
            runtime[target] = hash if File.binread(installed, 4) == "\x7fELF"
          end
        else
          abort "unsupported package member: #{name}"
        end
      end
    end
  end
  abort 'package identity absent' unless identified
end
%w[mesa-package-files.sha256 runtime-libraries.sha256].zip([files,runtime]).each do |name,data|
  File.write(bundle + '/' + name, data.sort.map { |p,h| "#{h}  #{p}\n" }.join)
end
File.write(bundle + '/mesa-package-links.tsv', links.sort.map { |p,t| "#{p}\t#{t}\n" }.join)

def run(log, env, *command)
  File.write(log + '.command', Shellwords.join(command) + "\n")
  out,err,status = Open3.capture3(env, *command)
  File.write(log, out + err)
  abort "command failed: #{log}" unless status.success?
  out.strip
end

prefix = sysroot + '/usr/pkg'
env = {'PKG_CONFIG_PATH'=>'', 'PKG_CONFIG_LIBDIR'=>prefix+'/lib/pkgconfig:'+prefix+'/share/pkgconfig:'+sysroot+'/usr/lib/pkgconfig', 'PKG_CONFIG_SYSROOT_DIR'=>sysroot}
seen, closure, missing = {}, [], []
runtime.each do |path, hash|
  next if seen[hash]
  seen[hash] = true
  text = run(bundle + '/source/closure-' + seen.size.to_s + '.log', {}, readelf, '-d', sysroot + path)
  text.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten.each do |name|
    provider = runtime.keys.find { |p| File.basename(p) == name }
    provider ||= ["/usr/lib/#{name}", "/lib/#{name}"].find { |p| File.file?(sysroot + p) }
    missing << "#{path}: #{name}" unless provider
    closure << [path, name, provider || 'MISSING'].join("\t")
  end
end
File.write(bundle + '/source/recursive-needed.tsv', closure.join("\n") + "\n")
abort "unrecorded recursive dependencies:\n#{missing.join("\n")}" unless missing.empty?
abort 'wrong target compiler' unless run(bundle+'/source/compiler-target.log', {}, cc, '-dumpmachine') == 'aarch64--netbsd'
modules = {'pangocairo'=>'1.58.2', 'pangoft2'=>'1.58.2', 'glib-2.0'=>'2.90.1', 'harfbuzz'=>'14.6.0', 'cairo'=>'1.18.6', 'fontconfig'=>'2.18.4', 'freetype2'=>'26.6.20'}
modules.each do |name,version|
  actual = run(bundle+'/source/version-'+name+'.log', env, pkgconfig, '--modversion', name)
  abort "wrong #{name} version: #{actual}" unless actual == version
end
flags = Shellwords.split(run(bundle+'/source/pkgconfig.log', env, pkgconfig, '--cflags', '--libs', *modules.keys))
binary = bundle + '/bin/text-render'
command = [cc, "--sysroot=#{sysroot}", '-std=c11', '-O2', '-fPIC', '-pie', '-Wall', '-Wextra', '-Werror',
           bundle+'/source/text-render.c', *flags, '-pthread', "-Wl,-rpath-link,#{prefix}/lib", "-Wl,-rpath-link,#{prefix}/gcc16/lib",
           '-Wl,-rpath,/usr/pkg/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-o', binary]
run(bundle+'/source/compile.log', {}, *command)
controls = {
  'no-draw' => ["\tpango_cairo_show_layout(cr, layout);", "\t/* Negative control: deliberately omit drawing. */"],
  'no-ligature' => ['enabled ? "liga=1" : "liga=0"', '"liga=0"']
}
controls.each do |name, (old, replacement)|
  original = File.read(bundle+'/source/text-render.c')
  abort "ambiguous negative control: #{name}" unless original.scan(old).length == 1
  control = bundle+'/source/control-'+name+'.c'
  File.write(control, original.sub(old, replacement))
  args = command.map { |p| p == bundle+'/source/text-render.c' ? control : p }
  args[args.index('-o') + 1] = bundle+'/bin/control-'+name
  run(bundle+'/source/control-'+name+'.compile.log', {}, *args)
end
header = File.binread(binary,20)
abort 'not AArch64 ELF' unless header.byteslice(0,6) == "\x7fELF\x02\x01" && header.byteslice(18,2).unpack1('v') == 183
elf = run(bundle+'/source/elf.log', {}, readelf, '-d', binary)
paths = elf.scan(/\((?:RPATH|RUNPATH)\).*\[([^\]]+)\]/).flatten.flat_map { |p| p.split(':') }
abort 'noncanonical rpath' unless paths.sort == %w[/usr/pkg/gcc16/lib /usr/pkg/lib]
elf.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten.each do |name|
  abort "unrecorded consumer dependency: #{name}" unless runtime.keys.any? { |p| File.basename(p) == name } || %w[/lib /usr/lib].any? { |p| File.file?(sysroot+p+'/'+name) }
end
File.write(bundle+'/source/inputs.sha256', hashes.map { |p,h| "#{h}  #{p}\n" }.join)
hashes.each { |p,h| abort "input changed: #{p}" unless Digest::SHA256.file(p).hexdigest == h }
artifacts = Dir.glob(bundle+'/**/*').select { |p| File.file?(p) }.sort
File.write(bundle+'/artifacts.sha256', artifacts.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(bundle+'/')}\n" }.join)
abort 'final bundle/sysroot verification failed' unless system('sh', bundle+'/run-mesa-package-tests.sh', '--verify-sysroot', bundle, sysroot)
archive = work + '/text-render.tar.gz'
abort 'archive failed' unless system({'COPYFILE_DISABLE'=>'1'}, 'tar', '--no-xattrs', '-czf', archive, '-C', bundle, '.')
puts "#{Digest::SHA256.file(archive).hexdigest}  #{archive}"
