# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Validate recorded guest resource limits.
module QueryVmResources
  DEFAULT_RAM_MIB = 1024

  def self.ram_mib(value = DEFAULT_RAM_MIB)
    unless value.is_a?(Integer) || (value.is_a?(String) && value.match?(/\A[0-9]+\z/))
      raise ArgumentError, 'RAM must be an integer from 1024 to 8192 MiB'
    end
    result = value.is_a?(String) ? Integer(value, 10) : value
    raise ArgumentError, 'RAM must be an integer from 1024 to 8192 MiB' unless (1024..8192).cover?(result)
    result
  end
end
