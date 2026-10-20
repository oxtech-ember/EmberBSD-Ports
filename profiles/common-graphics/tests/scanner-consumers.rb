#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), real Meson consumers of host scanner metadata.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'shellwords'
abort 'usage: scanner-consumers.rb PREPARED_PKGSRC COMMON_MAKECONF LLVM_HELPER SCANNER PATCHED_PROTOCOLS PATCHED_MESA NEW_WORK' unless ARGV.length == 7
tree, common, llvm, scanner, protocols, mesa = ARGV.first(6).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
python, meson, ninja = %w[TEST_PYTHON TEST_MESON NINJA].map { |v| ENV.fetch(v) }
File.write("#{work}/mk.conf", <<~MK)
  .include "#{common}"
  .if defined(BSD_PKG_MK)
  WRKOBJDIR=#{work}/work
  EMBERBSD_COMMON_GRAPHICS_CROSS=yes
  EMBERBSD_GRAPHICS_LLVM_CONFIG=#{llvm}
  EMBERBSD_WAYLAND_SCANNER=#{scanner}
  .include "#{tree}/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
  .endif
MK

def run(log, *command, env: {}, ok: true)
  out, status = Open3.capture2e(env, *command)
  File.write(log, out)
  abort "unexpected exit #{status.exitstatus}: #{log}" unless status.success? == ok
  out
end

def check(name)
  abort "FAIL: #{name}" unless yield
  puts "PASS: #{name}"
end

base = [make, '-C', "#{tree}/devel/wayland-protocols", "MAKECONF=#{work}/mk.conf"]
names = %w[PKG_FAIL_REASON MESON_CROSS_FILE _EMBERBSD_SCANNER_NATIVE TOOLBASE CROSS_DESTDIR MESON_ARGS]
values = run("#{work}/protocols-parse.log", *base, 'show-vars', "VARNAMES=#{names.join(' ')}").lines.map(&:chomp)
abort 'unexpected diagnostic lines' unless values.length == names.length
v = names.zip(values).to_h
check('complete protocols recipe accepts the real scanner installation') { v.fetch('PKG_FAIL_REASON').empty? }
FileUtils.mkdir_p(File.dirname(v.fetch('MESON_CROSS_FILE')))
run("#{work}/production-guard.log", *base, 'emberbsd-scanner-check')
run("#{work}/machine-files.log", *base, v.fetch('MESON_CROSS_FILE'), v.fetch('_EMBERBSD_SCANNER_NATIVE'))
native = File.read(v.fetch('_EMBERBSD_SCANNER_NATIVE'))
cross = File.read(v.fetch('MESON_CROSS_FILE'))
check('production machine files separate host metadata and the cross scanner binding') do
  native.include?("PKG_CONFIG_SYSROOT_DIR=") && native.include?(File.dirname(File.dirname(scanner)) + '/lib/pkgconfig') && cross.include?("wayland-scanner = '#{scanner}'")
end

swaylock_base = [make, '-C', "#{tree}/wayland/swaylock", "MAKECONF=#{work}/mk.conf"]
swaylock_names = %w[PKG_FAIL_REASON MESON_BINARIES MESON_BINARY.wayland-scanner MESON_NATIVE_ARGS]
swaylock_values = run("#{work}/swaylock-parse.log", *swaylock_base, 'show-vars', "VARNAMES=#{swaylock_names.join(' ')}").lines.map(&:chomp)
abort 'unexpected Swaylock diagnostic lines' unless swaylock_values.length == swaylock_names.length
swaylock = swaylock_names.zip(swaylock_values).to_h
check('Swaylock selects the validated host scanner and its native metadata') do
  swaylock.fetch('PKG_FAIL_REASON').empty? &&
    swaylock.fetch('MESON_BINARIES').split.include?('wayland-scanner') &&
    swaylock.fetch('MESON_BINARY.wayland-scanner') == scanner &&
    swaylock.fetch('MESON_NATIVE_ARGS').include?('--native-file')
end
run("#{work}/swaylock-scanner-guard.log", *swaylock_base, 'emberbsd-scanner-check')
native_swaylock = run("#{work}/swaylock-native-parse.log", *swaylock_base, 'USE_CROSS_COMPILE=no',
  'show-vars', 'VARNAMES=MESON_BINARIES MESON_BINARY.wayland-scanner').lines.map(&:chomp)
check('native Swaylock does not inherit the cross scanner binding') do
  native_swaylock.length == 2 && native_swaylock.all?(&:empty?)
end

FileUtils.mkdir_p("#{work}/empty-pc")
env = {'PKG_CONFIG' => "#{v.fetch('TOOLBASE')}/bin/pkg-config", 'PKG_CONFIG_FOR_BUILD' => "#{v.fetch('TOOLBASE')}/bin/pkg-config", 'PKG_CONFIG_PATH' => '', 'PKG_CONFIG_PATH_FOR_BUILD' => '', 'PKG_CONFIG_LIBDIR' => "#{work}/empty-pc", 'PKG_CONFIG_SYSROOT_DIR' => v.fetch('CROSS_DESTDIR'), 'CMAKE' => '/usr/bin/false', 'CMAKE_FOR_BUILD' => '/usr/bin/false'}
common_args = ['--cross-file', v.fetch('MESON_CROSS_FILE'), '--prefix=/usr/pkg', '--wrap-mode=nodownload', *Shellwords.split(v.fetch('MESON_ARGS'))]
run("#{work}/red-no-native-metadata.log", python, meson, 'setup', "#{work}/red", protocols, *common_args, env: env)
red = JSON.parse(run("#{work}/red-install.json", python, meson, 'introspect', '--installed', "#{work}/red"))
check('upstream control silently omits enum headers without native scanner metadata') { red.values.none? { |p| p.include?('/include/wayland-protocols/') } }
run("#{work}/green-configure.log", python, meson, 'setup', "#{work}/green", protocols, *common_args, '--native-file', v.fetch('_EMBERBSD_SCANNER_NATIVE'), env: env)
run("#{work}/green-generate.log", ninja, '-C', "#{work}/green", '-j2')
installed = JSON.parse(run("#{work}/green-install.json", python, meson, 'introspect', '--installed', "#{work}/green"))
actual = installed.values.select { |p| p.start_with?('/usr/pkg/include/wayland-protocols/') }.map { |p| p.delete_prefix('/usr/pkg/') }.sort
expected = File.readlines("#{tree}/devel/wayland-protocols/PLIST", chomp: true).grep(/^include\/wayland-protocols\//).sort
check('real scanner generates every protocol header required by the package PLIST') { !expected.empty? && actual == expected && installed.select { |_, p| p.include?('/include/wayland-protocols/') }.keys.all? { |p| File.file?(p) } }

mesa_base = [make, '-C', "#{tree}/graphics/MesaLib", "MAKECONF=#{work}/mk.conf"]
mesa_vars = run("#{work}/mesa-parse.log", *mesa_base, 'show-vars', 'VARNAMES=PKG_FAIL_REASON MESON_CROSS_FILE _EMBERBSD_SCANNER_NATIVE BUILDLINK_API_DEPENDS.wayland BUILDLINK_API_DEPENDS.wayland-protocols').lines.map(&:chomp)
check('complete Mesa recipe selects current Wayland and protocol floors') { mesa_vars.length == 5 && mesa_vars[0].empty? && mesa_vars[3].include?('wayland>=1.26.0nb1') && mesa_vars[4].include?('wayland-protocols>=1.49') }
FileUtils.mkdir_p(File.dirname(mesa_vars[1]))
run("#{work}/mesa-machine-files.log", *mesa_base, mesa_vars[1], mesa_vars[2], 'emberbsd-scanner-check')
FileUtils.mkdir_p("#{work}/mesa-consumer")
FileUtils.cp("#{mesa}/src/egl/wayland/wayland-drm/wayland-drm.xml", "#{work}/mesa-consumer/wayland-drm.xml")
import_line = File.readlines("#{mesa}/meson.build").find { |l| l.include?("mod_wl = import('unstable-wayland')") }
scan_line = File.readlines("#{mesa}/src/egl/wayland/wayland-drm/meson.build").find { |l| l.start_with?('_wl_drm = mod_wl.scan_xml(') }
abort 'upstream Mesa Wayland module context changed' unless import_line && scan_line
File.write("#{work}/mesa-consumer/meson.build", "project('mesa-scanner-contract')\n" + import_line + scan_line)
target_env = env.merge('PKG_CONFIG_LIBDIR' => "#{v.fetch('CROSS_DESTDIR')}/usr/pkg/lib/pkgconfig")
run("#{work}/mesa-module-configure.log", python, meson, 'setup', "#{work}/mesa-module-build", "#{work}/mesa-consumer", '--cross-file', mesa_vars[1], '--native-file', mesa_vars[2], '--wrap-mode=nodownload', env: target_env)
run("#{work}/mesa-module-generate.log", ninja, '-C', "#{work}/mesa-module-build", '-j2', 'wayland-drm-protocol.c', 'wayland-drm-client-protocol.h', 'wayland-drm-server-protocol.h')
check('actual Mesa Wayland module scans with the selected host executable') do
  File.read("#{work}/mesa-module-build/build.ninja").include?(scanner) && File.read("#{work}/mesa-module-build/wayland-drm-protocol.c").include?('wl_drm_interface')
end

# Clone real installed outputs; never replace successful scanner query answers.
original_prefix = File.dirname(File.dirname(scanner))
%w[changed-executable wrong-metadata].each do |kind|
  clone = "#{work}/#{kind}"
  FileUtils.mkdir_p(clone)
  FileUtils.cp_r(original_prefix, "#{clone}/prefix")
  FileUtils.cp("#{File.dirname(original_prefix)}/installed.sha256", "#{clone}/installed.sha256")
  if kind == 'changed-executable'
    File.open("#{clone}/prefix/bin/wayland-scanner", 'a') { |f| f.puts('changed executable') }
  else
    pc = "#{clone}/prefix/lib/pkgconfig/wayland-scanner.pc"
    File.write(pc, File.read(pc).sub('Version: 1.26.0', 'Version: 1.25.0'))
    # Keep the receipt internally consistent so only the semantic guard fails.
    lines = Dir.glob("#{clone}/prefix/**/*", File::FNM_DOTMATCH).select { |p| File.file?(p) }.map { |p| "#{Digest::SHA256.file(p).hexdigest}  ./#{p.delete_prefix(clone + '/prefix/')}\n" }
    File.write("#{clone}/installed.sha256", lines.join)
  end
  out = run("#{work}/#{kind}.log", *base, "EMBERBSD_WAYLAND_SCANNER=#{clone}/prefix/bin/wayland-scanner", 'emberbsd-scanner-check', ok: false)
  expected_error = kind == 'changed-executable' ? 'Wayland scanner receipt mismatch:' : 'Wayland scanner native metadata disagrees'
  check("production consumer rejects #{kind}") { out.include?(expected_error) }
end
puts 'PASS: source-causal native metadata selection and real protocol generation; no target library was built or installed'
