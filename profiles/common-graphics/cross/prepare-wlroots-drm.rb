#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), verify installed packages and compile an API consumer.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
require 'rubygems/package'
require 'zlib'

abort 'usage: prepare-wlroots-drm.rb CROSS_TOOLS SYSROOT HOST_PKG_CONFIG MESA_BUNDLE NEW_WORK PACKAGE...' unless ARGV.length == 22
tools, sysroot, pkgconfig, mesa = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[4])
abort 'NEW_WORK must be new and absolute' unless ARGV[4].start_with?('/') && !File.exist?(work)
packages = ARGV.drop(5).map { |p| File.realpath(p) }
expected = %w[wlroots-0.20.2nb4 input-headers-1.31.3 pixman-0.46.4 libxkbcommon-1.13.2nb1 xkeyboard-config-2.48nb1 wayland-1.26.0nb1 seatd-0.9.3nb1 libopeninput-1.31.3nb1 libdisplay-info-0.4.0 libliftoff-0.5.0 lcms2-2.19.1 tiff-4.7.2 libjpeg-turbo-3.2.0nb2 lerc-4.2.0 jbigkit-2.1nb1 libudev-bsd-0.7.0.1 libxcb-1.17.0]
abort 'provide the seventeen exact canonical consumer/dependency packages' unless packages.map { |p| File.basename(p, '.tgz') }.sort == expected.sort
owner = File.dirname(File.realpath(__FILE__))
cc, readelf = %w[gcc readelf].map { |n| "#{tools}/bin/aarch64--netbsd-#{n}" }
verify = "#{mesa}/run-mesa-package-tests.sh"
abort 'accepted Mesa verification failed' unless system('sh', verify, '--verify-sysroot', mesa, sysroot)
contents = ["#{mesa}/source/MesaLib.CONTENTS", "#{mesa}/MesaLib.CONTENTS"].find { |p| File.file?(p) }
abort 'need accepted MesaLib-26.2.6nb10' unless contents && File.read(contents).include?("@name MesaLib-26.2.6nb10\n")
inputs = [__FILE__, "#{owner}/wlroots-drm.c", "#{owner}/run-wlroots-drm.sh", cc, readelf, pkgconfig, verify,
          "#{mesa}/artifacts.sha256", contents, *packages] +
         %w[mesa-package-files.sha256 mesa-package-links.tsv runtime-libraries.sha256].map { |n| "#{mesa}/#{n}" }
hashes = inputs.to_h { |p| [p,Digest::SHA256.file(p).hexdigest] }
bundle = "#{work}/bundle"
FileUtils.mkdir_p(["#{bundle}/bin", "#{bundle}/source"])
FileUtils.cp(verify, bundle)
FileUtils.cp(contents, "#{bundle}/source/MesaLib.CONTENTS")
%w[wlroots-drm.c run-wlroots-drm.sh].each { |n| FileUtils.cp("#{owner}/#{n}", n.end_with?('.c') ? "#{bundle}/source" : bundle) }
files = File.readlines("#{mesa}/mesa-package-files.sha256").to_h { |l| h,p=l.chomp.split(/  /,2); [p,h] }
links = File.readlines("#{mesa}/mesa-package-links.tsv").to_h { |l| l.chomp.split("\t",2) }
runtime = File.readlines("#{mesa}/runtime-libraries.sha256").to_h { |l| h,p=l.chomp.split(/  /,2); [p,h] }
packages.each do |archive|
  identity = File.basename(archive, '.tgz')
  recorded = false
  Zlib::GzipReader.open(archive) do |gzip|
    Gem::Package::TarReader.new(gzip) do |tar|
      tar.each do |entry|
        next if entry.directory? || entry.header.typeflag == 'x'
        name = entry.full_name
        if name.start_with?('+')
          if name == '+CONTENTS'
            text = entry.read
            abort 'package name mismatch' unless text.include?("@name #{identity}\n")
            File.write("#{bundle}/source/#{identity}.CONTENTS", text)
            recorded = true
          elsif name == '+BUILD_INFO'
            text = entry.read
            abort 'require the explicit DRM/input/color wlroots package' if identity.start_with?('wlroots-') && !text.include?("PKG_OPTIONS=color-management drm glesv2 libinput libliftoff session\n")
            File.write("#{bundle}/source/#{identity}.BUILD_INFO", text)
          end
          next
        end
        abort 'unsafe package path' if name.start_with?('/') || name.split('/').include?('..')
        target = "/usr/pkg/#{name}"
        installed = sysroot + target
        if entry.file?
          hash = Digest::SHA256.hexdigest(entry.read)
          abort "installed package drift: #{target}" unless File.file?(installed) && Digest::SHA256.file(installed).hexdigest == hash
          files[target] = hash
          runtime[target] = hash if File.binread(installed,4) == "\x7fELF"
        elsif entry.header.typeflag == '2'
          abort "installed link drift: #{target}" unless File.symlink?(installed) && File.readlink(installed) == entry.header.linkname
          links[target] = entry.header.linkname
          # Absolute directory links (XKB compatibility root) have no file hash;
          # their exact value and every canonical descendant file are verified.
          if File.file?(installed)
            hash = Digest::SHA256.file(installed).hexdigest
            files[target] = hash
            runtime[target] = hash if File.binread(installed,4) == "\x7fELF"
          end
        else
          abort "unsupported package entry: #{name}"
        end
      end
    end
  end
  abort 'missing package identity' unless recorded
end
%w[mesa-package-files.sha256 runtime-libraries.sha256].zip([files,runtime]).each do |name,data|
  File.write("#{bundle}/#{name}",data.sort.map { |p,h| "#{h}  #{p}\n" }.join)
end
File.write("#{bundle}/mesa-package-links.tsv",links.sort.map { |p,t| "#{p}\t#{t}\n" }.join)

def run(log, env, *command)
  File.write(log+'.command',Shellwords.join(command)+"\n")
  out,err,status=Open3.capture3(env,*command)
  File.write(log,out+err)
  abort "command failed: #{log}" unless status.success?
  out.strip
end
prefix = sysroot+'/usr/pkg'
env={'PKG_CONFIG_PATH'=>'','PKG_CONFIG_LIBDIR'=>prefix+'/lib/pkgconfig:'+prefix+'/share/pkgconfig','PKG_CONFIG_SYSROOT_DIR'=>sysroot}
# Check every recorded ELF, not just the final executable's direct dependencies.
# This also covers the session/input and image-tool branches of the package set.
seen = {}
closure = []
missing = []
runtime.each do |path, hash|
  next if seen[hash]
  seen[hash] = true
  text = run("#{bundle}/source/closure-#{seen.length}.log", {}, readelf, '-d', sysroot + path)
  text.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten.each do |name|
    provider = runtime.keys.find { |p| File.basename(p) == name }
    provider ||= ["/usr/lib/#{name}", "/lib/#{name}"].find { |p| File.file?(sysroot + p) }
    missing << "#{path} requires #{name}" unless provider
    closure << [path, name, provider || 'MISSING'].join("\t")
  end
end
File.write("#{bundle}/source/recursive-needed.tsv", closure.join("\n") + "\n")
abort "unrecorded recursive dependencies:\n#{missing.join("\n")}" unless missing.empty?
abort 'wrong target compiler' unless run("#{bundle}/source/target.log",{},cc,'-dumpmachine') == 'aarch64--netbsd'
run("#{bundle}/source/compiler.log",{},cc,'--version')
abort 'wrong wlroots version' unless run("#{bundle}/source/version.log",env,pkgconfig,'--modversion','wlroots-0.20') == '0.20.2'
flags = Shellwords.split(run("#{bundle}/source/pkgconfig.log",env,pkgconfig,'--cflags','--libs','wlroots-0.20','egl','glesv2','wayland-server','xkbcommon','libdrm'))
binary="#{bundle}/bin/wlroots-drm"
run("#{bundle}/source/compile.log",{},cc,"--sysroot=#{sysroot}",'-std=c11','-D_NETBSD_SOURCE','-DWLR_USE_UNSTABLE','-O2','-fPIC','-pie','-Wall','-Wextra','-Werror',"#{bundle}/source/wlroots-drm.c",*flags,'-pthread',"-Wl,-rpath-link,#{prefix}/lib","-Wl,-rpath-link,#{prefix}/gcc16/lib",'-Wl,-rpath,/usr/pkg/lib','-Wl,-rpath,/usr/pkg/gcc16/lib','-o',binary)
header=File.binread(binary,20)
abort 'not AArch64 ELF' unless header.byteslice(0,6)=="\x7fELF\x02\x01" && header.byteslice(18,2).unpack1('v')==183
elf=run("#{bundle}/source/elf.log",{},readelf,'-h','-d',binary)
abort 'missing real wlroots library link' unless elf.include?('[libwlroots-0.20.so]')
paths=elf.scan(/\((?:RPATH|RUNPATH)\).*\[([^\]]+)\]/).flatten.flat_map { |p| p.split(':') }
abort 'noncanonical rpath' unless paths.sort==%w[/usr/pkg/gcc16/lib /usr/pkg/lib]
elf.scan(/\(NEEDED\).*\[([^\]]+)\]/).flatten.each do |n|
  abort "unrecorded consumer dependency: #{n}" unless runtime.keys.any? { |p| File.basename(p)==n } || File.file?("#{sysroot}/usr/lib/#{n}") || File.file?("#{sysroot}/lib/#{n}")
end
File.write("#{bundle}/source/inputs.sha256",hashes.map { |p,h| "#{h}  #{p}\n" }.join)
File.write("#{bundle}/source/policy.json",JSON.pretty_generate({packages: expected, default_renderer: 'llvmpipe', renderer_modes: {llvmpipe: {LIBGL_ALWAYS_SOFTWARE:'1',WLR_RENDERER_ALLOW_SOFTWARE:'1'}, virgl: {}}, scope:'Four real DRM modeset/presentation frames through libseat, GLES2 pixel readback and cleanup with the explicitly selected actual renderer; input enumeration is not physical event acceptance.'})+"\n")
hashes.each { |p,h| abort "input changed: #{p}" unless Digest::SHA256.file(p).hexdigest==h }
artifacts=Dir.glob("#{bundle}/**/*").select { |p| File.file?(p) }.sort
File.write("#{bundle}/artifacts.sha256",artifacts.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(bundle+'/')}\n" }.join)
abort 'final bundle/sysroot verification failed' unless system('sh',"#{bundle}/run-mesa-package-tests.sh",'--verify-sysroot',bundle,sysroot)
archive="#{work}/wlroots-drm.tar.gz"
abort 'tar failed' unless system({'COPYFILE_DISABLE'=>'1'},'tar','--no-xattrs','-czf',archive,'-C',bundle,'.')
puts "#{Digest::SHA256.file(archive).hexdigest}  #{archive}"
