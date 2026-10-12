// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), installed Milou/KConfig integration.
import QtQuick
import QtTest
import org.kde.milou as Milou

Item {
    id: root
    width: 320
    height: 200

    Component {
        id: modelComponent
        Milou.ResultsModel {}
    }

    TestCase {
        name: "InstalledMilou"
        when: windowShown

        function test_configuredFavorites() {
            const model = createTemporaryObject(modelComponent, root)
            verify(!!model, "Component exists")
            compare(model.favoriteIds, ["ember-alpha", "ember-β"])
        }

        function test_overrideAndReset() {
            const model = createTemporaryObject(modelComponent, root)
            verify(!!model, "Component exists")
            model.favoriteIds = ["manual-one", "manual-two"]
            compare(model.favoriteIds, ["manual-one", "manual-two"])
            model.favoriteIds = undefined
            compare(model.favoriteIds, ["ember-alpha", "ember-β"])
        }

        function test_instanceIsolation() {
            const first = createTemporaryObject(modelComponent, root)
            const second = createTemporaryObject(modelComponent, root)
            verify(!!first, "Component exists")
            verify(!!second, "Component exists")
            first.favoriteIds = ["only-first"]
            compare(first.favoriteIds, ["only-first"])
            compare(second.favoriteIds, ["ember-alpha", "ember-β"])
        }
    }
}
