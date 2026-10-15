// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Run with the installed target Qt QML tool.
import QtQml
import org.kde.plasma.private.volume 0.1

QtObject {
    Component.onCompleted: {
        if (PulseAudio.NormalVolume !== 65536 || PulseAudio.MinimalVolume !== 0) {
            console.error("Unexpected PulseAudio volume constants")
            Qt.exit(1)
        } else {
            console.log("PASS: installed volume QML plugin and PulseAudioQt constants")
            Qt.exit(0)
        }
    }
}
