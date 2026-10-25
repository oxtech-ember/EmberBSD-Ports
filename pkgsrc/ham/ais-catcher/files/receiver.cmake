# SPDX-License-Identifier: BSD-2-Clause
# Shared package selection for local RTL-SDR and raw IQ reception.
set(RTLSDR ON CACHE BOOL "Required RTL-SDR backend" FORCE)
foreach(feature SOAPYSDR AIRSPY SDRPLAY AIRSPYHF HACKRF HYDRASDR SOXR ZLIB
                SAMPLERATE ZMQ PSQL SQLITE OPENSSL NMEA2000 WEBVIEWER)
    set(${feature} OFF CACHE BOOL "Optional backend disabled" FORCE)
endforeach()
