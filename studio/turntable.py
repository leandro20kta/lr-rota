"""Rota Cinema Studio — apresentação 360° do veículo + exportação dos ficheiros do veículo.
Env: W,H,SAMPLES,FPS,DUR, STILL_P ("0.0,0.33,0.66" → stills), FRAMES, DEVICE, OUTDIR, EXPORT=1 (grava .blend e .glb em studio/assets/vehicles)
"""
import os, sys, math, time
import bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from rcs import materials as M, vehicle, vehicle_rig, smoke, lighting

OUT = os.environ.get("OUTDIR", os.path.join(HERE, "out")); os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)
W, H = int(os.environ.get("W", 1280)), int(os.environ.get("H", 720)); SAMPLES = int(os.environ.get("SAMPLES", 64))
FPS, DUR = int(os.environ.get("FPS", 24)), float(os.environ.get("DUR", 6)); NF = max(2, int(FPS*DUR)); L = 4.6

bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, NF
cy = sc.cycles; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.use_denoising = True; cy.max_bounces = 8; cy.volume_bounces = 0; cy.volume_step_rate = 4.0
if os.environ.get("DEVICE", "CPU").upper() == "GPU":
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for ct in ("OPTIX", "CUDA", "HIP", "METAL"):
            try: prefs.compute_device_type = ct; prefs.get_devices(); break
            except Exception: continue
        for d in prefs.devices: d.use = True
        cy.device = "GPU"
    except Exception as e: print("GPU indisponível:", e)
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = 0.0

# estúdio: ciclorama escuro, chão espelhado
bpy.ops.mesh.primitive_plane_add(size=60); floor = bpy.context.object; floor.name = "Chao"
fm, fnt, fb = M.principled("ChaoEstudio"); fb.inputs["Base Color"].default_value = (0.018, 0.02, 0.024, 1); fb.inputs["Roughness"].default_value = 0.16; fb.inputs["Specular IOR Level"].default_value = 0.7
nz = fnt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 4; ramp = fnt.nodes.new("ShaderNodeMapRange"); ramp.inputs["To Min"].default_value = 0.1; ramp.inputs["To Max"].default_value = 0.28
fnt.links.new(nz.outputs["Fac"], ramp.inputs["Value"]); fnt.links.new(ramp.outputs["Result"], fb.inputs["Roughness"]); floor.data.materials.append(fm)
bpy.ops.mesh.primitive_cylinder_add(radius=18, depth=14, vertices=96, location=(0, 0, 7)); cyc = bpy.context.object; cyc.name = "Ciclorama"
for p in cyc.data.polygons: p.use_smooth = True
cyc.data.materials.append(M.simple("Fundo", (0.012, 0.014, 0.018), 0.6)); cyc.modifiers.new("solid", "SOLIDIFY").thickness = -0.1

# veículo
GLB = os.environ.get("CAR_GLB") or os.path.join(HERE, "..", "models", "car.glb")
if os.path.exists(GLB): car, real = vehicle.load(L, GLB); car = vehicle_rig.adopt(car, L)
else: car, real = vehicle_rig.build_estate(L), False
anim = vehicle_rig.Animator(car, fps=FPS); fumo = smoke.Exhaust(car, L, puffs_per_pipe=6, life_frames=26, strength=0.05, follow=True)

# luz: softbox por cima, contraluz azul-petróleo, recorte laranja
def area(name, energy, color, size, loc, target=(0, 0, 0.7)):
    bpy.ops.object.light_add(type="AREA"); o = bpy.context.object; o.name = name; o.data.energy = energy; o.data.color = color; o.data.size = size; o.location = loc
    d = Vector(target) - Vector(loc); o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler(); return o
area("Softbox", 3200, (1.0, 0.97, 0.93), 7, (0, 0, 6))
area("ContraluzAzul", 2600, (0.25, 0.6, 1.0), 4, (-7, 5, 3.2))
area("RecorteLaranja", 500, (1.0, 0.55, 0.22), 3, (7, -7, 2.4))
area("Faixa", 1400, (1.0, 1.0, 1.0), 1.2, (1, -6, 6.0))
area("Preenchimento", 600, (0.9, 0.93, 1.0), 8, (8, 3, 2.5))
w = bpy.data.worlds.new("Mundo"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.008, 0.012, 1); w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.3
lighting.bloom(sc, threshold=1.0, strength=0.35, size=0.7)

bpy.ops.object.camera_add(location=(8.6, -6.4, 1.9)); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 50
d = Vector((0, 0, 0.62)) - cam.location; cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = (cam.location - Vector((0, 0, 0.6))).length; cam.data.dof.aperture_fstop = 4.0

def pose(f):
    t = (f-1)/NF; car.rotation_euler = (0, 0, -math.pi*0.15 + t*2*math.pi)
    anim.showcase(t*DUR); fumo.step(f)

def render_to(path):
    t0 = time.time(); sc.render.filepath = path; bpy.ops.render.render(write_still=True); print(f"render {os.path.basename(path)} {time.time()-t0:.1f}s")

stills = [float(x) for x in os.environ.get("STILL_P", "").split(",") if x.strip()]
if stills:
    for sp in stills:
        f0 = 1 + int(sp*NF); fumo.hist = []
        for f in range(max(1, f0-30), f0+1): pose(f)
        render_to(os.path.join(OUT, "frames", f"turn_{int(round(sp*100)):03d}.png"))
elif os.environ.get("RENDER", "1") == "1":
    SH, NS = int(os.environ.get("SHARD", "0")), int(os.environ.get("NSHARDS", "1"))
    for f in range(1, NF+1):
        pose(f)
        if (f-1) % NS == SH: render_to(os.path.join(OUT, "frames", f"t{f:04d}.png"))

if os.environ.get("EXPORT") == "1":
    dst = os.path.join(HERE, "assets", "vehicles"); os.makedirs(dst, exist_ok=True); fumo.hist = []
    # animação gravada em keyframes (rodas, direção, suspensão, rotação 360°) para o .glb
    for o in bpy.data.collections["Fumo"].objects: o.hide_render = True
    keyed = [car] + [o for o in car.children_recursive if o.name.startswith(("roda_", "Suspensao"))]
    for f in range(1, NF+1, 2):
        pose(f)
        for o in keyed: o.keyframe_insert("rotation_euler", frame=f); o.keyframe_insert("location", frame=f)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(dst, "carrinha_provisoria.blend"), compress=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in [car] + list(car.children_recursive): o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(dst, "carrinha_provisoria.glb"), export_format="GLB", use_selection=True, export_animations=True, export_lights=False, export_apply=True)
    print("exportado:", os.listdir(dst))
print("carro real:", real, "| frames:", NF)
