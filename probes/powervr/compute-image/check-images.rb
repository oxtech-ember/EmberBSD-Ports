#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors.
# Validate the CPU-produced bounded profiles, not GPU execution.
require "digest"
require "json"
abort "usage: check-images.rb GE_DIR BXM_DIR" unless ARGV.size == 2
profiles = [[ARGV[0], "22.102.54.38", 36], [ARGV[1], "36.56.104.183", 44]]
profiles.each do |dir, bvnc, main_length|
  manifest = JSON.parse(File.read(File.join(dir, "manifest.json")))
  producer = manifest.fetch("producer")
  abort "wrong profile" unless producer.fetch("bvnc") == bvnc && !producer.fetch("hardware_validated")
  manifest.fetch("outputs").each do |name, record|
    bytes = File.binread(File.join(dir, name))
    abort "output mismatch: #{name}" unless bytes.bytesize == record.fetch("size") && Digest::SHA256.hexdigest(bytes) == record.fetch("sha256")
  end
  command = File.binread(File.join(dir, "command.bin"))
  abort "wrong command size" unless command.bytesize == 48
  words = command.unpack("V12")
  abort "wrong main stream length" unless words[0] == main_length && words[1] == 0
  abort "wrong flags" unless words[11] == 0
  if main_length == 36
    abort "wrong BRN49927 extension" unless words[9, 2] == [1, 0x20]
  end
  resources = manifest.fetch("resources").to_h { |r| [r.fetch("name"), r] }
  abort "wrong resource count" unless resources.size == 10
  scratch = resources.fetch("scratch")
  abort "wrong canary mapping" unless scratch.fetch("gpu_va") == "0x8000000000" && scratch.fetch("size") == 4 && scratch.fetch("slc_bypass")
  abort "wrong USC heap" unless resources.fetch("usc-programs").fetch("gpu_va") == "0xe000000000"
  abort "wrong border table" unless resources.fetch("border-colors").fetch("size") == 262144
end
puts "GE and BXM CPU image contracts passed; GPU execution not tested"
