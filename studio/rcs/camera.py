"""Câmara cinematográfica: 5 cenas (aproximação → desenho da rota → carro arranca → seguimento 3/4 macro → afastamento),
com suavização por frame e profundidade de campo física."""
import math
import bpy
from mathutils import Vector

def ease(t): return 4*t*t*t if t < .5 else 1 - ((-2*t+2)**3)/2
def smooth(a, b, t): return min(1.0, max(0.0, (t-a)/(b-a)))

class Rig:
    def __init__(self, scene, route_fn, tangent_fn, route_pts, car_len, span):
        self.at, self.tan, self.pts, self.L, self.span = route_fn, tangent_fn, route_pts, car_len, span
        bpy.ops.object.camera_add(); self.cam = bpy.context.object; scene.camera = self.cam
        self.cam.data.sensor_width = 36; self.cam.data.lens = 85
        self.focus = bpy.data.objects.new("Foco", None); bpy.context.collection.objects.link(self.focus)
        self.cam.data.dof.use_dof = True; self.cam.data.dof.focus_object = self.focus; self.cam.data.dof.aperture_fstop = 2.0; self.cam.data.dof.aperture_blades = 7
        self.pos = None; self.look = None

    def pose(self, p):
        """p ∈ [0,1]. Devolve (progresso da rota desenhada, progresso do carro)."""
        L, span = self.L, self.span
        draw = ease(smooth(.10, .40, p)); car_u = ease(smooth(.20, .86, p)); reveal = ease(smooth(.84, 1.0, p))
        cu = max(0.0005, min(.9995, car_u)); cp = self.at(cu); ct = self.tan(cu); up = Vector((0, 0, 1)); right = ct.cross(up).normalized()
        origin = self.pts[0]
        far = Vector((origin.x + span*.55, origin.y - span*.95, span*0.9))
        near = Vector((origin.x + L*2.2, origin.y - L*2.6, L*1.3))
        chase = cp - ct*L*3.6 + right*L*2.4 + up*L*1.15
        over = Vector((span*.05, -span*.75, span*0.95))
        if p < .20:
            t = ease(smooth(0, .20, p)); target = far.lerp(near, t); look = Vector((origin.x, origin.y, 0)); lens, fstop = 35 + 25*t, 4.0 - 2.0*t
        elif p < .84:
            target = chase; look = cp + ct*L*0.4 + Vector((0, 0, L*0.18)); lens, fstop = 70, 2.0
        else:
            target = chase.lerp(over, reveal); look = (cp + ct*L*0.4).lerp(Vector((0, 0, 0)), reveal); lens, fstop = 70 - 35*reveal, 2.0 + 3*reveal
        if self.pos is None or p < .20: self.pos, self.look = target.copy(), look.copy()
        self.pos = self.pos.lerp(target, .12); self.look = self.look.lerp(look, .15)
        self.cam.location = self.pos; d = self.look - self.pos; self.cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        self.cam.data.lens = lens; self.cam.data.dof.aperture_fstop = fstop
        self.focus.location = cp if .20 <= p < .84 else self.look
        return draw, car_u, cp, ct
