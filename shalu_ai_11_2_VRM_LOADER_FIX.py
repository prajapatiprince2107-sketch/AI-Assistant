
import os
import math
import shutil

from panda3d.core import loadPrcFileData, LoaderFileTypeRegistry

loadPrcFileData("", "win-size 1100 760")
loadPrcFileData("", "window-title Shalu AI 11.2 - VRM Anime")

# IMPORTANT: register panda3d-gltf manually.
# The previous test proved that this registration works on this PC.
try:
    from gltf._loader import GltfLoader

    class LoaderEntryPoint:
        def __init__(self, name, loader):
            self.name = name
            self.loader = loader

        def load(self):
            return self.loader

    registry = LoaderFileTypeRegistry.getGlobalPtr()
    registry.register_deferred_type(LoaderEntryPoint("gltf", GltfLoader))
    registry.register_deferred_type(LoaderEntryPoint("glb", GltfLoader))
    print("GLTF/GLB loader registered manually.")
except Exception as exc:
    print("ERROR registering GLTF/GLB loader:", repr(exc))

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import AmbientLight, DirectionalLight, Vec4


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VRM_FILE = os.path.join(BASE_DIR, "SHALU.vrm")
RUNTIME_GLB = os.path.join(BASE_DIR, "SHALU_RUNTIME.glb")


class ShaluVRM(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()

        self.setBackgroundColor(0.025, 0.035, 0.08)

        self.camera.setPos(0, -8.5, 1.35)
        self.camera.lookAt(0, 0, 1.35)

        # Lighting
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.75, 0.75, 0.82, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        key = DirectionalLight("key")
        key.setColor(Vec4(1.0, 0.92, 0.95, 1))
        key_np = self.render.attachNewNode(key)
        key_np.setHpr(-25, -35, 0)
        self.render.setLight(key_np)

        fill = DirectionalLight("fill")
        fill.setColor(Vec4(0.55, 0.65, 1.0, 1))
        fill_np = self.render.attachNewNode(fill)
        fill_np.setHpr(145, -10, 0)
        self.render.setLight(fill_np)

        self.model = None
        self.load_shalu()

        self.t = 0.0
        self.taskMgr.add(self.idle_motion, "shalu_idle_motion")

    def load_shalu(self):
        print("Python folder:", BASE_DIR)
        print("SHALU.vrm exists:", os.path.isfile(VRM_FILE))

        if not os.path.isfile(VRM_FILE):
            print("ERROR: SHALU.vrm not found.")
            return

        # VRM is a GLB container. Make a temporary .glb copy.
        try:
            shutil.copy2(VRM_FILE, RUNTIME_GLB)
            print("Runtime GLB created:", RUNTIME_GLB)
            print("Runtime GLB exists:", os.path.isfile(RUNTIME_GLB))
        except Exception as exc:
            print("ERROR creating runtime GLB:", repr(exc))
            return

        try:
            # Relative filename is intentional; loader is registered for .glb.
            print("Loading SHALU_RUNTIME.glb ...")
            self.model = self.loader.loadModel("SHALU_RUNTIME.glb")

            if self.model.isEmpty():
                print("ERROR: loader returned an empty model.")
                return

            self.model.reparentTo(self.render)

            bounds = self.model.getTightBounds()
            if bounds[0] is not None and bounds[1] is not None:
                lo, hi = bounds
                center = (lo + hi) * 0.5
                size = hi - lo
                largest = max(abs(size.x), abs(size.y), abs(size.z), 0.001)

                self.model.setPos(-center.x, -center.y, -center.z)
                self.model.setScale(3.8 / largest)

            self.model.setH(180)

            print("SUCCESS: SHALU VRM/GLB model loaded!")

        except Exception as exc:
            print("ERROR loading SHALU_RUNTIME.glb:", repr(exc))

    def idle_motion(self, task):
        if self.model:
            self.t += globalClock.getDt()
            self.model.setP(math.sin(self.t * 0.9) * 0.7)
            self.model.setH(180 + math.sin(self.t * 0.55) * 1.2)

        return Task.cont


if __name__ == "__main__":
    ShaluVRM().run()
