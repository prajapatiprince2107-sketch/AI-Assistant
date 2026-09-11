
import os
import math

from panda3d.core import loadPrcFileData, LoaderFileTypeRegistry
loadPrcFileData("", "win-size 1100 760")
loadPrcFileData("", "window-title Shalu AI 11.0 - 3D Anime")

# Explicitly register both .gltf and .glb with panda3d-gltf.
# This avoids the Windows/entry-point registration issue.
try:
    from gltf._loader import GltfLoader

    class LoaderEntryPoint:
        def __init__(self, name, loader):
            self.name = name
            self.loader = loader

        def load(self):
            return self.loader

    registry = LoaderFileTypeRegistry.getGlobalPtr()
    registry.register_deferred_type(
        LoaderEntryPoint("gltf", GltfLoader)
    )
    registry.register_deferred_type(
        LoaderEntryPoint("glb", GltfLoader)
    )
    print("GLTF/GLB loader registered manually.")
except Exception as exc:
    print("GLTF/GLB registration failed:", repr(exc))

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import AmbientLight, DirectionalLight, Vec4


class Shalu3D(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()

        self.camera.setPos(0, -7, 1.25)
        self.camera.lookAt(0, 0, 1.25)

        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.8, 0.8, 0.9, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        key = DirectionalLight("key")
        key.setColor(Vec4(1, 0.92, 0.95, 1))
        key_np = self.render.attachNewNode(key)
        key_np.setHpr(-25, -35, 0)
        self.render.setLight(key_np)

        self.model = None
        self.load_model()
        self.time = 0.0
        self.taskMgr.add(self.animate_idle, "animate_idle")

    def load_model(self):
        # Relative Panda path: avoids Windows drive/backslash path issues.
        model_name = "shalu_3d.glb"
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), model_name)

        print("Python file folder:", os.path.dirname(os.path.abspath(__file__)))
        print("GLB exists:", os.path.isfile(full_path))
        print("Loading:", model_name)

        if not os.path.isfile(full_path):
            print("ERROR: shalu_3d.glb is missing.")
            return

        try:
            self.model = self.loader.loadModel(model_name)

            if self.model.isEmpty():
                print("ERROR: model loaded as an empty NodePath.")
                return

            self.model.reparentTo(self.render)

            bounds = self.model.getTightBounds()
            if bounds[0] is not None and bounds[1] is not None:
                lo, hi = bounds
                center = (lo + hi) * 0.5
                size = hi - lo
                largest = max(abs(size.x), abs(size.y), abs(size.z), 0.001)

                self.model.setPos(-center.x, -center.y, -center.z)
                self.model.setScale(3.0 / largest)

            self.model.setH(180)
            print("SUCCESS: Shalu 3D GLB loaded!")

        except Exception as exc:
            print("ERROR loading GLB:", repr(exc))

    def animate_idle(self, task):
        self.time += globalClock.getDt()

        if self.model:
            self.model.setP(math.sin(self.time * 0.9) * 1.0)
            self.model.setH(180 + math.sin(self.time * 0.7) * 1.5)

        return Task.cont


if __name__ == "__main__":
    Shalu3D().run()
