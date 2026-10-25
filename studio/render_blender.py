"""Rota Cinema Studio — passo 2: cena e render no Blender (Cycles). Monta os módulos rcs/*.
Uso:  blender -b -P studio/render_blender.py    ou    python -c "import runpy; runpy.run_path('studio/render_blender.py')"
Env: W,H, SAMPLES, FPS, DUR, STILL_P ("0.3,0.55,0.9" → stills), FRAMES ("1-120" | "" = todos), DEVICE (CPU|GPU), OUTDIR, CAR_K (0.05).
"""
import json, math, os, sys, time
import bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from rcs import materials as M, vehicle, vehicle_rig, smoke, camera, lighting

OUT = os.environ.get("OUTDIR", os.path.join(HERE, "out")); S = json.load(open(os.path.join(OUT, "scene.json"), encoding="utf-8"))
W, H = int(os.environ.get("W", 1280)), int(os.environ.get("H", 720)); SAMPLES = int(os.environ.get("SAMPLES", 64))
FPS, DUR = int(os.environ.get("FPS", 30)), float(os.environ.get("DUR", 20)); NF = max(2, int(FPS*DUR)); MAP_M = S.get("map_m", 20.0)

# ---------- rota: simplificação + amostragem por distância ----------
def _dp(pts, eps):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; ab = b - a; L = ab.length; best, bi = 0, 0
    for i in range(1, len(pts)-1):
        d = (pts[i]-a).length if L < 1e-9 else abs(ab.x*(a.y-pts[i].y) - ab.y*(a.x-pts[i].x))/L
        if d > best: best, bi = d, i
    return _dp(pts[:bi+1], eps)[:-1] + _dp(pts[bi:], eps) if best > eps else [a, b]
route_full = [Vector((p[0], p[1], 0.0)) for p in S["route"]]; route = _dp(route_full, 0.004); print("rota:", len(route_full), "->", len(route), "pontos")
cum = [0.0]
for i in range(1, len(route)): cum.append(cum[-1] + (route[i]-route[i-1]).length)
TOTAL = cum[-1]; span = max(max(abs(p.x) for p in route), max(abs(p.y) for p in route))*2
CAR_L = span*float(os.environ.get("CAR_K", "0.05"))
def at(u):
    d = max(0.0, min(1.0, u))*TOTAL; lo, hi = 0, len(cum)-1
    while hi-lo > 1:
        mid = (lo+hi)//2
        if cum[mid] <= d: lo = mid
        else: hi = mid
    seg = cum[hi]-cum[lo]; t = 0 if seg == 0 else (d-cum[lo])/seg; return route[lo].lerp(route[hi], t)
def tangent(u, k=0.003):
    d = at(min(1, u+k)) - at(max(0, u-k)); return d.normalized() if d.length > 1e-6 else Vector((1, 0, 0))

# ---------- cena ----------
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100; sc.render.fps = FPS
cy = sc.cycles; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02; cy.use_denoising = True; cy.max_bounces = 6; cy.caustics_reflective = cy.caustics_refractive = False
if os.environ.get("DEVICE", "CPU").upper() == "GPU":
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for ct in ("OPTIX", "CUDA", "HIP", "METAL"):
            try: prefs.compute_device_type = ct; prefs.get_devices(); break
            except Exception: continue
        for d in prefs.devices: d.use = True
        cy.device = "GPU"; print("Cycles GPU:", prefs.compute_device_type, [d.name for d in prefs.devices if d.use])
    except Exception as e: print("GPU indisponível, CPU:", e)
lighting.color_management(sc); sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"

bpy.ops.mesh.primitive_plane_add(size=MAP_M); plane = bpy.context.object; plane.name = "Mapa"; plane.data.materials.append(M.paper_map(os.path.join(OUT, "map.png")))
bpy.ops.mesh.primitive_cube_add(size=1); table = bpy.context.object; table.name = "Mesa"; table.scale = (MAP_M*12, MAP_M*12, 0.3); table.location = (0, 0, -0.151); table.data.materials.append(M.simple("MesaM", (0.025, 0.03, 0.04), 0.7))

def make_curve(name, radius, mat, z):
    cd = bpy.data.curves.new(name, "CURVE"); cd.dimensions = "3D"; cd.bevel_depth = radius; cd.bevel_resolution = 8; cd.fill_mode = "FULL"; cd.use_fill_caps = True; cd.resolution_u = 10; cd.twist_mode = "Z_UP"; cd.bevel_factor_mapping_start = "SPLINE"; cd.bevel_factor_mapping_end = "SPLINE"
    sp = cd.splines.new("NURBS"); sp.points.add(len(route)-1); sp.order_u = 3; sp.use_endpoint_u = True
    for i, p in enumerate(route): sp.points[i].co = (p.x, p.y, z, 1.0)
    ob = bpy.data.objects.new(name, cd); bpy.context.collection.objects.link(ob); ob.data.materials.append(mat); ob.visible_shadow = False; return ob
tube = make_curve("Rota", CAR_L*0.03, M.route_glow((1.0, 0.26, 0.02), 3.2), CAR_L*0.03*0.9 + 0.002)
preview = make_curve("RotaPrevia", CAR_L*0.009, M.route_glow((1.0, 0.35, 0.06), 0.45), 0.004)

GLB = os.path.join(HERE, "..", "models", "car.glb")
if os.path.exists(GLB):
    car, car_real = vehicle.load(CAR_L, GLB); car = vehicle_rig.adopt(car, CAR_L)
else:
    car, car_real = vehicle_rig.build_estate(CAR_L), False; print("carro: carrinha ORIGINAL provisória (não é o BMW)")
anim = vehicle_rig.Animator(car, fps=FPS); fumo = smoke.Exhaust(car, CAR_L, puffs_per_pipe=6, life_frames=20, strength=0.06)
car_parts = [car] + list(car.children_recursive)
def car_visible(v):
    for o in car_parts: o.hide_render = not v
sun, rim, spot = lighting.setup(sc, MAP_M); lighting.bloom(sc)
rig = camera.Rig(sc, at, tangent, route, CAR_L, span)

# marcadores de paragens: disco branco
stops = []
for s_ in [dict(name=S["origin"]["name"], xy=S["route"][0]), *S.get("stops", []), dict(name=S["dest"]["name"], xy=S["route"][-1])]:
    bpy.ops.mesh.primitive_cylinder_add(radius=CAR_L*0.09, depth=CAR_L*0.02, vertices=32, location=(s_["xy"][0], s_["xy"][1], CAR_L*0.01)); d = bpy.context.object
    d.data.materials.append(M.simple("Marcador", (0.95, 0.9, 0.82), 0.5)); stops.append(d)

def pose(p):
    draw, car_u, cp, ct = rig.pose(p)
    tube.data.bevel_factor_end = max(0.0005, car_u); preview.data.bevel_factor_end = max(0.0005, draw)
    anim.step(cp, math.atan2(ct.y, ct.x)); car_visible(p >= .18)
    lighting.follow(sun, cp, CAR_L, spot, cp + ct*CAR_L*2)
    if p >= .18: fumo.step(0)

# ---------- render ----------
os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)
def render_to(path):
    t0 = time.time(); sc.render.filepath = path; bpy.ops.render.render(write_still=True); print(f"render {os.path.basename(path)} {time.time()-t0:.1f}s")
stills = [float(x) for x in os.environ.get("STILL_P", "").split(",") if x.strip()]; frames = os.environ.get("FRAMES", "")
if stills:
    for sp in stills:
        rig.pos = None; anim.prev = None; anim.prev_heading = None; fumo.hist = []
        for k in range(60): pose(max(0, sp - (60-k)*0.004))
        pose(sp); render_to(os.path.join(OUT, "frames", f"still_{int(round(sp*100)):03d}.png"))
else:
    if "-" in frames: a, b = [int(x) for x in frames.split("-")]; sel = set(range(a, b+1))
    elif frames: sel = set(int(x) for x in frames.split(","))
    else: sel = set(range(1, NF+1))
    SH, NS = int(os.environ.get("SHARD", "0")), int(os.environ.get("NSHARDS", "1")); sel = {f for f in sel if (f-1) % NS == SH}
    rig.pos = None
    for f in range(1, NF+1):
        pose((f-1)/(NF-1))
        if f in sel: render_to(os.path.join(OUT, "frames", f"f{f:04d}.png"))
print("carro real:", car_real, "| frames:", NF, "| CAR_L:", round(CAR_L, 3), "| span:", round(span, 2), "| mapa:", S.get("map_px"), "px", S.get("source"))
