#!/bin/sh
# Start QGroundControl. It uses the installed Qt, QML and GStreamer files.
exec @PREFIX@/libexec/qgroundcontrol/QGroundControl "$@"
