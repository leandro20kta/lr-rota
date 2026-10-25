"""Fumo de escape discreto, determinístico (sem simulação de fluidos): baforadas volumétricas
nascem em cada escape_N, ficam no sítio onde nasceram (o carro afasta-se), sobem, crescem e desvanecem.
Densidade por objeto via Object Info → Color (um só material partilhado)."""
import bpy, math, random
from mathutils import Vector

def _material():
    m = bpy.data.materials.new("FumoEscape"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    info = nt.nodes.new("ShaderNodeObjectInfo"); sep = nt.nodes.new("ShaderNodeSeparateColor")
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 6.0
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 3.5; noise.inputs["Detail"].default_value = 4
    grad = nt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type = "SPHERICAL"
    m2 = nt.nodes.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; m3 = nt.nodes.new("ShaderNodeMath"); m3.operation = "MULTIPLY"
    vol = nt.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Color"].default_value = (0.82, 0.84, 0.88, 1); vol.inputs["Anisotropy"].default_value = 0.3
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"], grad.inputs["Vector"]); nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(info.outputs["Color"], sep.inputs["Color"]); nt.links.new(sep.outputs[0], mul.inputs[0])
    nt.links.new(grad.outputs["Fac"], m2.inputs[0]); nt.links.new(noise.outputs["Fac"], m2.inputs[1])
    nt.links.new(m2.outputs[0], m3.inputs[0]); nt.links.new(mul.outputs[0], m3.inputs[1])
    nt.links.new(m3.outputs[0], vol.inputs["Density"]); nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return m

class Exhaust:
    def __init__(self, vehicle_root, car_len, puffs_per_pipe=10, life_frames=22, strength=0.35, seed=7):
        self.pipes = sorted([o for o in vehicle_root.children_recursive if o.name.startswith("escape_")], key=lambda o: o.name)
        self.L, self.N, self.life, self.k = car_len, puffs_per_pipe, life_frames, strength
        self.mat = _material(); self.hist = []; self.rng = random.Random(seed); self.puffs = []
        col = bpy.data.collections.new("Fumo"); bpy.context.scene.collection.children.link(col)
        for pi, pipe in enumerate(self.pipes):
            for j in range(self.N):
                bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=16, ring_count=8); o = bpy.context.object; o.name = f"fumo_{pi}_{j}"
                for c in list(o.users_collection): c.objects.unlink(o)
                col.objects.link(o); o.data.materials.append(self.mat); o.hide_render = True
                o.visible_shadow = False
                self.puffs.append((pi, j, o, self.rng.uniform(0, 1), Vector((self.rng.uniform(-1, 1), self.rng.uniform(-1, 1), self.rng.uniform(0.3, 1)))))

    def step(self, frame):
        """Registar onde está cada escape neste frame e posicionar as baforadas vivas."""
        bpy.context.view_layer.update()
        self.hist.append([(p.matrix_world.translation.copy(), (p.matrix_world.to_3x3() @ Vector((-1, 0, 0))).normalized()) for p in self.pipes])
        spacing = max(1, self.life // self.N)
        for pi, j, o, jitter, drift in self.puffs:
            birth = len(self.hist) - 1 - j*spacing - int(jitter*spacing)
            if birth < 0: o.hide_render = True; continue
            age = (len(self.hist) - 1 - birth)/self.life
            if age > 1: o.hide_render = True; continue
            pos, back = self.hist[birth][pi]
            L = self.L
            o.location = pos + back*(L*0.08 + age*L*0.35) + Vector((drift.x*L*0.06*age, drift.y*L*0.06*age, drift.z*L*0.22*age))
            r = L*(0.025 + 0.09*age); o.scale = (r, r*0.85, r*0.8)
            dens = self.k*(1 - age)**1.6*min(1.0, age*6)
            o.color = (dens, 0, 0, 1); o.hide_render = dens < 0.005
