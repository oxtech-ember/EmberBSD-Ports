#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted). Parse actual pkgsrc recipes.
require 'fileutils'
require 'open3'
abort 'usage: powervr-selection.rb PREPARED_PKGSRC COMMON_MAKECONF LLVM_HELPER HOST_SCANNER SEALED_GENERATORS ABI_SOURCE NEW_WORK' unless ARGV.size == 7
tree, common, llvm, scanner, generators, source = ARGV.first(6).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
abort 'Use a new absolute work directory' unless ARGV.last.start_with?('/') && !File.exist?(work)
FileUtils.mkdir_p(work)
make = ENV.fetch('BMAKE', 'bmake')
digest = ENV.fetch('DIGEST')
File.write(work + '/mk.conf', <<~MK)
.include "#{common}"
.if defined(BSD_PKG_MK)
WRKOBJDIR=#{work}/work
EMBERBSD_COMMON_GRAPHICS_CROSS=yes
EMBERBSD_GRAPHICS_LLVM_CONFIG=#{llvm}
EMBERBSD_WAYLAND_SCANNER=#{scanner}
EMBERBSD_MESA_GENERATORS=#{generators}
.include "#{tree}/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
.endif
MK
base = [make, '-C', tree + '/graphics/MesaLib', 'MAKECONF=' + work + '/mk.conf']
run = lambda do |name, *args, valid: true|
    out, status = Open3.capture2e(*base, *args)
    File.write(work + '/' + name + '.log', out)
    abort "Unexpected result: #{name}" unless status.success? == valid
    out
end
check = lambda { |condition, message| abort "FAIL: #{message}" unless condition; puts "PASS: #{message}" }
vars = %w[PKG_FAIL_REASON PKGNAME PKG_OPTIONS MESON_ARGS MESON_NATIVE_ARGS _EMBERBSD_MESA_NATIVE PLIST.powervr]
query = lambda do |name, options, *overrides|
    text = run.call(name, 'show-vars', 'VARNAMES=' + vars.join(' '), 'PKG_OPTIONS.MesaLib=' + options, *overrides)
    lines = text.lines.map(&:chomp)
    abort "Unexpected recipe diagnostics: #{name}" unless lines.size == vars.size
    vars.zip(lines).to_h
end
plain = query.call('plain', 'llvm x11 wayland', 'EMBERBSD_MESA_GENERATORS=/missing')
check.call(plain.fetch('PKG_FAIL_REASON').empty? && !plain.fetch('MESON_ARGS').include?('vulkan-drivers=imagination') && plain.fetch('PLIST.powervr').empty?, 'default GL recipe does not require PowerVR tools')
pvr = query.call('powervr', 'llvm x11 wayland powervr')
check.call(pvr.fetch('PKG_FAIL_REASON').empty? && pvr.fetch('PKGNAME') == 'MesaLib-26.2.4nb5', 'PowerVR is an ordinary MesaLib package option')
%w[-Dgallium-drivers=v3d,virgl,softpipe,llvmpipe -Dplatforms=x11,wayland -Dllvm=enabled -Dshared-llvm=enabled -Dvulkan-drivers=imagination -Dmesa-clc=system -Dprecomp-compiler=system -Dimagination-srv=false].each do |option|
    check.call(pvr.fetch('MESON_ARGS').split.include?(option), "keeps #{option}")
end
check.call(pvr.fetch('PLIST.powervr') == 'yes', 'PowerVR adds its normal PLIST payload')
# Upstream installs driver defaults as well as the ICD and its manifest.
payload = %w[lib/libvulkan_powervr_mesa.so share/drirc.d/00-pvr-defaults.conf share/vulkan/icd.d/powervr_mesa_icd.json]
plist = File.readlines(tree + '/graphics/MesaLib/PLIST', chomp: true)
complete = lambda { |lines| payload.all? { |path| lines.include?('${PLIST.powervr}' + path) && !lines.include?(path) } }
check.call(complete.call(plist), 'all three PowerVR files have conditional package ownership')
missing_defaults = plist.reject { |line| line == '${PLIST.powervr}share/drirc.d/00-pvr-defaults.conf' }
check.call(!complete.call(missing_defaults), 'causal missing driver defaults fails the payload oracle')
native = pvr.fetch('_EMBERBSD_MESA_NATIVE')
FileUtils.mkdir_p(File.dirname(native))
run.call('native-file', native, 'PKG_OPTIONS.MesaLib=llvm x11 wayland powervr')
%w[mesa_clc vtn_bindgen2 pco_clc].each do |name|
    check.call(File.read(native).include?("#{name} = '#{generators}/bin/#{name}'"), "native Meson file binds #{name}")
end
run.call('actual-check', 'emberbsd-mesa-generators-check', 'PKG_OPTIONS.MesaLib=llvm x11 wayland powervr', 'WRKSRC=' + source, 'TOOLS_DIGEST=' + digest)
invalid = query.call('missing-tools', 'llvm x11 wayland powervr', 'EMBERBSD_MESA_GENERATORS=/missing')
check.call(invalid.fetch('PKG_FAIL_REASON').include?('sealed EMBERBSD_MESA_GENERATORS'), 'missing native tools fail package selection')
# A causal prior recipe lacks the Vulkan option and cannot satisfy this oracle.
recipe = File.read(tree + '/graphics/MesaLib/Makefile')
old = work + '/Makefile-old'
File.write(old, recipe.sub('-Dvulkan-drivers=imagination', '-Dvulkan-drivers='))
text = run.call('disabled-icd-control', '-f', old, 'show-var', 'VARNAME=MESON_ARGS', 'PKG_OPTIONS.MesaLib=llvm x11 wayland powervr')
check.call(!text.split.include?('-Dvulkan-drivers=imagination'), 'causal disabled-ICD control fails the feature oracle')
puts 'PASS: real pkgsrc selection, native file, production receipt check and causal disabled-ICD control'
