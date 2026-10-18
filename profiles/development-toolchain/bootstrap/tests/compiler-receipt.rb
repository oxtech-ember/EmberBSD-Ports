#!/usr/bin/env ruby
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); actual preflight compiler-receipt guard.
require 'minitest/autorun'
require 'minitest/mock'
require 'tmpdir'
require_relative '../rebuild-libstdcxx'

class CompilerReceiptTest < Minitest::Test
  class ReceiptPreflight < GCC16Runtime::LibstdcxxRebuild
    def record(path)
      # Stop after the real identity and source-hash checks, before tool I/O.
      throw :receipt_verified, true if path == @receipt
    end
  end

  def verify(text, target = 'aarch64', source_hashes: :valid)
    Dir.mktmpdir('compiler-receipt-', '/tmp') do |dir|
      old = dir + '/old'
      FileUtils.mkdir_p(old + '/lang/gcc16')
      FileUtils.mkdir_p(dir + '/application/toolchain')
      archive = dir + '/gcc.tar.xz'
      File.write(archive, 'archive fixture')
      File.write(old + '/lang/gcc16/distinfo', 'distinfo fixture')
      hashes = [archive, old + '/lang/gcc16/distinfo'].map do |path|
        "#{Digest::SHA256.file(path).hexdigest}  #{path}\n"
      end.join
      hashes = '' if source_hashes == :missing
      hashes = hashes.gsub(/^[0-9a-f]{64}/, '0' * 64) if source_hashes == :wrong
      File.write(dir + '/application/inputs.txt', text + hashes)
      args = [target, dir + '/new', old, archive,
              dir + '/application/toolchain', dir + '/seed',
              dir + '/parent', dir + '/unused-output']
      builder = ReceiptPreflight.new(['--check', *args])
      parent = Object.new
      parent.define_singleton_method(:verify) do
        { metadata: { 'GCC_RUNTIME_TARGET' => target } }
      end
      # Parent-stage and recipe validation are independent services here.
      # The complete production preflight executes its receipt/hash guards.
      GCC16Runtime::Stage.stub(:new, parent) do
        GCC16Runtime::Inheritance.stub(:check_delta, nil) do
          assert_equal true, catch(:receipt_verified) { builder.preflight }
        end
      end
      refute File.exist?(dir + '/unused-output')
    end
  end

  def test_agreeing_producer_and_binutils_identities
    %w[aarch64 amd64].each do |target|
      triplet = GCC16Runtime::TARGETS.fetch(target).fetch(:triplet)
      [1, 2, 3].each do |copies|
        text = "mode=applications\ntarget=#{target}\ntriplet=#{triplet}\n"
        # cross/build.sh appends its binutils input receipt unchanged.
        (copies - 1).times { text << "target=#{target}\ntriplet=#{triplet}\n" }
        verify(text, target)
      end
    end
  end

  def test_missing_conflicting_or_noncanonical_identity_is_rejected
    valid = "mode=applications\ntriplet=aarch64--netbsd\n"
    invalid = [
      "mode=applications\n",
      "mode=applications\ntriplet=x86_64--netbsd\n",
      valid + "triplet=x86_64--netbsd\n",
      valid + "triplet=\n",
      valid + "triplet=aarch64-unknown-netbsd\n",
      valid + "triplet=aarch64--netbsd \n",
      valid + 'triplet=aarch64--netbsd',
      "triplet=aarch64--netbsd\n",
      valid + "mode=applications\n",
      valid + "mode=kernel\n",
      valid.sub('mode=applications', 'mode=kernel')
    ]
    invalid.each do |text|
      error = assert_raises(GCC16Runtime::Invalid) { verify(text) }
      assert_equal 'Missing application compiler provenance', error.message
    end
  end

  def test_source_hash_checks_still_follow_identity
    %i[missing wrong].each do |hashes|
      error = assert_raises(GCC16Runtime::Invalid) do
        verify("mode=applications\ntriplet=aarch64--netbsd\ntriplet=aarch64--netbsd\n",
          source_hashes: hashes)
      end
      assert_equal 'Application compiler source identity differs', error.message
    end
  end
end
