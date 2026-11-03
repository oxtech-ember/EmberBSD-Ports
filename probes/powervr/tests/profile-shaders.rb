#!/usr/bin/env ruby
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EmberBSD contributors.
require_relative "../idfwdf/layout"
base = Idfwdf::SHADER_NAMES
symbols = base.values + ["cs_probe_store_0_bvnc_22_102_54_38"]
table = symbols.each_with_index.map { |symbol, i| "static const uint32_t #{symbol}[1] = { 0x#{(i+1).to_s(16)} };" }.join("\n")
raise "BXM probe" unless Idfwdf.shaders(table).fetch("probe") == [1].pack("V")
ge = Idfwdf.shaders(table, "22.102.54.38")
raise "GE probe" unless ge.fetch("probe") == [5].pack("V")
raise "common helper" unless ge.fetch("store") == [2].pack("V")
begin
  Idfwdf.shaders(table, "22.102.54.39")
  raise "unknown profile accepted"
rescue ArgumentError
end
raise "BXM compiler args" unless Idfwdf.compiler_bvnc_args("36.56.104.183") == []
raise "GE compiler args" unless Idfwdf.compiler_bvnc_args("22.102.54.38") == ["bvnc=22.102.54.38"]
raise "legacy BXM receipt" unless Idfwdf.receipt_bvnc({}) == "36.56.104.183"
raise "GE receipt" unless Idfwdf.receipt_bvnc({"bvnc" => "22.102.54.38"}) == "22.102.54.38"
begin
  Idfwdf.receipt_bvnc({"bvnc" => "22.102.54.38"}, "36.56.104.183")
  raise "mismatch accepted"
rescue ArgumentError
end
puts "profile shader selection passed"
