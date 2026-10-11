// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted). Deterministic scene-graph and layer pixels.
import QtQuick

Rectangle {
    id: root
    width: 640
    height: 400
    property int phase: 0
    readonly property list<color> colors: ["#ff0000", "#0000ff", "#ff00ff", "#00ffff"]
    color: root.colors[root.phase % 4]

    Rectangle {
        x: 16
        y: 16
        width: 64
        height: 64
        color: "#00ff00"
        // Exercise Quick's intermediate GPU render target, not just a clear.
        layer.enabled: true
    }
}
