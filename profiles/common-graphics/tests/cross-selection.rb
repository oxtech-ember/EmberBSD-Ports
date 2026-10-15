#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Parse actual pkgsrc recipes with real cross tools.
require 'fileutils'
require 'open3'
require 'shellwords'
abort 'usage: cross-selection.rb PREPARED_PKGSRC COMMON_CROSS_MAKECONF LLVM_HELPER HOST_SCANNER NEW_WORK' unless ARGV.length == 5
tree, common, helper, scanner = ARGV.first(4).map { |p| File.realpath(p) }
work = File.expand_path(ARGV.last)
Dir.mkdir(work)
make = ENV.fetch('BMAKE', 'bmake')
File.write("#{work}/mk.conf", <<~MK)
  .include "#{common}"
  .if defined(BSD_PKG_MK)
  WRKOBJDIR=#{work}/work
  EMBERBSD_COMMON_GRAPHICS_CROSS=yes
  EMBERBSD_GRAPHICS_LLVM_CONFIG=#{helper}
  EMBERBSD_WAYLAND_SCANNER=#{scanner}
  .include "#{tree}/EMBERBSD-COMMON-GRAPHICS-MK.CONF"
  .endif
MK

def run(log, *command, ok: true)
  out, status = Open3.capture2e(*command)
  File.write(log, out)
  abort "unexpected command status #{status.exitstatus}: #{log}" unless status.success? == ok
  out
end

def check(name)
  abort "FAIL: #{name}" unless yield
  puts "PASS: #{name}"
end

base = [make, '-C', "#{tree}/graphics/MesaLib", "MAKECONF=#{work}/mk.conf"]
vars = %w[PKG_FAIL_REASON PREFIX LOCALBASE TOOLBASE TOOL_PYTHONBIN PYTHONBIN LLVM_CONFIG_PATH MESON_BINARY.llvm-config SUBST_SED.python MESON_CROSS_FILE MESON_BINARY.c MESON_BINARY.cpp TOOLS_DIGEST CROSS_MACHINE_ARCH]
values = run("#{work}/mesa.log", *base, 'show-vars', "VARNAMES=#{vars.join(' ')}").lines.map(&:chomp)
abort 'unexpected diagnostic lines in real pkgsrc parse; inspect mesa.log' unless values.length == vars.length
v = vars.zip(values).to_h
check('cross Mesa full recipe parses without package failure') { v['PKG_FAIL_REASON'].empty? }
check('target prefix remains /usr/pkg and Python runs from host TOOLBASE') do
  v['PREFIX'] == '/usr/pkg' && v['LOCALBASE'] == '/usr/pkg' && v['PYTHONBIN'] == '/usr/pkg/bin/python3.14' && v['TOOL_PYTHONBIN'] == "#{v['TOOLBASE']}/bin/python3.14" && v['SUBST_SED.python'].include?(v['TOOL_PYTHONBIN'])
end
check('Mesa uses the explicit real LLVM metadata helper') { v['LLVM_CONFIG_PATH'] == helper && v['MESON_BINARY.llvm-config'] == helper }
# pkgsrc reuses MAKECONF with USE_CROSS_COMPILE=no for tool dependencies,
# including their own native dependencies. They must retain the host profile.
%w[devel/py-mako textproc/py-markupsafe].each do |package|
  host_vars = %w[PKG_FAIL_REASON OPSYS LOCALBASE PKGSRC_COMPILER EMBERBSD_COMMON_GRAPHICS LLVM_CONFIG_PATH]
  host_values = run("#{work}/#{File.basename(package)}-native.log", make, '-C', "#{tree}/#{package}", "MAKECONF=#{work}/mk.conf", 'USE_CROSS_COMPILE=no', 'show-vars', "VARNAMES=#{host_vars.join(' ')}").lines.map(&:chomp)
  abort 'unexpected native dependency diagnostic lines' unless host_values.length == host_vars.length
  h = host_vars.zip(host_values).to_h
  check("#{package} native dependency retains macOS host configuration") do
    h['PKG_FAIL_REASON'].empty? && h['OPSYS'] == 'Darwin' && h['LOCALBASE'] == v['TOOLBASE'] && h['PKGSRC_COMPILER'] == 'clang' && h['EMBERBSD_COMMON_GRAPHICS'].empty? && h['LLVM_CONFIG_PATH'].empty?
  end
end
# Execute the actual pkgsrc cross-file target, not a handwritten stand-in.
FileUtils.mkdir_p(File.dirname(v.fetch('MESON_CROSS_FILE')))
run("#{work}/cross-file.log", *base, v.fetch('MESON_CROSS_FILE'))
cross_file = File.read(v.fetch('MESON_CROSS_FILE'))
check('actual Meson cross file binds LLVM metadata to the selected NetBSD target') do
  %w[aarch64 x86_64].include?(v['CROSS_MACHINE_ARCH']) && cross_file.include?("system = 'netbsd'") && cross_file.include?("cpu_family = '#{v.fetch('CROSS_MACHINE_ARCH')}'") && cross_file.include?("llvm-config = '#{helper}'")
end
# These are real recipe/profile refusals; no llvm-config responses are invented.
{
  'opt-in' => ['EMBERBSD_COMMON_GRAPHICS_CROSS=no', 'requires EMBERBSD_COMMON_GRAPHICS_CROSS=yes'],
  'unreceipted-helper' => ['EMBERBSD_GRAPHICS_LLVM_CONFIG=/usr/bin/false', 'receipt-guarded llvm-config'],
  'overridden-llvm' => ['LLVM_CONFIG_PATH=/usr/bin/false', 'overridden LLVM_CONFIG_PATH'],
  'target-prefix' => ['CROSS_LOCALBASE=/opt/mesa', 'one final /usr/pkg prefix'],
  'host-python' => ['TOOL_PYTHONBIN=/usr/bin/false', 'canonical build-host Python'],
  'base-x11' => ['X11_TYPE=native', 'requires modular target X11']
}.each do |name, (override, expected)|
  out = run("#{work}/#{name}.log", *base, 'show-var', 'VARNAME=PKG_FAIL_REASON', override)
  check("rejects #{name}") { out.include?(expected) }
end

libdrm = [make, '-C', "#{tree}/x11/libdrm", "MAKECONF=#{work}/mk.conf"]
drm_vars = %w[PKG_FAIL_REASON MESON_BINARY.python REPLACE.tool-python.new MESON_CROSS_FILE]
drm_values = run("#{work}/libdrm.log", *libdrm, 'show-vars', "VARNAMES=#{drm_vars.join(' ')}").lines.map(&:chomp)
abort 'unexpected libdrm diagnostic lines' unless drm_values.length == drm_vars.length
d = drm_vars.zip(drm_values).to_h
check('libdrm full recipe uses host Python for Meson and build scripts') { d['PKG_FAIL_REASON'].empty? && d['MESON_BINARY.python'] == v['TOOL_PYTHONBIN'] && d['REPLACE.tool-python.new'] == v['TOOL_PYTHONBIN'] }
FileUtils.mkdir_p(File.dirname(d.fetch('MESON_CROSS_FILE')))
run("#{work}/drm-cross-file.log", *libdrm, d.fetch('MESON_CROSS_FILE'))
check('libdrm actual cross file contains the host Python path') { File.read(d.fetch('MESON_CROSS_FILE')).include?("python = '#{v['TOOL_PYTHONBIN']}'") }

# Run the exact production receipt-verification commands, without unrelated
# Python imports or later shared-library readiness checks masking the cause.
recipe = File.read("#{tree}/graphics/MesaLib/Makefile")
guard = recipe[/^\tcd \$\{LLVM_CONFIG_PATH:H:H:Q\} && \\\n.*?^\tdone < inputs.sha256\n/m]
abort 'missing production receipt verifier' unless guard
clone = "#{work}/changed-helper"
FileUtils.cp_r(File.dirname(File.dirname(helper)), clone)
File.open("#{clone}/bin/llvm-config.real", 'a') { |f| f.puts('changed executable') }
File.write("#{work}/guard.mk", "TEST=test\nTOOLS_DIGEST=#{v.fetch('TOOLS_DIGEST')}\nLLVM_CONFIG_PATH=#{helper}\nverify:\n" + guard)
run("#{work}/receipt-positive.log", make, '-r', '-m', '/', '-f', "#{work}/guard.mk", 'verify')
out = run("#{work}/receipt-negative.log", make, '-r', '-m', '/', '-f', "#{work}/guard.mk", 'verify', "LLVM_CONFIG_PATH=#{clone}/bin/llvm-config", ok: false)
check('production recipe rejects a modified helper executable before invoking it') { out.include?('LLVM helper receipt mismatch: bin/llvm-config.real') }
puts 'PASS: actual pkgsrc parsing, generated machine files and receipt guard; complete Mesa configuration/build still requires staged LLVM and target dependencies'
