
import os
import math

# Register the GLTF/GLB loader before Panda3D tries to load the model.
try:
    import gltf
    print("GLTF loader registered.")
except Exception as exc:
    print("GLTF loader import failed:", exc)

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    AmbientLight, DirectionalLight, Vec4,
    loadPrcFileData
)

loadPrcFileData("", "win-size 1100 760")
loadPrcFileData("", "window-title Shalu AI 11.0 - 3D Anime")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "shalu_3d.glb")


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
        self.load_3d_model()
        self.time = 0.0
        self.taskMgr.add(self.animate_idle, "animate_idle")

    def load_3d_model(self):
        print("Checking:", MODEL_PATH)

        if not os.path.isfile(MODEL_PATH):
            print("ERROR: shalu_3d.glb is not in:", BASE_DIR)
            return

        try:
            self.model = self.loader.loadModel(MODEL_PATH)

            if self.model.isEmpty():
                print("ERROR: Panda3D returned an empty model.")
                return

            self.model.reparentTo(self.render)

            # Center and frame the model automatically.
            bounds = self.model.getTightBounds()
            if bounds[0] is not None and bounds[1] is not None:
                lo, hi = bounds
                center = (lo + hi) * 0.5
                size = hi - lo
                largest = max(abs(size.x), abs(size.y), abs(size.z), 0.001)

                self.model.setPos(-center.x, -center.y, -center.z)
                self.model.setScale(3.0 / largest)

            self.model.setH(180)
            print("SUCCESS: Shalu 3D model loaded!")

        except Exception as exc:
            print("ERROR loading Shalu 3D model:", repr(exc))

    def animate_idle(self, task):
        self.time += globalClock.getDt()

        if self.model:
            self.model.setP(math.sin(self.time * 0.9) * 1.0)
            self.model.setH(180 + math.sin(self.time * 0.7) * 1.5)

        return Task.cont


if __name__ == "__main__":
    app = Shalu3D()
    app.run()
