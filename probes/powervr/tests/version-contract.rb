#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors.
require "digest"
require "fileutils"
require "json"
require "open3"
require "tmpdir"
abort "usage: version-contract.rb GENERATOR INPUTS_JSON" unless ARGV.size == 2
build, input_path = ARGV.map { |p| File.realpath(p) }
input = JSON.parse(File.read(input_path))
receipt_path = File.realpath(input.fetch("compiler_receipt").fetch("path"))
runner = File.expand_path("../compute-image/run.rb", __dir__)
Dir.mktmpdir("powervr-version-") do |dir|
  receipt = JSON.parse(File.read(receipt_path))
  generator = JSON.parse(File.read(File.join(build, "build-manifest.json")))
  raise "fixture must share its valid header" unless receipt.fetch("files").fetch("shared_header").fetch("sha256") == generator.fetch("patched_iface_sha256")
  receipt["mesa_version"] = "26.2.5"
  old_path = File.join(dir, "receipt.json")
  File.write(old_path, JSON.generate(receipt))
  input["compiler_receipt"] = { "path" => old_path, "sha256" => Digest::SHA256.file(old_path).hexdigest }
  old_input = File.join(dir, "inputs.json")
  File.write(old_input, JSON.generate(input))
  output, status = Open3.capture2e(RbConfig.ruby, runner, build, old_input, File.join(dir, "old-output"))
  raise "old compiler receipt accepted: #{output}" if status.success?
  raise "wrong rejection: #{output}" unless output.include?("Mesa version")
  raise "rejected output created" if File.exist?(File.join(dir, "old-output"))

  changed_build = File.join(dir, "build")
  Dir.mkdir(changed_build)
  generator["mesa_version"] = "26.2.5"
  File.write(File.join(changed_build, "build-manifest.json"), JSON.generate(generator))
  File.symlink(File.join(build, "generate"), File.join(changed_build, "generate"))
  output, status = Open3.capture2e(RbConfig.ruby, runner, changed_build, input_path, File.join(dir, "mismatch-output"))
  raise "mismatched generator accepted: #{output}" if status.success?
  raise "wrong rejection: #{output}" unless output.include?("Mesa version")
  raise "rejected output created" if File.exist?(File.join(dir, "mismatch-output"))
end
puts "Mesa receipt and generator version mismatches rejected"
