
import os
import math
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    AmbientLight, DirectionalLight, Vec4,
    WindowProperties, loadPrcFileData
)

loadPrcFileData("", "win-size 1100 760")
loadPrcFileData("", "window-title Shalu AI 11.0 - 3D Anime")

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "shalu_3d.glb"
)

class Shalu3D(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.disableMouse()

        # Camera
        self.camera.setPos(0, -7, 1.3)
        self.camera.lookAt(0, 0, 1.3)

        # Lighting
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.72, 0.72, 0.82, 1))
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

        # Idle animation hook.
        self.taskMgr.add(self.animate_idle, "animate_idle")

    def load_3d_model(self):
        if not os.path.exists(MODEL_PATH):
            print()
            print("3D model not found:")
            print(MODEL_PATH)
            print()
            print("Put your Shalu 3D .glb model in this same folder")
            print("and name it: shalu_3d.glb")
            return

        try:
            self.model = self.loader.loadModel(MODEL_PATH)
            self.model.reparentTo(self.render)
            self.model.setPos(0, 0, -1.15)
            self.model.setScale(1.8)
            self.model.setH(180)
            print("Shalu 3D model loaded successfully.")
        except Exception as exc:
            print("Could not load Shalu 3D model:", exc)

    def animate_idle(self, task):
        self.time += globalClock.getDt()

        if self.model:
            # Very subtle breathing/idle movement.
            self.model.setZ(-1.15 + math.sin(self.time * 1.8) * 0.018)
            self.model.setP(math.sin(self.time * 0.9) * 1.2)
            self.model.setH(180 + math.sin(self.time * 0.7) * 1.5)

        return Task.cont

if __name__ == "__main__":
    app = Shalu3D()
    app.run()
