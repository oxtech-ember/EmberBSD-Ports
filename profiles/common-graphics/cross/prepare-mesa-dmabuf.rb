#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), compile a real DMA-BUF consumer with existing packages.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'
require 'json'

abort 'usage: prepare-mesa-dmabuf.rb CROSS_TOOLS SYSROOT HOST_PKG_CONFIG ACCEPTED_MESA_BUNDLE NEW_WORK' unless ARGV.length == 5
tools, sysroot, pkgconfig, mesa = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[4])
abort 'NEW_WORK must be new and absolute' unless ARGV[4].start_with?('/') && !File.exist?(work)
owner = File.dirname(File.realpath(__FILE__))
cc, readelf = %w[gcc readelf].map { |name| "#{tools}/bin/aarch64--netbsd-#{name}" }
prefix = "#{sysroot}/usr/pkg"
verify = "#{mesa}/run-mesa-package-tests.sh"
abort 'installed Mesa input verification failed' unless system('sh', verify, '--verify-sysroot', mesa, sysroot)
contents = ["#{mesa}/source/MesaLib.CONTENTS", "#{mesa}/MesaLib.CONTENTS"].find { |p| File.file?(p) }
abort 'require accepted canonical MesaLib 26.2.4nb3' unless contents && File.read(contents).include?("@name MesaLib-26.2.4nb3\n")
inputs = [__FILE__, "#{owner}/mesa-dmabuf.c", "#{owner}/run-mesa-dmabuf.sh", cc, readelf, pkgconfig, verify, contents,
          "#{mesa}/artifacts.sha256"] +
         %w[mesa-package-files.sha256 mesa-package-links.tsv runtime-libraries.sha256].map { |p| "#{mesa}/#{p}" } +
         %w[egl glesv2 gbm].map { |p| "#{prefix}/lib/pkgconfig/#{p}.pc" } +
         %w[EGL/egl.h EGL/eglext.h GLES2/gl2.h GLES2/gl2ext.h gbm.h libdrm/drm_fourcc.h].map { |p| "#{prefix}/include/#{p}" }
hashes = inputs.to_h { |p| [p, Digest::SHA256.file(p).hexdigest] }
bundle = "#{work}/bundle"
FileUtils.mkdir_p(["#{bundle}/bin", "#{bundle}/source"])
%w[mesa-package-files.sha256 mesa-package-links.tsv runtime-libraries.sha256].each { |p| FileUtils.cp("#{mesa}/#{p}", bundle) }
FileUtils.cp(verify, bundle)
FileUtils.cp(contents, "#{bundle}/source/MesaLib.CONTENTS")
FileUtils.cp("#{owner}/run-mesa-dmabuf.sh", bundle)
FileUtils.cp("#{owner}/mesa-dmabuf.c", "#{bundle}/source")

def run(log, environment, *command)
  File.write(log + '.command', Shellwords.join(command) + "\n")
  out, err, status = Open3.capture3(environment, *command)
  File.write(log, out + err)
  abort "command failed: #{log}" unless status.success?
  out.strip
end

environment = {'PKG_CONFIG_PATH'=>'', 'PKG_CONFIG_LIBDIR'=>"#{prefix}/lib/pkgconfig:#{prefix}/share/pkgconfig",
               'PKG_CONFIG_SYSROOT_DIR'=>sysroot}
%w[egl glesv2 gbm].each do |mod|
  abort "wrong #{mod} provider" unless run("#{bundle}/source/#{mod}-version.log", environment, pkgconfig, '--modversion', mod) == '26.2.4'
end
flags = Shellwords.split(run("#{bundle}/source/pkgconfig.log", environment, pkgconfig, '--cflags', '--libs', 'egl', 'glesv2', 'gbm'))
abort 'wrong compiler target' unless run("#{bundle}/source/target.log", {}, cc, '-dumpmachine') == 'aarch64--netbsd'
run("#{bundle}/source/compiler.log", {}, cc, '--version')
binary = "#{bundle}/bin/mesa-dmabuf"
run("#{bundle}/source/compile.log", {}, cc, "--sysroot=#{sysroot}", '-std=c11', '-D_NETBSD_SOURCE',
    '-O2', '-fPIC', '-pie', '-Wall', '-Wextra', '-Werror', "#{bundle}/source/mesa-dmabuf.c", *flags,
    '-pthread', "-Wl,-rpath-link,#{prefix}/lib", "-Wl,-rpath-link,#{prefix}/gcc16/lib",
    '-Wl,-rpath,/usr/pkg/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-o', binary)
elf = run("#{bundle}/source/elf.log", {}, readelf, '-h', '-d', binary)
header = File.binread(binary,20)
abort 'not AArch64 ELF' unless header.byteslice(0,6) == "\x7fELF\x02\x01" && header.byteslice(18,2).unpack1('v') == 183
abort 'missing actual EGL/GLES/GBM dependencies' unless %w[libEGL.so.1 libGLESv2.so.2 libgbm.so.1].all? { |p| elf.include?("[#{p}]") }
paths = elf.scan(/\((?:RPATH|RUNPATH)\).*\[([^\]]+)\]/).flatten.flat_map { |p| p.split(':') }
abort 'noncanonical runtime paths' unless paths.sort == %w[/usr/pkg/gcc16/lib /usr/pkg/lib]
File.write("#{bundle}/source/inputs.sha256", hashes.map { |p,h| "#{h}  #{p}\n" }.join)
File.write("#{bundle}/source/policy.json", JSON.pretty_generate({
  renderers: {'llvmpipe'=>{'LIBGL_ALWAYS_SOFTWARE'=>'1'}, 'V3D'=>{}}, cycles: 4,
  required: 'Real EmberBSD DRM device with linear ARGB8888 GEM/PRIME buffers and EGL DMA-BUF import',
  scope: 'GLES rendering into shared real device buffers, with explicit renderer acceptance; no compositor claim'
})+"\n")
hashes.each { |p,h| abort "input changed: #{p}" unless Digest::SHA256.file(p).hexdigest == h }
files = Dir.glob("#{bundle}/**/*").select { |p| File.file?(p) }.sort
File.write("#{bundle}/artifacts.sha256", files.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.delete_prefix(bundle+'/')}\n" }.join)
abort 'final bundle verification failed' unless system('sh', "#{bundle}/run-mesa-package-tests.sh", '--verify-sysroot', bundle, sysroot)
archive = "#{work}/mesa-dmabuf.tar.gz"
abort 'tar failed' unless system({'COPYFILE_DISABLE'=>'1'}, 'tar', '--no-xattrs', '-czf', archive, '-C', bundle, '.')
puts "#{Digest::SHA256.file(archive).hexdigest}  #{archive}"
