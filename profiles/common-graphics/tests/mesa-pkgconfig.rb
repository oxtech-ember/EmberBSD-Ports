#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), compile an actual consumer through installed metadata.
require 'digest'
require 'fileutils'
require 'open3'
require 'shellwords'

abort 'usage: mesa-pkgconfig.rb CROSS_TOOLS SYSROOT HOST_PKG_CONFIG NEW_WORK [epoxy|desktop-gl]' unless ARGV.length == 4 || (ARGV.length == 5 && %w[epoxy desktop-gl].include?(ARGV[4]))
desktop = ARGV[4] == 'desktop-gl'
epoxy = desktop || ARGV[4] == 'epoxy'
tools, sysroot, pkgconfig = ARGV.first(3).map { |p| File.realpath(p) }
work = File.expand_path(ARGV[3])
abort 'NEW_WORK must not exist' if File.exist?(work)
FileUtils.mkdir_p(work)
cc = "#{tools}/bin/aarch64--netbsd-gcc"
readelf = "#{tools}/bin/aarch64--netbsd-readelf"
source = File.expand_path('../cross/mesa-render.c', __dir__)
prefix = "#{sysroot}/usr/pkg"
environment = {'PKG_CONFIG_PATH' => '', 'PKG_CONFIG_LIBDIR' => "#{prefix}/lib/pkgconfig:#{prefix}/share/pkgconfig",
               'PKG_CONFIG_SYSROOT_DIR' => sysroot}

def run(environment, log, *command)
  File.write(log + '.command', Shellwords.join(command) + "\n")
  out, err, status = Open3.capture3(environment, *command)
  File.write(log, out + err)
  abort "failed: #{log}" unless status.success?
  out.strip
end

modules = %w[gl glx egl gbm glesv1_cm glesv2 dri]
modules << 'epoxy' if epoxy
modules.each do |mod|
  version = run(environment, "#{work}/#{mod}-version.log", pkgconfig, '--modversion', mod)
  abort "wrong #{mod} provider" unless version == (mod == 'epoxy' ? '1.5.10' : '26.2.4')
  run(environment, "#{work}/#{mod}-shared.log", pkgconfig, '--cflags', '--libs', mod)
  run(environment, "#{work}/#{mod}-static-metadata.log", pkgconfig, '--static', '--cflags', '--libs', mod)
end
link_modules = epoxy ? %w[epoxy gbm] : %w[egl glesv2 gbm]
flags = Shellwords.split(run(environment, "#{work}/consumer-flags.log", pkgconfig, '--cflags', '--libs', *link_modules))
flags << '-DEMBER_EPOXY_DISPATCH' if epoxy
flags << '-DEMBER_DESKTOP_GL' if desktop
executable = "#{work}/#{epoxy ? 'epoxy' : 'mesa'}-pkgconfig-render"
# PIC keeps libepoxy's dispatch-pointer imports as undefined GOT entries;
# non-PIC executables legitimately use COPY relocations instead.
command = [cc, "--sysroot=#{sysroot}", '-std=c11', '-D_NETBSD_SOURCE', '-O2', '-fPIC', '-pie', '-Wall', '-Wextra', '-Werror',
           source, *flags, '-pthread', "-Wl,-rpath-link,#{prefix}/lib", "-Wl,-rpath-link,#{prefix}/gcc16/lib",
           '-Wl,-rpath,/usr/pkg/lib', '-Wl,-rpath,/usr/pkg/gcc16/lib', '-o', executable]
run({}, "#{work}/consumer-build.log", *command)
elf = run({}, "#{work}/consumer-elf.log", readelf, '-h', '-d', '-Ws', executable)
providers = epoxy ? %w[libepoxy.so.0 libgbm.so.1] : %w[libEGL.so.1 libGLESv2.so.2 libgbm.so.1]
abort 'consumer is not target ELF with selected providers' unless elf.include?('AArch64') && providers.all? { |name| elf.include?("[#{name}]") }
if epoxy
  abort 'epoxy consumer bypasses dynamic dispatch' if elf.include?('[libEGL.so.1]') || elf.include?('[libGLESv2.so.2]')
  abort 'missing actual epoxy dispatch symbols' unless %w[epoxy_eglGetError epoxy_glGetString epoxy_glDrawArrays].all? { |name| elf.match?(/UND\s+#{name}(?:\s|$)/) }
end
abort 'consumer runtime metadata leaks the build sysroot' if elf.include?(sysroot) || elf.include?(work)
inputs = [__FILE__, source, cc, readelf, pkgconfig, executable, "#{work}/consumer-build.log.command"] + modules.map { |name| "#{prefix}/lib/pkgconfig/#{name}.pc" }
File.write("#{work}/inputs.sha256", inputs.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p}\n" }.join)
puts "PASS: #{modules.length} actual pkg-config modules, private metadata and cross-linked #{epoxy ? 'epoxy dispatch' : 'EGL/GLES/GBM'} consumer"
puts 'Static metadata queries do not establish a static Mesa build; execute the consumer on the target separately.'
