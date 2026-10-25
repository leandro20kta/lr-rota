"""Rota Cinema Studio — passo 2: cena e render no Blender (Cycles).
Uso:  blender -b -P studio/render_blender.py -- [opções]   ou   python -c "import bpy" + exec (modo módulo)
Variáveis de ambiente: W,H (resolução), SAMPLES, FPS, DUR (segundos), FRAMES ("1-150" ou "10,80,140"),
STILL_P (lista de progressos 0..1 para stills, ex. "0.3,0.55,0.9"), DEVICE (CPU|GPU), OUTDIR.
"""
import bpy, json, math, os, sys
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.environ.get('OUTDIR', os.path.join(ROOT, 'out'))
S = json.load(open(os.path.join(OUT, 'scene.json'), encoding='utf-8'))
W, H = int(os.environ.get('W', 1280)), int(os.environ.get('H', 720)); SAMPLES = int(os.environ.get('SAMPLES', 64))
FPS, DUR = int(os.environ.get('FPS', 30)), float(os.environ.get('DUR', 20)); NF = int(FPS*DUR)
MAP_M = S.get('map_m', 20.0)
route = [Vector((p[0], p[1], 0.0)) for p in S['route']]
# comprimento acumulado para amostrar por distância
cum = [0.0]
for i in range(1, len(route)): cum.append(cum[-1] + (route[i]-route[i-1]).length)
TOTAL = cum[-1]
span = max(max(abs(p.x) for p in route), max(abs(p.y) for p in route))*2
CAR_L = max(0.6, min(1.25, span*0.11))

def at(u):
    d = max(0.0, min(1.0, u))*TOTAL; lo, hi = 0, len(cum)-1
    while hi-lo > 1:
        mid = (lo+hi)//2
        if cum[mid] <= d: lo = mid
        else: hi = mid
    seg = cum[hi]-cum[lo]; t = 0 if seg == 0 else (d-cum[lo])/seg
    p = route[lo].lerp(route[hi], t); tan = (route[hi]-route[lo]);
    if tan.length < 1e-6: tan = Vector((1,0,0))
    return p, tan.normalized()
def tangent_smooth(u, k=0.004):
    a, _ = at(max(0, u-k)); b, _ = at(min(1, u+k)); d = b-a
    return d.normalized() if d.length > 1e-6 else Vector((1,0,0))

# ---------- cena limpa ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NF
cy = sc.cycles; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.use_denoising = True; cy.max_bounces = 6; cy.caustics_reflective = False; cy.caustics_refractive = False
if os.environ.get('DEVICE', 'CPU').upper() == 'GPU':
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for ct in ('OPTIX', 'CUDA', 'HIP', 'METAL'):
            try: prefs.compute_device_type = ct; prefs.get_devices(); break
            except Exception: continue
        for d in prefs.devices: d.use = True
        cy.device = 'GPU'
    except Exception as e: print('GPU indisponível, CPU:', e)
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = -0.15
sc.render.film_transparent = False; sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'

def mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; return m, m.node_tree, m.node_tree.nodes['Principled BSDF']
def img_tex(nt, path, colorspace='sRGB'):
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(path); n.image.colorspace_settings.name = colorspace; return n

# ---------- mapa de papel ----------
bpy.ops.mesh.primitive_plane_add(size=MAP_M); plane = bpy.context.object; plane.name = 'Mapa'
m, nt, bsdf = mat('Papel'); tex = img_tex(nt, os.path.join(OUT, 'map.png'))
noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 900; noise.inputs['Detail'].default_value = 6
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.06; bump.inputs['Distance'].default_value = 0.002
nt.links.new(noise.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color']); bsdf.inputs['Roughness'].default_value = 0.72; bsdf.inputs['Specular IOR Level'].default_value = 0.35
plane.data.materials.append(m)
# detalhe do corredor (4x) por cima
d = S['detail']; bpy.ops.mesh.primitive_plane_add(size=1); det = bpy.context.object; det.name = 'Detalhe'
det.scale = (d['w'], d['h'], 1); det.location = (d['x0'] + d['w']/2, d['y0'] - d['h']/2, 0.0015)
m2, nt2, b2 = mat('PapelDetalhe'); t2 = img_tex(nt2, os.path.join(OUT, 'detail.png'))
nt2.links.new(t2.outputs['Color'], b2.inputs['Base Color']); nt2.links.new(t2.outputs['Alpha'], b2.inputs['Alpha']); b2.inputs['Roughness'].default_value = 0.72; b2.inputs['Specular IOR Level'].default_value = 0.35
bump2 = nt2.nodes.new('ShaderNodeBump'); bump2.inputs['Strength'].default_value = 0.06; bump2.inputs['Distance'].default_value = 0.002
noise2 = nt2.nodes.new('ShaderNodeTexNoise'); noise2.inputs['Scale'].default_value = 900; nt2.links.new(noise2.outputs['Fac'], bump2.inputs['Height']); nt2.links.new(bump2.outputs['Normal'], b2.inputs['Normal'])
m2.blend_method = 'BLEND' if hasattr(m2, 'blend_method') else None; det.data.materials.append(m2)
# base/mesa por baixo
bpy.ops.mesh.primitive_cube_add(size=1); table = bpy.context.object; table.scale = (MAP_M*1.04, MAP_M*1.04, 0.25); table.location = (0, 0, -0.126)
mt, ntt, bt = mat('Mesa'); bt.inputs['Base Color'].default_value = (0.08, 0.06, 0.05, 1); bt.inputs['Roughness'].default_value = 0.8; table.data.materials.append(mt)

# ---------- rota luminosa (curva com bevel, revelada por bevel_factor_end) ----------
def make_route(name, radius, emission, strength, alpha=1.0):
    cd = bpy.data.curves.new(name, 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = radius; cd.bevel_resolution = 6; cd.fill_mode = 'FULL'; cd.use_fill_caps = True
    sp = cd.splines.new('POLY'); sp.points.add(len(route)-1)
    for i, p in enumerate(route): sp.points[i].co = (p.x, p.y, radius*0.9 + 0.002, 1.0)
    ob = bpy.data.objects.new(name, cd); bpy.context.collection.objects.link(ob)
    mr = bpy.data.materials.new(name+'M'); mr.use_nodes = True; nr = mr.node_tree; nr.nodes.clear()
    em = nr.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = emission; em.inputs['Strength'].default_value = strength
    out = nr.nodes.new('ShaderNodeOutputMaterial')
    if alpha < 1:
        tr = nr.nodes.new('ShaderNodeBsdfTransparent'); mix = nr.nodes.new('ShaderNodeMixShader'); mix.inputs['Fac'].default_value = alpha
        nr.links.new(tr.outputs[0], mix.inputs[1]); nr.links.new(em.outputs[0], mix.inputs[2]); nr.links.new(mix.outputs[0], out.inputs['Surface'])
        if hasattr(mr, 'blend_method'): mr.blend_method = 'BLEND'
    else: nr.links.new(em.outputs[0], out.inputs['Surface'])
    ob.data.materials.append(mr); ob.visible_shadow = False; return ob
tube = make_route('Rota', CAR_L*0.028, (1.0, 0.33, 0.08, 1), 9.0)
halo = make_route('RotaHalo', CAR_L*0.075, (1.0, 0.42, 0.12, 1), 1.2, alpha=0.28)

# ---------- carro ----------
def procedural_car(L):
    s = L/4.6; col = bpy.data.collections.new('Carro'); bpy.context.scene.collection.children.link(col)
    import bmesh
    def extrude_profile(name, pts, width, bevel, material, z0=0.0):
        me = bpy.data.meshes.new(name); bm = bmesh.new()
        vs = [bm.verts.new((x*s, -width*s/2, (y+z0)*s)) for x, y in pts]; f = bm.faces.new(vs)
        r = bmesh.ops.extrude_face_region(bm, geom=[f]); verts = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0, width*s, 0), verts=verts); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); col.objects.link(ob); ob.data.materials.append(material)
        mod = ob.modifiers.new('bevel', 'BEVEL'); mod.width = bevel*s; mod.segments = 5; mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(40)
        for p in ob.data.polygons: p.use_smooth = True
        return ob
    def arc(cx, cy, r, a0, a1, n=10): return [(cx + r*math.cos(a0 + (a1-a0)*i/n), cy + r*math.sin(a0 + (a1-a0)*i/n)) for i in range(n+1)]
    body_pts = [(-2.25,.46),(-2.32,.66),(-2.28,.96),(-2.0,1.03),(-1.5,1.04),(-1.0,1.07),(-.55,1.40),(.5,1.42),(1.0,1.28),(1.42,1.0),(1.95,.95),(2.3,.8),(2.34,.5),(2.3,.46),(1.96,.46)] + arc(1.45,.46,.51,0,math.pi)[1:-1] + [(.94,.46),(-.94,.46)] + arc(-1.45,.46,.51,0,math.pi)[1:-1] + [(-1.96,.46)]
    paint, nt, b = mat('Pintura'); b.inputs['Base Color'].default_value = (0.012, 0.013, 0.016, 1); b.inputs['Metallic'].default_value = 0.35; b.inputs['Roughness'].default_value = 0.28; b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.06
    glass, ntg, bg = mat('Vidro'); bg.inputs['Base Color'].default_value = (0.02, 0.04, 0.07, 1); bg.inputs['Metallic'].default_value = 0.2; bg.inputs['Roughness'].default_value = 0.06; bg.inputs['Coat Weight'].default_value = 1.0
    trim, _, btm = mat('Plastico'); btm.inputs['Base Color'].default_value = (0.02, 0.02, 0.022, 1); btm.inputs['Roughness'].default_value = 0.55
    tyre, _, bty = mat('Pneu'); bty.inputs['Base Color'].default_value = (0.012, 0.012, 0.012, 1); bty.inputs['Roughness'].default_value = 0.9
    rim, _, brm = mat('Jante'); brm.inputs['Base Color'].default_value = (0.75, 0.77, 0.8, 1); brm.inputs['Metallic'].default_value = 1.0; brm.inputs['Roughness'].default_value = 0.22
    hl, nth, bh = mat('Farol'); bh.inputs['Emission Color'].default_value = (0.85, 0.92, 1.0, 1); bh.inputs['Emission Strength'].default_value = 6
    tl, ntl, btl = mat('Farolim'); btl.inputs['Base Color'].default_value = (0.3,0.02,0.02,1); btl.inputs['Emission Color'].default_value = (1.0, 0.08, 0.05, 1); btl.inputs['Emission Strength'].default_value = 10
    body = extrude_profile('Carroçaria', body_pts, 1.74, .11, paint)
    cab = extrude_profile('Vidros', [(-1.3,1.0),(-.95,1.03),(-.5,1.36),(.48,1.38),(.95,1.25),(1.33,.98)], 1.6, .03, glass, .02)
    def box(name, dims, loc, material):
        bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name; o.scale = tuple(v*s for v in dims); o.location = tuple(v*s for v in loc)
        for c in o.users_collection: c.objects.unlink(o)
        col.objects.link(o); o.data.materials.append(material); return o
    box('Tejadilho', (.92,1.46,.035), (0,0,1.435), paint); box('Splitter', (.18,1.82,.06), (2.3,0,.42), trim); box('Difusor', (.2,1.7,.1), (-2.26,0,.44), trim); box('Grelha', (.06,.78,.24), (2.34,0,.66), trim)
    for y in (1.02,-1.02): box('Espelho', (.2,.14,.09), (.9,y,1.08), paint)
    for y in (.6,-.6): box('Farol', (.05,.5,.1), (2.33,y,.82), hl); box('Farolim', (.05,.62,.08), (-2.31,y,.86), tl)
    for x, y in ((1.45,.97),(1.45,-.97),(-1.45,.97),(-1.45,-.97)):
        bpy.ops.mesh.primitive_cylinder_add(radius=.42*s, depth=.3*s, vertices=48, location=(x*s, y*s, .42*s), rotation=(math.pi/2,0,0)); t = bpy.context.object
        for c in t.users_collection: c.objects.unlink(t)
        col.objects.link(t); t.data.materials.append(tyre); t.name = 'Pneu'
        bpy.ops.mesh.primitive_cylinder_add(radius=.29*s, depth=.32*s, vertices=32, location=(x*s, y*s, .42*s), rotation=(math.pi/2,0,0)); r = bpy.context.object
        for c in r.users_collection: c.objects.unlink(r)
        col.objects.link(r); r.data.materials.append(rim); r.name = 'Jante'
    root = bpy.data.objects.new('CarroRoot', None); col.objects.link(root)
    for o in list(col.objects):
        if o is not root: o.parent = root
    return root, False

def load_car(L):
    glb = os.path.join(ROOT, '..', 'models', 'car.glb')
    if os.path.exists(glb):
        try:
            before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=glb); new = [o for o in bpy.data.objects if o not in before]
            root = bpy.data.objects.new('CarroRoot', None); bpy.context.collection.objects.link(root)
            tops = [o for o in new if o.parent is None]
            for o in tops: o.parent = root
            xs = [v.x for o in new if o.type == 'MESH' for v in (o.matrix_world @ Vector(c) for c in o.bound_box)]
            ys = [v.y for o in new if o.type == 'MESH' for v in (o.matrix_world @ Vector(c) for c in o.bound_box)]
            zs = [v.z for o in new if o.type == 'MESH' for v in (o.matrix_world @ Vector(c) for c in o.bound_box)]
            length = max(max(xs)-min(xs), max(ys)-min(ys)); k = L/length; root.scale = (k, k, k); root.location.z = -min(zs)*k
            print('carro: models/car.glb'); return root, True
        except Exception as e: print('car.glb falhou, carro provisório:', e)
    print('carro: PROVISÓRIO (procedural)'); return procedural_car(L)
car, car_real = load_car(CAR_L)

# ---------- luz e ambiente ----------
bpy.ops.object.light_add(type='SUN'); sun = bpy.context.object; sun.data.energy = 3.2; sun.data.color = (1.0, 0.86, 0.68); sun.data.angle = math.radians(3.5); sun.rotation_euler = (math.radians(52), 0, math.radians(-35))
bpy.ops.object.light_add(type='AREA'); rimL = bpy.context.object; rimL.data.energy = 1500; rimL.data.color = (0.35, 0.62, 1.0); rimL.data.size = 10; rimL.location = (-MAP_M*0.4, MAP_M*0.5, MAP_M*0.35); rimL.rotation_euler = (math.radians(55), 0, math.radians(-140))
sc.world = bpy.data.worlds.new('Mundo'); sc.world.use_nodes = True; wn = sc.world.node_tree; bgn = wn.nodes['Background']; bgn.inputs['Color'].default_value = (0.02, 0.07, 0.12, 1); bgn.inputs['Strength'].default_value = 0.6

# ---------- câmara com DOF ----------
bpy.ops.object.camera_add(); cam = bpy.context.object; sc.camera = cam; cam.data.lens = 50; cam.data.sensor_width = 36
cam.data.dof.use_dof = True; cam.data.dof.focus_object = car; cam.data.dof.aperture_fstop = 2.2
focus_empty = bpy.data.objects.new('Foco', None); bpy.context.collection.objects.link(focus_empty); cam.data.dof.focus_object = focus_empty

def ease(t): return 4*t*t*t if t < .5 else 1 - ((-2*t+2)**3)/2
def smooth(a, b, t): return min(1, max(0, (t-a)/(b-a)))
def look_at(obj, target):
    d = target - obj.location; obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

state = {'cam': None, 'look': None}
def pose(p):
    draw = ease(smooth(.10, .42, p)); carU = ease(smooth(.22, .86, p)); reveal = ease(smooth(.84, 1, p))
    tube.data.bevel_factor_end = max(0.0005, carU); halo.data.bevel_factor_end = max(0.0005, draw)
    cu = max(0.0005, min(.9995, carU)); cp, _ = at(cu); ct = tangent_smooth(cu); up = Vector((0,0,1)); right = ct.cross(up).normalized()
    car.location = (cp.x, cp.y, 0.0); car.rotation_euler = (0, 0, math.atan2(ct.y, ct.x)); car.hide_render = p < .2
    origin = route[0]; head = cp + ct*CAR_L*0.9
    far = Vector((origin.x + span*.9, origin.y - span*1.1, span*1.25)); near = Vector((origin.x + CAR_L*2.4, origin.y - CAR_L*3.0, CAR_L*1.6))
    chase = cp - ct*CAR_L*3.3 + right*CAR_L*1.45 + up*CAR_L*0.95; over = Vector((span*.1, -span*.85, span*1.35))
    if p < .22: t = ease(smooth(0, .22, p)); camp = far.lerp(near, t); look = Vector((origin.x, origin.y, 0))
    elif p < .84: camp = chase; look = Vector((head.x, head.y, CAR_L*0.3))
    else: camp = chase.lerp(over, reveal); look = Vector((head.x, head.y, CAR_L*0.3)).lerp(Vector((0,0,0)), reveal)
    if state['cam'] is None or p < .22: state['cam'] = camp.copy(); state['look'] = look.copy()
    state['cam'] = state['cam'].lerp(camp, .14); state['look'] = state['look'].lerp(look, .16)
    cam.location = state['cam']; look_at(cam, state['look']); focus_empty.location = state['look'] if p >= .22 else Vector((origin.x, origin.y, 0))
    cam.data.dof.aperture_fstop = 2.0 if .22 <= p < .84 else 5.6
    sun.location = (cp.x + 3, cp.y - 2, 6)

# ---------- compositor: bloom suave (Blender 5: grupo de nós de composição) ----------
try:
    if hasattr(sc, 'compositing_node_group'):
        ct = bpy.data.node_groups.new('Composicao', 'CompositorNodeTree'); sc.compositing_node_group = ct
    else:
        sc.use_nodes = True; ct = sc.node_tree
    ct.nodes.clear(); rl = ct.nodes.new('CompositorNodeRLayers'); gl = ct.nodes.new('CompositorNodeGlare')
    outn = ct.nodes.new('NodeGroupOutput') if hasattr(sc, 'compositing_node_group') else ct.nodes.new('CompositorNodeComposite')
    if hasattr(sc, 'compositing_node_group'): ct.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    try: gl.glare_type = 'BLOOM'
    except Exception:
        try: gl.inputs['Type'].default_value = 'Bloom'
        except Exception: pass
    for k, v in (('Threshold', 1.0), ('Strength', 0.3), ('Size', 0.6), ('Quality', 'High')):
        try: gl.inputs[k].default_value = v
        except Exception: pass
    ct.links.new(rl.outputs['Image'], gl.inputs['Image']); ct.links.new(gl.outputs['Image'], outn.inputs[0]); print('compositor: bloom ok')
except Exception as e: print('compositor:', e)

# ---------- render ----------
os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
stills = [float(x) for x in os.environ.get('STILL_P', '').split(',') if x.strip()]
frames = os.environ.get('FRAMES', '')
def render_to(path):
    sc.render.filepath = path; bpy.ops.render.render(write_still=True); print('render', path)
if stills:
    for sp in stills:
        state['cam'] = None
        for k in range(0, 60): pose(max(0, sp - (60-k)*0.004))  # aquecer a câmara (suavização) até ao instante pedido
        pose(sp); render_to(os.path.join(OUT, 'frames', f'still_{int(sp*100):03d}.png'))
else:
    if '-' in frames: a, b = [int(x) for x in frames.split('-')]; sel = range(a, b+1)
    elif frames: sel = [int(x) for x in frames.split(',')]
    else: sel = range(1, NF+1)
    state['cam'] = None; last = 0
    for f in range(1, NF+1):
        pose((f-1)/(NF-1))
        if f in sel: render_to(os.path.join(OUT, 'frames', f'f{f:04d}.png'))
print('carro real:', car_real, '| NF', NF, '| CAR_L', round(CAR_L, 3), '| span', round(span, 2))
