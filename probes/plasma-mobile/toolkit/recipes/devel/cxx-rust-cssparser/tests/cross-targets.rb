#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Exercise production make target selection and a declared compiler boundary.
require 'fileutils'
require 'open3'
require 'tmpdir'
root = File.expand_path('..', __dir__)
abort 'FAIL: generic cross recipe is missing' unless File.file?("#{root}/cross.mk")
make = ENV.fetch('BMAKE', 'bmake')
def check(name)
  abort "FAIL: #{name}" unless yield
  puts "PASS: #{name}"
end
Dir.mktmpdir('ember-cssparser-targets-') do |work|
  work = File.realpath(work)
  variables = %w[PKG_FAIL_REASON RUST_TARGET CARGO_ENV _EMBER_CSS_GNU_TRIPLET TOOL_DEPENDS]
  File.write("#{work}/fixture.mk", <<~MK)
    USE_CROSS_COMPILE?=yes
    CROSS_OPSYS=NetBSD
    CROSS_OS_VERSION=11.0
    CROSS_MACHINE_ARCH?=aarch64
    MACHINE_ARCH?=${CROSS_MACHINE_ARCH}
    MACHINE_GNU_PLATFORM?=aarch64--netbsd
    WRKDIR=#{work}/work
    EMBERBSD_CROSS_HOST_PREFIX=#{work}/host
    EMBERBSD_CROSS_BUILD_CC=/usr/bin/cc
    EMBERBSD_CROSS_BUILD_CXX=/usr/bin/c++
    AR=/absolute/cross-ar
    FILESDIR=#{root}
    .include "#{root}/cross.mk"
    show:
    .for key in #{variables.join(' ')}
    \t@printf '%s\\n' ${${key}:Q}
    .endfor
  MK
  query = lambda do |*overrides|
    output, status = Open3.capture2e(make, '-r', '-m', '/', '-f', "#{work}/fixture.mk", 'show', *overrides)
    abort output unless status.success?
    values = output.lines.map(&:chomp)
    abort output unless values.size == variables.size
    variables.zip(values).to_h
  end
  arm = query.call
  check('AArch64 target and host-tool dependency are preserved') { arm['PKG_FAIL_REASON'].empty? && arm['RUST_TARGET'] == 'aarch64-unknown-netbsd' && arm['TOOL_DEPENDS'].include?('rust-std-aarch64-netbsd-1.99.0') }
  amd = query.call('CROSS_MACHINE_ARCH=x86_64', 'MACHINE_ARCH=x86_64', 'MACHINE_GNU_PLATFORM=x86_64--netbsd')
  check('amd64 target selects matching linker and C++ bridge') { amd['PKG_FAIL_REASON'].empty? && amd['RUST_TARGET'] == 'x86_64-unknown-netbsd' && amd['CARGO_ENV'].include?('CARGO_TARGET_X86_64_UNKNOWN_NETBSD_LINKER=') && amd['CARGO_ENV'].include?('CXX_x86_64_unknown_netbsd=') && amd['_EMBER_CSS_GNU_TRIPLET'] == 'x86_64--netbsd' }
  check('amd64 target std uses the common host data package') { amd['TOOL_DEPENDS'].include?('rust-std-x86_64-netbsd-1.99.0') }
  check('foreign architecture fails explicitly') { !query.call('CROSS_MACHINE_ARCH=riscv64')['PKG_FAIL_REASON'].empty? }
  check('mixed GNU toolchain fails explicitly') { !query.call('CROSS_MACHINE_ARCH=x86_64')['PKG_FAIL_REASON'].empty? }
  check('mixed Rust target fails explicitly') { !query.call('RUST_TARGET=x86_64-unknown-netbsd')['PKG_FAIL_REASON'].empty? }
  native = query.call('USE_CROSS_COMPILE=no')
  check('native dependency recursion has no target Cargo settings') { native['RUST_TARGET'].empty? && native['CARGO_ENV'].empty? && native['TOOL_DEPENDS'].empty? }
end
puts 'PASS: actual make cross selection; no Rust build or target execution'
