
import os
import shutil
import math

from panda3d.core import loadPrcFileData
loadPrcFileData("", "win-size 1100 760")
loadPrcFileData("", "window-title Shalu AI 11.1 - VRM Anime")

from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import AmbientLight, DirectionalLight, Vec4, TextNode


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VRM_FILE = os.path.join(BASE_DIR, "SHALU.vrm")
GLB_FILE = os.path.join(BASE_DIR, "SHALU_RUNTIME.glb")


class ShaluVRM(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()

        self.setBackgroundColor(0.025, 0.035, 0.08)

        # VRM 1.0 is a GLB container. Panda3D-gltf loads the GLB container,
        # while VRM-specific extensions remain inside the file.
        if not os.path.isfile(VRM_FILE):
            print("ERROR: SHALU.vrm not found:")
            print(VRM_FILE)
            return

        try:
            shutil.copyfile(VRM_FILE, GLB_FILE)
            print("Created runtime GLB:", GLB_FILE)
        except Exception as exc:
            print("ERROR copying VRM:", repr(exc))
            return

        # Camera
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

        self.status = self.make_text(
            "● SHALU IS READY",
            0.0, 0.86,
            0.055
        )

        self.hint = self.make_text(
            "VRM 1.0 • Anime Avatar",
            0.0, -0.90,
            0.035
        )

        self.t = 0.0
        self.taskMgr.add(self.idle_motion, "shalu_idle_motion")

    def make_text(self, text, x, z, scale):
        node = TextNode("ui")
        node.setText(text)
        node.setAlign(TextNode.ACenter)
        node.setTextColor(0.2, 1.0, 0.55, 1)
        np = self.aspect2d.attachNewNode(node)
        np.setScale(scale)
        np.setPos(x, 0, z)
        return np

    def load_shalu(self):
        print("Loading actual Shalu VRM as GLB container...")
        try:
            self.model = self.loader.loadModel(GLB_FILE)

            if self.model.isEmpty():
                print("ERROR: SHALU_RUNTIME.glb loaded as an empty model.")
                return

            self.model.reparentTo(self.render)

            # Center and scale automatically.
            bounds = self.model.getTightBounds()
            if bounds[0] is not None and bounds[1] is not None:
                lo, hi = bounds
                center = (lo + hi) * 0.5
                size = hi - lo
                largest = max(abs(size.x), abs(size.y), abs(size.z), 0.001)

                self.model.setPos(-center.x, -center.y, -center.z)
                self.model.setScale(3.8 / largest)

            # Most VRM characters face +Z/-Y depending on exporter.
            self.model.setH(180)

            print("SUCCESS: Actual SHALU.vrm model loaded!")
            print("VRM file:", VRM_FILE)

        except Exception as exc:
            print("ERROR loading Shalu VRM:", repr(exc))

    def idle_motion(self, task):
        if self.model:
            self.t += globalClock.getDt()

            # Very subtle idle motion.
            self.model.setP(math.sin(self.t * 0.9) * 0.7)
            self.model.setH(180 + math.sin(self.t * 0.55) * 1.2)

        return Task.cont


if __name__ == "__main__":
    ShaluVRM().run()
