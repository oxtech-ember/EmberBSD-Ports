#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Run only a newly prepared private guest.
require 'digest'
require 'json'
require 'fileutils'
require_relative 'resources'
abort 'usage: run.rb WORK' unless ARGV.size == 1
work = File.realpath(ARGV[0])
abort 'work must be an absolute canonical path' unless ARGV[0] == work
manifest = JSON.parse(File.read(work + '/artifacts/input.json'))
begin
  ram_mib = QueryVmResources.ram_mib(manifest.fetch('ram_mib', QueryVmResources::DEFAULT_RAM_MIB))
rescue ArgumentError => error
  abort error.message
end
Dir.glob('/proc/[0-9]*/cmdline').each do |path|
  begin
    first = File.binread(path).split("\0").first
    abort 'another QEMU system guest is active' if first && File.basename(first).start_with?('qemu-system-')
  rescue Errno::ENOENT, Errno::EACCES
    next
  end
end
kernel = work + '/artifacts/kernel.img'
disk = work + '/query.ffs'
abort 'kernel differs from prepared input' unless Digest::SHA256.file(kernel).hexdigest == manifest.fetch('kernel_image_sha256')
abort 'disk path is not the owned regular file' unless File.file?(disk) && !File.symlink?(disk) && File.stat(disk).nlink == 1
selected_qemu = ENV.fetch('QEMU_AARCH64', 'qemu-system-aarch64')
qemu = if selected_qemu.include?('/')
         File.realpath(selected_qemu)
       else
         candidate = ENV.fetch('PATH').split(':').map { |dir| File.join(dir, selected_qemu) }
                        .find { |path| File.file?(path) && File.executable?(path) }
         abort 'QEMU executable not found' unless candidate
         File.realpath(candidate)
       end
abort 'QEMU must be an executable ELF binary' unless File.executable?(qemu) && File.binread(qemu, 4) == "\x7fELF"
command = [qemu, '-name', 'ember-e14-query', '-machine', 'virt,accel=tcg', '-cpu', 'cortex-a72',
           '-m', ram_mib.to_s, '-smp', '2', '-display', 'none', '-serial', 'stdio', '-monitor', 'none', '-no-reboot',
           '-kernel', kernel, '-append', 'root=ld4a console=plcom0',
           '-drive', "file=#{disk},if=none,format=raw,id=root", '-device', 'virtio-blk-pci,drive=root',
           '-netdev', "user,id=net0,hostfwd=tcp:127.0.0.1:#{manifest.fetch('port')}-:22",
           '-device', 'virtio-net-pci,netdev=net0,romfile=']
start_time = File.read('/proc/self/stat').rpartition(') ').last.split.fetch(19)
File.write(work + '/artifacts/run.json', JSON.pretty_generate({argv: command, process_start_time: start_time,
  qemu_sha256: Digest::SHA256.file(qemu).hexdigest, disk_sha256: Digest::SHA256.file(disk).hexdigest}) + "\n")
File.write(work + '/runner.pid', Process.pid.to_s + "\n")
exec(*command)
