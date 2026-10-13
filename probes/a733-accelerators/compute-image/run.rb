#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors.
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require_relative '../idfwdf/layout'
abort 'usage: run.rb BUILD INPUTS_JSON NEW_OUTPUT' unless ARGV.size == 3
build = File.realpath(ARGV[0])
input_path = File.realpath(ARGV[1])
out = File.expand_path(ARGV[2])
abort 'output already exists' if File.exist?(out)
input = JSON.parse(File.read(input_path))
abort 'BVNC mismatch' unless input['bvnc'] == '36.56.104.183'
abort 'old IDFWDF shader ABI' unless input['idfwdf_layout_dwords'] == 10

def verified_input(entry, base)
  abort 'missing input metadata' unless entry.is_a?(Hash) && entry['path'].is_a?(String) && entry['sha256'].is_a?(String)
  path = File.realpath(File.expand_path(entry['path'], base))
  abort "input hash mismatch: #{path}" unless Digest::SHA256.file(path).hexdigest == entry['sha256']
  path
end
base = File.dirname(input_path)
compiler = verified_input(input.fetch('compiler_manifest'), base)
proof_path = verified_input(input.fetch('compiler_receipt'), base)
proof = Idfwdf.verify_receipt(proof_path, compiler)
generator = JSON.parse(File.read(File.join(build, 'build-manifest.json')))
abort 'shader and host shared headers differ' unless proof.fetch('files').fetch('shared_header').fetch('sha256') == generator.fetch('patched_iface_sha256')
shaders = %w[probe store load idfwdf].map { |name| verified_input(input.fetch('shaders').fetch(name), base) }
expected_shaders = Idfwdf.shaders(File.read(compiler))
%w[probe store load idfwdf].zip(shaders).each do |name, path|
  abort "shader does not match verified compiler output: #{name}" unless File.binread(path) == expected_shaders.fetch(name)
end
FileUtils.mkdir_p(out)
command = [File.join(build, 'generate'), *shaders]
output, status = Open3.capture2e(*command, chdir: out)
File.write(File.join(out, 'run.log'), output)
abort "producer failed (#{status})" unless status.success?
producer = JSON.parse(File.read(File.join(out, 'producer.json')))
files = %w[general.bin pds.bin usc.bin static-state.bin border.bin command.bin]
manifest = {
  schema: 'ember-a733-compute-image-v1',
  status: 'cpu-generated-not-hardware-validated',
  producer: producer,
  inputs_sha256: Digest::SHA256.file(input_path).hexdigest,
  compiler_manifest_sha256: Digest::SHA256.file(compiler).hexdigest,
  compiler_receipt_sha256: Digest::SHA256.file(proof_path).hexdigest,
  shader_inputs: input.fetch('shaders').transform_values { |e| e.reject { |k,_| k == 'path' } },
  source_hashes: JSON.parse(File.read(File.join(build, 'source-hashes.json'))),
  build: JSON.parse(File.read(File.join(build, 'build-manifest.json'))),
  outputs: files.to_h { |name| [name, {size: File.size(File.join(out, name)), sha256: Digest::SHA256.file(File.join(out, name)).hexdigest}] },
  command: {image: 'command.bin', stream_bytes: producer.fetch('command_stream_bytes'), drm_flags: producer.fetch('command_drm_flags')},
  resources: [
    {name:'scratch', image:'general.bin', offset:0, size:4, gpu_va:'0x8000000000', alignment:4096, access:'read-write', slc_bypass:true},
    {name:'resume', image:'general.bin', offset:4096, size:512, gpu_va:'0x8000001000', alignment:64, access:'read-write', slc_bypass:true},
    {name:'idfwdf-texture', image:'general.bin', offset:8192, size:128, gpu_va:'0x8000002000', alignment:4, access:'read-write', slc_bypass:false},
    {name:'idfwdf-shareds', image:'general.bin', offset:12288, size:40, gpu_va:'0x8000003000', alignment:4, access:'read-only', slc_bypass:false},
    {name:'cdm-stream', image:'general.bin', offset:16384, size:producer.fetch('cdm_bytes'), gpu_va:'0x8000004000', alignment:4, access:'read-only', slc_bypass:false},
    {name:'context-state-a', image:'pds.bin', offset:0, size:16432, gpu_va:'0xda00000000', alignment:64, access:'read-write', slc_bypass:false},
    {name:'context-state-b', image:'pds.bin', offset:20480, size:16432, gpu_va:'0xda00005000', alignment:64, access:'read-write', slc_bypass:false},
    {name:'pds-programs', image:'pds.bin', offset:40960, size:File.size(File.join(out,'pds.bin'))-40960, gpu_va:'0xda0000a000', alignment:64, access:'read-only', slc_bypass:false},
    {name:'border-colors', image:'border.bin', offset:0, size:producer.fetch('border_bytes'), gpu_va:producer.fetch('border_va'), alignment:64, access:'read-only', slc_bypass:false},
    {name:'usc-programs', image:'usc.bin', offset:0, size:File.size(File.join(out,'usc.bin')), gpu_va:'0xe000000000', alignment:64, access:'read-only', slc_bypass:false}
  ],
  probe: proof.fetch('probe'),
  lifetime: 'Retain all resources until the GPU owner permits release. Coherent CPU memory does not imply GPU SLC bypass.',
  limitations: ['No DMA, MMU, firmware queue, DRM, or hardware execution.',
                'The dispatch pads to 32 lanes. The compiler SPIR-V proves only instance zero reaches one four-byte store. GPU execution remains unverified.',
                'The emitted command stream uses the exact pinned Mesa profile. Other feature sets and command extensions are rejected.']
}
manifest[:resources].each do |r|
  image_size = manifest[:outputs].fetch(r[:image])[:size]
  abort 'resource exceeds image' unless r[:offset] >= 0 && r[:size] > 0 && r[:offset]+r[:size] <= image_size
  abort 'unaligned GPU resource' unless Integer(r[:gpu_va]) % r[:alignment] == 0
end
File.write(File.join(out,'manifest.json'), JSON.pretty_generate(manifest)+"\n")
puts "CPU image prepared: #{out}"
