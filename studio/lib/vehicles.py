"""Veículos: carrega models/car.glb (o carro real) ou constrói um coupé provisório genérico.
Convenção: frente para +X, cima +Z, chão em z=0, comprimento L em unidades de cena."""
import bpy, bmesh, math, os
from mathutils import Vector
from . import materials as M

def _arc(cx, cy, r, a0, a1, n=12): return [(cx + r*math.cos(a0 + (a1-a0)*i/n), cy + r*math.sin(a0 + (a1-a0)*i/n)) for i in range(n+1)]

def _extrude_profile(col, name, pts, width, s, material, bevel=0.1, subsurf=0, z0=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((x*s, -width*s/2, (y+z0)*s)) for x, y in pts]; f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f]); verts = [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, width*s, 0), verts=verts); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); col.objects.link(ob); ob.data.materials.append(material)
    if bevel > 0:
        mod = ob.modifiers.new('bevel', 'BEVEL'); mod.width = bevel*s; mod.segments = 6; mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(35)
    if subsurf: sm = ob.modifiers.new('subsurf', 'SUBSURF'); sm.levels = subsurf; sm.render_levels = subsurf
    for p in ob.data.polygons: p.use_smooth = True
    return ob

def _prim(col, op, material, name, s, **kw):
    op(**kw); o = bpy.context.object; o.name = name
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o); o.data.materials.append(material)
    for p in o.data.polygons: p.use_smooth = True
    return o

def procedural_coupe(L, paint_color=(0.010, 0.011, 0.014)):
    """Coupé genérico PROVISÓRIO (não é um BMW). Comprimento L."""
    s = L/4.6; col = bpy.data.collections.new('Carro'); bpy.context.scene.collection.children.link(col)
    paint = M.car_paint(color=paint_color); glass = M.car_glass(); trim = M.plastic(); tyre = M.rubber(); rimm = M.rim()
    body_pts = [(-2.25,.5),(-2.33,.7),(-2.28,.98),(-2.0,1.04),(-1.5,1.05),(-1.05,1.08),(-.6,1.38),(.45,1.4),(.95,1.28),(1.4,1.02),(1.95,.96),(2.3,.82),(2.35,.55),(2.3,.5),(1.98,.5)] + _arc(1.45,.5,.5,0,math.pi)[1:-1] + [(.92,.5),(-.92,.5)] + _arc(-1.45,.5,.5,0,math.pi)[1:-1] + [(-1.98,.5)]
    body = _extrude_profile(col, 'Carroçaria', body_pts, 1.76, s, paint, bevel=.12, subsurf=1)
    cab = _extrude_profile(col, 'Vidros', [(-1.32,1.02),(-.98,1.05),(-.55,1.35),(.44,1.37),(.92,1.25),(1.33,1.0)], 1.62, s, glass, bevel=.03, z0=.015)
    bx = lambda name, dims, loc, mat: _prim(col, bpy.ops.mesh.primitive_cube_add, mat, name, s, size=1)
    def box(name, dims, loc, mat):
        o = bx(name, dims, loc, mat); o.scale = tuple(v*s for v in dims); o.location = tuple(v*s for v in loc); return o
    box('Tejadilho', (.9,1.5,.03), (-.05,0,1.41), paint); box('Splitter', (.16,1.84,.05), (2.32,0,.47), trim); box('Difusor', (.18,1.72,.09), (-2.28,0,.49), trim); box('Grelha', (.05,.8,.22), (2.36,0,.7), trim)
    for y in (1.0,-1.0): box('Espelho', (.18,.13,.08), (.92,y,1.1), paint)
    hl = M.lamp('Farol', (0.85, 0.92, 1.0), 5.0); tl = M.lamp('Farolim', (1.0, 0.07, 0.04), 9.0, base=(0.3, 0.02, 0.02))
    for y in (.6,-.6): box('Farol', (.04,.46,.09), (2.35,y,.84), hl); box('Farolim', (.04,.6,.07), (-2.33,y,.88), tl)
    for x, y in ((1.45,.98),(1.45,-.98),(-1.45,.98),(-1.45,-.98)):
        t = _prim(col, bpy.ops.mesh.primitive_cylinder_add, tyre, 'Pneu', s, radius=.43*s, depth=.3*s, vertices=56, location=(x*s, y*s, .43*s), rotation=(math.pi/2,0,0))
        r = _prim(col, bpy.ops.mesh.primitive_cylinder_add, rimm, 'Jante', s, radius=.3*s, depth=.32*s, vertices=40, location=(x*s, y*s, .43*s), rotation=(math.pi/2,0,0))
        for i in range(5):
            sp = _prim(col, bpy.ops.mesh.primitive_cube_add, trim, 'Raio', s, size=1); sp.scale = (.06*s, .05*s, .5*s); sp.location = (x*s, (y + (.17 if y > 0 else -.17))*s, .43*s); sp.rotation_euler = (0, i*math.pi*2/5, 0)
    root = bpy.data.objects.new('CarroRoot', None); col.objects.link(root)
    for o in list(col.objects):
        if o is not root: o.parent = root
    return root

def load(L, models_dir):
    """Devolve (root, real): real=True quando models/car.glb foi carregado."""
    glb = os.path.join(models_dir, 'car.glb')
    if os.path.exists(glb):
        try:
            before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=glb); new = [o for o in bpy.data.objects if o not in before]
            root = bpy.data.objects.new('CarroRoot', None); bpy.context.collection.objects.link(root)
            for o in new:
                if o.parent is None: o.parent = root
                if o.type == 'MESH':
                    o.cycles.use_motion_blur = False
                    for p in o.data.polygons: p.use_smooth = True
            pts = [o.matrix_world @ Vector(c) for o in new if o.type == 'MESH' for c in o.bound_box]
            xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
            length = max(max(xs)-min(xs), max(ys)-min(ys)); k = L/length; root.scale = (k, k, k); root.location.z = -min(zs)*k
            print('carro: models/car.glb (real)'); return root, True
        except Exception as e: print('car.glb falhou, usa provisório:', e)
    print('carro: PROVISÓRIO genérico (não é o BMW)'); return procedural_coupe(L), False
