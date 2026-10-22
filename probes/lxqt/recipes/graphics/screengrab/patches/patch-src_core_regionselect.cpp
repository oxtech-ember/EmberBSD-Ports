$NetBSD$

--- src/core/regionselect.cpp.orig
+++ src/core/regionselect.cpp
@@ -128,7 +128,6 @@ void RegionSelect::showEvent(QShowEvent *event)
                 layershell->setKeyboardInteractivity(LayerShellQt::Window::KeyboardInteractivityExclusive);
                 layershell->setExclusiveZone(-1); // not moved to accommodate for other surfaces
                 win->setScreen(_selectedScreen == nullptr ? qApp->primaryScreen() : _selectedScreen);
-                layershell->setScreenConfiguration(LayerShellQt::Window::ScreenConfiguration::ScreenFromQWindow);
             }
         }
     }
