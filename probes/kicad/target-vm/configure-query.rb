#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Select explicit target providers for GI execution.
require 'json'
abort 'usage: configure-query.rb WORK BUILD_ROOT SYSROOT READELF NEW_CONFIG' unless ARGV.size == 5
work, build, sysroot, readelf = ARGV.first(4).map { |p| File.realpath(p) }
output = File.expand_path(ARGV.last)
abort 'new absolute config required' unless ARGV.last.start_with?('/') && !File.exist?(output) && !File.symlink?(output)
abort 'private SSH wrapper missing' unless File.executable?(work + '/bin/ssh')
abort 'readelf is not executable' unless File.executable?(readelf)
config = {target: 'aarch64', build_root: build, sysroot: sysroot, cache: work + '/cache',
          readelf: readelf, ssh: 'ember-e14-query', host_key_alias: 'ember-e14-query', library_dirs: []}
File.write(output, JSON.pretty_generate(config) + "\n", mode: 'w', perm: 0600)
puts "Use EMBERBSD_GI_QUERY_CONFIG=#{output} and prepend #{work}/bin to PATH."
