#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Parse production Makefile/profile statements with external pkgsrc includes
# omitted at the declared host metadata boundary. Do not configure Mesa.
require 'fileutils'
require 'open3'
require 'tmpdir'

root = File.expand_path('..', __dir__)
make = ENV.fetch('BMAKE', 'bmake')
def check(name)
  abort "FAIL: #{name}" unless yield
  puts "PASS: #{name}"
end
Dir.mktmpdir('ember-graphics-amd64-') do |work|
  work = File.realpath(work)
  File.write("#{work}/profile.mk", File.read("#{root}/mk.conf"))
  %w[EMBERBSD-COMMON-GRAPHICS-SOURCES EMBERBSD-COMMON-TOOLS-MK.CONF inputs.sha256 receipt.json llvm-config scanner].each { |name| File.write("#{work}/#{name}", '') }
  FileUtils.mkdir_p("#{work}/helper/bin")
  FileUtils.cp("#{work}/llvm-config", "#{work}/helper/bin/llvm-config")
  %w[inputs.sha256 receipt.json].each { |name| FileUtils.cp("#{work}/#{name}", "#{work}/helper/#{name}") }
  recipes = {'mesa' => 'graphics/MesaLib', 'drm' => 'x11/libdrm'}
  recipes.each do |name, path|
    text = File.readlines("#{root}/../../pkgsrc/#{path}/Makefile").reject { |line| line.start_with?('.include') }.join
    File.write("#{work}/#{name}.mk", text)
  end
  vars = %w[PKG_FAIL_REASON ONLY_FOR_PLATFORM MESON_ARGS PLIST.intel PLIST.v3d _EMBERBSD_MESA_LLVM_TRIPLE EMBERBSD_COMMON_GRAPHICS OPSYS]
  File.write("#{work}/fixture.mk", <<~MK)
    BSD_PKG_MK=1
    OPSYS=NetBSD
    OS_VERSION=11.0
    MACHINE_ARCH?=aarch64
    CROSS_MACHINE_ARCH?=${MACHINE_ARCH}
    CROSS_OPSYS=NetBSD
    USE_CROSS_COMPILE?=yes
    EMBERBSD_COMMON_GRAPHICS_CROSS=yes
    EMBERBSD_CROSS_TOOLS=#{work}
    TOOLDIR=#{work}
    EMBERBSD_CROSS_SYSROOT=#{work}
    CROSS_DESTDIR=#{work}
    EMBERBSD_CROSS_HOST_PREFIX=#{work}
    CROSS_LOCALBASE=/usr/pkg
    PKGSRC_COMPILER=gcc
    USE_NATIVE_GCC=yes
    USE_PKGSRC_GCC=no
    USE_PKGSRC_GCC_RUNTIME=no
    PKGPATH?=graphics/MesaLib
    PKG_OPTIONS=llvm x11 wayland
    DISTNAME=mesa-26.2.5
    EMBERBSD_GRAPHICS_LLVM_CONFIG=#{work}/helper/bin/llvm-config
    EMBERBSD_WAYLAND_SCANNER=#{work}/scanner
    .include "#{work}/profile.mk"
    .include "#{work}/${RECIPE:Umesa}.mk"
    show:
    .for key in #{vars.join(' ')}
    \t@printf '%s\\n' ${${key}:Q}
    .endfor
  MK
  query = lambda do |*args|
    output, status = Open3.capture2e(make, '-r', '-m', '/', '-f', "#{work}/fixture.mk", 'show', *args)
    abort output unless status.success?
    lines = output.lines.map(&:chomp)
    abort output unless lines.size == vars.size
    vars.zip(lines).to_h
  end
  arm = query.call
  check('AArch64 default retains V3D and no Intel module') { arm['PKG_FAIL_REASON'].empty? && arm['MESON_ARGS'].include?('-Dgallium-drivers=v3d,virgl,softpipe,llvmpipe,zink') && !arm['MESON_ARGS'].include?('iris') }
  amd = query.call('MACHINE_ARCH=x86_64')
  check('amd64 Mesa parses with Iris, VirGL and llvmpipe') { amd['PKG_FAIL_REASON'].empty? && amd['MESON_ARGS'].include?('-Dgallium-drivers=iris,virgl,softpipe,llvmpipe,zink') && amd['_EMBERBSD_MESA_LLVM_TRIPLE'] == 'x86_64-unknown-netbsd' && amd['MESON_ARGS'].include?('-Dmesa-clc=system') && amd['MESON_ARGS'].include?('-Dprecomp-compiler=system') }
  check('Mesa platform selection is exactly the two NetBSD11 targets') { amd['ONLY_FOR_PLATFORM'].split.sort == %w[NetBSD-11.*-aarch64 NetBSD-11.*-x86_64] }
  mixed = query.call('MACHINE_ARCH=x86_64', 'CROSS_MACHINE_ARCH=aarch64')
  check('mixed profile target is rejected') { !mixed['PKG_FAIL_REASON'].empty? }
  foreign = query.call('MACHINE_ARCH=riscv64')
  check('foreign graphics target is rejected') { !foreign['PKG_FAIL_REASON'].empty? }
  host = query.call('OPSYS=Darwin', 'MACHINE_ARCH=arm64', 'USE_CROSS_COMPILE=no')
  check('recursive host dependency retains Darwin and no graphics profile') { host['EMBERBSD_COMMON_GRAPHICS'].empty? && host['OPSYS'] == 'Darwin' }
  drm_arm = query.call('PKGPATH=x11/libdrm', 'RECIPE=drm', 'DISTNAME=libdrm-2.4.134', 'PKGREVISION=4')
  drm_amd = query.call('MACHINE_ARCH=x86_64', 'PKGPATH=x11/libdrm', 'RECIPE=drm', 'DISTNAME=libdrm-2.4.134', 'PKGREVISION=4')
  check('AArch64 libdrm keeps Intel disabled') { drm_arm['PKG_FAIL_REASON'].empty? && drm_arm['MESON_ARGS'].include?('-Dintel=disabled') && drm_arm['PLIST.intel'].empty? }
  check('amd64 libdrm selects its own Intel module and payload') { drm_amd['PKG_FAIL_REASON'].empty? && drm_amd['MESON_ARGS'].include?('-Dintel=enabled') && drm_amd['PLIST.intel'] == 'yes' }
  mesa_plist = File.readlines("#{root}/../../pkgsrc/graphics/MesaLib/PLIST", chomp: true)
  check('architecture-specific Mesa driver defaults follow their DRI payload') do
    %w[lib/dri/iris_dri.so share/drirc.d/00-iris-defaults.conf].all? { |name| mesa_plist.include?('${PLIST.intel}' + name) && !mesa_plist.include?(name) } &&
      %w[lib/dri/v3d_dri.so share/drirc.d/00-v3d-defaults.conf].all? { |name| mesa_plist.include?('${PLIST.v3d}' + name) && !mesa_plist.include?(name) }
  end
end
puts 'PASS: production graphics/Mesa/libdrm make guards; no package build or hardware acceptance'
