#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Exercise the real PNG decoder and content gate.
require 'open3'
require 'zlib'
require 'tmpdir'
require 'shellwords'
abort 'Usage: capture-pixels-test.rb OUTPUT' unless ARGV.length == 1
output=File.expand_path(ARGV[0]); Dir.mkdir(output)
command=[ENV.fetch('CC','cc'), '-std=c11', '-Wall', '-Wextra', '-Werror', *Shellwords.split(ENV.fetch('CPPFLAGS','')), *Shellwords.split(ENV.fetch('CFLAGS','')), File.join(__dir__,'capture-pixels.c'), *Shellwords.split(ENV.fetch('LDFLAGS','')), '-lpng', '-o', File.join(output,'check')]
out,err,status=Open3.capture3(*command); abort(out+err) unless status.success?
File.write(File.join(output,'build-command.txt'), Shellwords.join(command)+"\n")
def chunk(name,data)
  [data.bytesize].pack('N')+name+data+[Zlib.crc32(name+data)].pack('N')
end
def png(width,height,kind)
  raw=''.b
  height.times do |y|
    raw << "\0"
    width.times do |x|
      rgb=kind==:varied ? (x < width/2 ? [240,50,40] : [10,200,240]) : [0,0,0]
      raw << (rgb+[kind==:transparent ? 0 : 255]).pack('C4')
    end
  end
  "\x89PNG\r\n\x1a\n".b+chunk('IHDR',[width,height,8,6,0,0,0].pack('NNC5'))+chunk('IDAT',Zlib::Deflate.deflate(raw))+chunk('IEND','')
end
valid=png(320,256,:varied)
cases={valid: [valid,true], transparent: [png(320,256,:transparent),false], black: [png(320,256,:black),false], dimensions: [png(319,256,:varied),false], truncated: [valid[0,24],false], corrupt: [valid.dup,false]}
cases[:corrupt][0].setbyte(45,cases[:corrupt][0].getbyte(45)^1)
cases.each do |name,(bytes,expected)|
  path=File.join(output,"#{name}.png"); File.binwrite(path,bytes)
  out,err,status=Open3.capture3(File.join(output,'check'),path)
  File.write(File.join(output,"#{name}.log"),out+err)
  abort "Wrong result for #{name}: #{status.exitstatus}" unless status.exited? && status.success? == expected
end
puts "PASS: valid content and five PNG rejection controls"
