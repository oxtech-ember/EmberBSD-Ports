Not submitted upstream. Tests software image-node dirty notifications.

--- /dev/null
+++ tests/auto/quick/softwarerenderer/tst_qsgsoftwarelayerdirty.cpp
@@ -0,0 +1,140 @@
+// SPDX-License-Identifier: BSD-2-Clause
+// Origin: EmberBSD contributors (AI-assisted)
+
+#include <QtTest/QTest>
+#include <QtQuick/QQuickRenderControl>
+#include <QtQuick/QQuickWindow>
+#include <QtQuick/QSGRendererInterface>
+#include <QtQuick/private/qquickwindow_p.h>
+#include <QtQuick/private/qsgabstractrenderer_p.h>
+#include <QtQuick/private/qsgadaptationlayer_p.h>
+#include <QtQuick/private/qsgcontext_p.h>
+
+class DirtyStateRecorder final : public QSGAbstractRenderer
+{
+public:
+    struct Change {
+        QSGNode *node;
+        QSGNode::DirtyState state;
+    };
+
+    QList<Change> changes;
+
+    void renderScene() override { }
+
+protected:
+    void nodeChanged(QSGNode *node, QSGNode::DirtyState state) override
+    {
+        changes.append({node, state});
+    }
+};
+
+class SoftwareLayerFixture
+{
+public:
+    SoftwareLayerFixture() : window(&renderControl) { }
+
+    ~SoftwareLayerFixture()
+    {
+        recorder.setRootNode(nullptr);
+        if (imageNode) {
+            imageNode->setTexture(nullptr);
+            if (imageNode->parent() == &root)
+                root.removeChildNode(imageNode);
+            delete imageNode;
+        }
+        delete layer;
+    }
+
+    bool initialize()
+    {
+        renderContext = QQuickWindowPrivate::get(&window)->context;
+        if (!renderContext)
+            return false;
+        QSGContext *sceneGraphContext = renderContext->sceneGraphContext();
+        if (!sceneGraphContext)
+            return false;
+        imageNode = sceneGraphContext->createInternalImageNode(renderContext);
+        layer = sceneGraphContext->createLayer(renderContext);
+        if (!imageNode || !layer)
+            return false;
+
+        recorder.setRootNode(&root);
+        root.appendChildNode(imageNode);
+        imageNode->setTexture(layer);
+        recorder.changes.clear();
+        return true;
+    }
+
+    bool makeLayerClean()
+    {
+        layer->setLive(false);
+        return layer->updateTexture();
+    }
+
+    QQuickRenderControl renderControl;
+    QQuickWindow window;
+    QSGRootNode root;
+    DirtyStateRecorder recorder;
+    QSGRenderContext *renderContext = nullptr;
+    QSGInternalImageNode *imageNode = nullptr;
+    QSGLayer *layer = nullptr;
+};
+
+class tst_QSGSoftwareLayerDirty : public QObject
+{
+    Q_OBJECT
+
+private slots:
+    void initTestCase()
+    {
+        QQuickWindow::setGraphicsApi(QSGRendererInterface::Software);
+    }
+
+    void unchangedLayerDoesNotDirtyImageNode()
+    {
+        SoftwareLayerFixture fixture;
+        QVERIFY(fixture.initialize());
+        QVERIFY(fixture.makeLayerClean());
+        fixture.recorder.changes.clear();
+
+        fixture.imageNode->preprocess();
+
+        QVERIFY2(fixture.recorder.changes.isEmpty(),
+                 "an unchanged layer must not invalidate the software image node");
+    }
+
+    void changedLayerDirtiesGeometryAndMaterial()
+    {
+        SoftwareLayerFixture fixture;
+        QVERIFY(fixture.initialize());
+        QVERIFY(fixture.makeLayerClean());
+        fixture.recorder.changes.clear();
+
+        fixture.layer->markDirtyTexture();
+        fixture.layer->scheduleUpdate();
+        fixture.imageNode->preprocess();
+
+        QCOMPARE(fixture.recorder.changes.size(), 2);
+        QCOMPARE(fixture.recorder.changes.at(0).node, fixture.imageNode);
+        QCOMPARE(int(fixture.recorder.changes.at(0).state), int(QSGNode::DirtyGeometry));
+        QCOMPARE(fixture.recorder.changes.at(1).node, fixture.imageNode);
+        QCOMPARE(int(fixture.recorder.changes.at(1).state), int(QSGNode::DirtyMaterial));
+    }
+
+    void targetRectChangeStillDirtiesGeometry()
+    {
+        SoftwareLayerFixture fixture;
+        QVERIFY(fixture.initialize());
+        fixture.recorder.changes.clear();
+
+        fixture.imageNode->setTargetRect(QRectF(0, 0, 10, 10));
+
+        QCOMPARE(fixture.recorder.changes.size(), 1);
+        QCOMPARE(fixture.recorder.changes.constFirst().node, fixture.imageNode);
+        QCOMPARE(int(fixture.recorder.changes.constFirst().state), int(QSGNode::DirtyGeometry));
+    }
+};
+
+QTEST_MAIN(tst_QSGSoftwareLayerDirty)
+#include "tst_qsgsoftwarelayerdirty.moc"
