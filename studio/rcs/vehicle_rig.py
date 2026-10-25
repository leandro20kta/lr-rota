"""Sistema de veículo reutilizável do Rota Cinema Studio.

Hierarquia (convenção de nomes — um .glb que a siga é adotado tal como está):
  Veiculo                     raiz (posição/rumo no mapa)
  ├── Suspensao               corpo: inclinação lateral, mergulho, salto
  │     └── (carroçaria, vidros, luzes, escapes...)
  ├── roda_FE_pivot → roda_FE dianteira esquerda   (pivot: esterçamento em Z; roda: rotação em Y)
  ├── roda_FD_pivot → roda_FD dianteira direita
  ├── roda_TE_pivot → roda_TE traseira esquerda
  └── roda_TD_pivot → roda_TD traseira direita
  escape_1..4 (empties nas saídas)   farol* / farolim* (materiais emissivos)
Frente = +X, esquerda = +Y, cima = +Z, chão em z = 0.

O modelo procedural aqui é uma CARRINHA ORIGINAL PROVISÓRIA (não reproduz nenhuma marca ou modelo real).
"""
import bpy, bmesh, math
from mathutils import Vector
from . import materials as M

WHEELS = ("roda_FE", "roda_FD", "roda_TE", "roda_TD")

# ---------------------------------------------------------------- construção
def _link(o, col):
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o); return o

def _empty(name, col, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None); col.objects.link(e); e.location = loc; e.empty_display_size = 0.1
    if parent: e.parent = parent
    return e

def _extrude(name, pts, width, s, mat, col, bevel=0.1, segs=6, y0=0.0, smooth=True):
    """Perfil lateral (x, z) em metros, extrudido na largura (y). Escala s = unidades/metro."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((x*s, (y0 - width/2)*s, z*s)) for x, z in pts]; f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f]); verts = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, width*s, 0), verts=verts); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col.objects.link(ob); ob.data.materials.append(mat)
    if bevel:
        m = ob.modifiers.new("bevel", "BEVEL"); m.width = bevel*s; m.segments = segs; m.limit_method = "ANGLE"; m.angle_limit = math.radians(35)
    if smooth:
        for p in ob.data.polygons: p.use_smooth = True
        try: ob.modifiers.new("wn", "WEIGHTED_NORMAL").keep_sharp = True
        except Exception: pass
    return ob

def _box(name, dims, loc, s, mat, col, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name
    o.scale = tuple(v*s for v in dims); o.location = tuple(v*s for v in loc); o.rotation_euler = rot
    _link(o, col); o.data.materials.append(mat)
    if bevel: m = o.modifiers.new("bevel", "BEVEL"); m.width = bevel*s; m.segments = 3
    return o

def _cyl(name, r, depth, loc, s, mat, col, rot=(math.pi/2, 0, 0), verts=48, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=r*s, depth=depth*s, vertices=verts, location=tuple(v*s for v in loc), rotation=rot)
    o = bpy.context.object; o.name = name; _link(o, col); o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    if bevel: m = o.modifiers.new("bevel", "BEVEL"); m.width = bevel*s; m.segments = 4; m.limit_method = "ANGLE"
    return o

def _arc(cx, cz, r, a0, a1, n=14): return [(cx + r*math.cos(a0 + (a1-a0)*i/n), cz + r*math.sin(a0 + (a1-a0)*i/n)) for i in range(n+1)]

def _wheel(name, s, col, mats, side):
    """Roda original: pneu de perfil baixo, jante de 10 raios duplos, disco de travão. Eixo de rotação = Y local."""
    tyre, rim, rim_face, brake, cap = mats
    root = _empty(name, col)
    R, W = 0.36, 0.25           # raio exterior (m), largura
    t = _cyl(name+"_pneu", R, W, (0, 0, 0), s, tyre, col, verts=64, bevel=0.035); t.parent = root
    r = _cyl(name+"_jante", R*0.80, W*0.92, (0, 0, 0), s, rim, col, verts=64); r.parent = root
    # face da jante: raios duplos (original) do lado exterior
    face_y = side*(W*0.47)
    for i in range(10):
        a = i*2*math.pi/10
        for off in (-0.045, 0.045):
            o = _box(f"{name}_raio{i}", (0.024, 0.03, R*0.74), (0, face_y, 0), s, rim_face, col)
            o.rotation_euler = (0, a + off, 0); o.location = (math.sin(a+off)*R*0.41*s, face_y*s, math.cos(a+off)*R*0.41*s); o.parent = root
    c = _cyl(name+"_centro", 0.055, 0.04, (0, face_y, 0), s, cap, col, verts=32); c.parent = root
    b = _cyl(name+"_disco", R*0.62, 0.03, (0, -side*0.05, 0), s, brake, col, verts=48); b.parent = root
    return root

def build_estate(length=0.7, paint_rgb=(0.006, 0.007, 0.009)):
    """Carrinha original provisória (4.6 m reais escalados para `length`). Devolve a raiz 'Veiculo'."""
    s = length/4.6
    col = bpy.data.collections.new("Veiculo"); bpy.context.scene.collection.children.link(col)
    paint, glass = M.car_paint(paint_rgb), M.car_glass()
    trim = M.simple("Plastico", (0.015, 0.015, 0.017), 0.45); chrome = M.simple("Cromado", (0.8, 0.8, 0.82), 0.12, 1.0)
    tyre = M.simple("Pneu", (0.01, 0.01, 0.011), 0.88); rim = M.simple("JanteBase", (0.025, 0.025, 0.028), 0.5, 0.4)
    rim_face = M.simple("JanteFace", (0.42, 0.43, 0.45), 0.24, 1.0); brake = M.simple("Disco", (0.3, 0.3, 0.32), 0.4, 1.0); cap = M.simple("Centro", (0.1, 0.1, 0.11), 0.3, 1.0)
    head = M.emissive("farol", (0.92, 0.96, 1.0), 14.0, base=(0.9, 0.9, 0.95)); tail = M.emissive("farolim", (1.0, 0.05, 0.03), 9.0, base=(0.25, 0.01, 0.01))
    root = _empty("Veiculo", col); susp = _empty("Suspensao", col, parent=root)
    WB, TR = 2.80, 1.52   # distância entre eixos, via (m)
    xf, xr = WB/2, -WB/2
    # carroçaria: perfil de carrinha (tejadilho longo, traseira quase vertical) com cavas das rodas
    body = ([(-2.30, .40), (-2.34, .62), (-2.30, 1.00), (-2.18, 1.30), (-1.95, 1.43), (-0.40, 1.46), (0.38, 1.44), (0.80, 1.28),
             (1.35, 1.02), (1.90, 0.94), (2.22, 0.86), (2.33, 0.70), (2.34, 0.48), (2.28, 0.40), (xf+0.46, 0.40)]
            + _arc(xf, 0.36, 0.46, 0, math.pi)[1:-1] + [(xf-0.46, 0.40), (xr+0.46, 0.40)] + _arc(xr, 0.36, 0.46, 0, math.pi)[1:-1] + [(xr-0.46, 0.40)])
    b = _extrude("carrocaria", body, 1.80, s, paint, col, bevel=0.12, segs=8); b.parent = susp
    # habitáculo (vidros) mais estreito, com pilares
    gh = [(-2.12, 1.02), (-2.05, 1.30), (-1.88, 1.40), (0.32, 1.405), (0.74, 1.26), (1.28, 1.03)]
    g = _extrude("vidros", gh, 1.62, s, glass, col, bevel=0.03, segs=3); g.location.z = 0.012*s; g.parent = susp
    for x in (-1.15, -0.05, 0.62):   # pilares B/C/D em preto brilhante
        p = _box("pilar", (0.07, 1.64, 0.32), (x, 0, 1.22), s, paint, col); p.parent = susp
    for y in (0.72, -0.72):          # barras de tejadilho (genéricas)
        rr = _box("barra_tejadilho", (2.1, 0.04, 0.035), (-0.85, y, 1.485), s, trim, col, bevel=0.01); rr.parent = susp
    # frente: grelha única larga (original), faróis em lâmina, para-choques com entradas
    _box("grelha", (0.05, 0.95, 0.16), (2.33, 0, 0.63), s, trim, col, bevel=0.01).parent = susp
    _box("entrada_ar", (0.05, 1.30, 0.10), (2.31, 0, 0.47), s, trim, col, bevel=0.01).parent = susp
    for y in (0.62, -0.62):
        _box("farol", (0.04, 0.36, 0.045), (2.30, y, 0.78), s, head, col).parent = susp
        _box("farol_drl", (0.04, 0.12, 0.03), (2.31, y*1.15, 0.50), s, head, col).parent = susp
    # traseira: farolins horizontais em L, difusor, 4 escapes (2+2)
    for y in (0.62, -0.62):
        _box("farolim", (0.04, 0.42, 0.05), (-2.30, y, 0.98), s, tail, col).parent = susp
        _box("farolim_L", (0.04, 0.05, 0.16), (-2.30, y*1.35, 0.92), s, tail, col).parent = susp
    _box("difusor", (0.16, 1.40, 0.12), (-2.26, 0, 0.44), s, trim, col, bevel=0.01).parent = susp
    _box("splitter", (0.16, 1.70, 0.05), (2.28, 0, 0.42), s, trim, col, bevel=0.01).parent = susp
    exh = []
    for i, (y) in enumerate((0.62, 0.48, -0.48, -0.62)):
        e = _cyl(f"ponteira_{i+1}", 0.045, 0.14, (-2.34, y, 0.44), s, chrome, col, rot=(0, math.pi/2, 0), verts=24); e.parent = susp
        m = _empty(f"escape_{i+1}", col, loc=((-2.42)*s, y*s, 0.44*s), parent=susp); exh.append(m)
    for y in (0.98, -0.98):
        _box("espelho", (0.14, 0.12, 0.09), (0.86, y, 1.10), s, paint, col, bevel=0.02).parent = susp
    # rodas: pivot (esterçamento) + roda (rotação)
    wm = (tyre, rim, rim_face, brake, cap)
    for nm, x, y in (("roda_FE", xf, TR/2), ("roda_FD", xf, -TR/2), ("roda_TE", xr, TR/2), ("roda_TD", xr, -TR/2)):
        piv = _empty(nm+"_pivot", col, loc=(x*s, y*s, 0.36*s), parent=root)
        w = _wheel(nm, s, col, wm, 1 if y > 0 else -1); w.parent = piv
    # feixes dos faróis (luz real projetada no mapa) e brilho dos farolins
    for y in (0.62, -0.62):
        bpy.ops.object.light_add(type="SPOT"); L = bpy.context.object; L.name = "feixe_farol"; _link(L, col); L.parent = susp
        L.location = (2.36*s, y*s, 0.78*s); L.rotation_euler = (0, math.radians(90 + 8), 0)
        L.data.energy = 5.0*length*length; L.data.color = (0.95, 0.97, 1.0); L.data.spot_size = math.radians(55); L.data.spot_blend = 0.6; L.data.shadow_soft_size = 0.02*length
        bpy.ops.object.light_add(type="POINT"); P = bpy.context.object; P.name = "brilho_farolim"; _link(P, col); P.parent = susp
        P.location = (-2.40*s, y*s, 0.98*s); P.data.energy = 0.3*length*length; P.data.color = (1.0, 0.1, 0.05); P.data.shadow_soft_size = 0.05*length
    root["lr_rota_vehicle"] = "carrinha_original_provisoria"; root["wheel_radius"] = 0.36*s; root["wheelbase"] = WB*s; root["length"] = length
    return root

# ---------------------------------------------------------------- adoção de um .glb
def adopt(root, length):
    """Liga um modelo importado à convenção. Se faltarem pivots de roda, cria-os no centro de cada roda."""
    objs = {o.name.split(".")[0]: o for o in root.children_recursive}
    for nm in WHEELS:
        w = objs.get(nm)
        if w and not (w.parent and w.parent.name.startswith(nm+"_pivot")):
            piv = bpy.data.objects.new(nm+"_pivot", None); bpy.context.collection.objects.link(piv)
            piv.parent = root; piv.matrix_world = w.matrix_world.copy(); w.parent = piv; w.matrix_parent_inverse.identity(); w.location = (0, 0, 0); w.rotation_euler = (0, 0, 0)
    if "Suspensao" not in objs:
        susp = bpy.data.objects.new("Suspensao", None); bpy.context.collection.objects.link(susp); susp.parent = root
        for o in list(root.children):
            if not o.name.startswith(tuple(n+"_pivot" for n in WHEELS)) and o is not susp: o.parent = susp
    root.setdefault("wheel_radius", 0.36*length/4.6); root.setdefault("wheelbase", 2.8*length/4.6); root["length"] = length
    return root

# ---------------------------------------------------------------- animação
class Animator:
    """Converte o movimento do veículo no mapa em rodas a girar, direção, suspensão. Chamar step() uma vez por frame, em ordem."""
    def __init__(self, root, fps=24, max_spin_per_frame=0.55):
        self.root = root; self.fps = fps; self.r = root["wheel_radius"]; self.wb = root["wheelbase"]; self.L = root["length"]
        self.susp = next((o for o in root.children if o.name.startswith("Suspensao")), None)
        self.piv = {nm: next((o for o in root.children if o.name.startswith(nm+"_pivot")), None) for nm in WHEELS}
        self.wheel = {nm: (p.children[0] if p and p.children else None) for nm, p in self.piv.items()}
        self.spin = 0.0; self.steer = 0.0; self.prev = None; self.prev_heading = None; self.prev_speed = 0.0
        self.roll = 0.0; self.pitch = 0.0; self.dist = 0.0; self.max_spin = max_spin_per_frame

    def step(self, pos, heading):
        """pos: Vector (x,y) no mapa; heading: rad. Atualiza a raiz e todas as peças móveis."""
        self.root.location = (pos.x, pos.y, 0.0); self.root.rotation_euler = (0, 0, heading)
        ds = 0.0 if self.prev is None else (Vector((pos.x, pos.y)) - Vector((self.prev.x, self.prev.y))).length
        dh = 0.0 if self.prev_heading is None else math.atan2(math.sin(heading - self.prev_heading), math.cos(heading - self.prev_heading))
        curv = dh/ds if ds > 1e-6 else 0.0
        speed = ds*self.fps; accel = (speed - self.prev_speed)*self.fps
        self.dist += ds
        # rodas: ângulo = distância/raio; limitado por frame para não "estroboscopar" (efeito vagão) em rotas aceleradas
        self.spin -= max(-self.max_spin, min(self.max_spin, ds/self.r))
        target_steer = max(-0.5, min(0.5, math.atan(self.wb*curv)*1.6))
        self.steer += (target_steer - self.steer)*0.25
        for nm in WHEELS:
            if self.wheel[nm]: self.wheel[nm].rotation_euler = (0, self.spin, 0)
            if self.piv[nm]: self.piv[nm].rotation_euler = (0, 0, self.steer if nm in ("roda_FE", "roda_FD") else 0.0)
        # suspensão: inclinação lateral nas curvas, mergulho na travagem, salto leve da estrada
        lat = speed*speed*curv/self.L; lon = accel/max(self.L*self.fps, 1e-6)
        self.roll += (max(-0.035, min(0.035, -lat*0.0025)) - self.roll)*0.2
        self.pitch += (max(-0.025, min(0.025, lon*0.004)) - self.pitch)*0.2
        bounce = 0.004*self.L*math.sin(self.dist/self.L*9.0) + 0.002*self.L*math.sin(self.dist/self.L*23.0)
        if self.susp: self.susp.rotation_euler = (self.roll, self.pitch, 0); self.susp.location = (0, 0, bounce)
        self.prev = Vector((pos.x, pos.y)); self.prev_heading = heading; self.prev_speed = speed

    def showcase(self, t, wheel_rate=1.2, steer_amp=0.35):
        """Apresentação parada (360°): rodas a girar devagar, direção a oscilar, suspensão a 'respirar'."""
        self.spin = -t*wheel_rate; self.steer = steer_amp*math.sin(t*1.3)
        for nm in WHEELS:
            if self.wheel[nm]: self.wheel[nm].rotation_euler = (0, self.spin, 0)
            if self.piv[nm]: self.piv[nm].rotation_euler = (0, 0, self.steer if nm in ("roda_FE", "roda_FD") else 0.0)
        if self.susp: self.susp.location = (0, 0, 0.004*self.L*math.sin(t*2.1)); self.susp.rotation_euler = (0.006*math.sin(t*1.7), 0.004*math.sin(t*1.1), 0)
