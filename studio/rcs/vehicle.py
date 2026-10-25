"""Veículo: carrega models/car.glb (o seu carro) ou constrói um coupé PROVISÓRIO genérico.
Convenção: frente para +X, cima +Z, chão em z=0, comprimento L (unidades de cena)."""
import bpy, bmesh, math, os
from mathutils import Vector
from . import materials as M

def _collection(name):
    col = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col); return col

def _arc(cx, cy, r, a0, a1, n=12): return [(cx + r*math.cos(a0 + (a1-a0)*i/n), cy + r*math.sin(a0 + (a1-a0)*i/n)) for i in range(n+1)]

def procedural(L):
    s = L/4.6; col = _collection("Carro")
    paint, glass = M.car_paint(), M.car_glass()
    trim = M.simple("Plastico", (0.02, 0.02, 0.022), 0.55); tyre = M.simple("Pneu", (0.012, 0.012, 0.012), 0.9)
    rim = M.simple("Jante", (0.22, 0.23, 0.25), 0.28, 1.0); hub = M.simple("Cubo", (0.15, 0.16, 0.18), 0.4, 0.9)
    head = M.emissive("Farol", (0.85, 0.92, 1.0), 6); tail = M.emissive("Farolim", (1.0, 0.08, 0.05), 10, base=(0.3, 0.02, 0.02))
    def extrude_profile(name, pts, width, bevel, mat, z0=0.0):
        me = bpy.data.meshes.new(name); bm = bmesh.new()
        vs = [bm.verts.new((x*s, -width*s/2, (y+z0)*s)) for x, y in pts]; f = bm.faces.new(vs)
        r = bmesh.ops.extrude_face_region(bm, geom=[f]); verts = [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0, width*s, 0), verts=verts); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); col.objects.link(ob); ob.data.materials.append(mat)
        mod = ob.modifiers.new("bevel", "BEVEL"); mod.width = bevel*s; mod.segments = 6; mod.limit_method = "ANGLE"; mod.angle_limit = math.radians(40)
        for p in ob.data.polygons: p.use_smooth = True
        return ob
    body_pts = ([(-2.25,.46),(-2.32,.66),(-2.28,.96),(-2.0,1.03),(-1.5,1.04),(-1.0,1.07),(-.55,1.40),(.5,1.42),(1.0,1.28),(1.42,1.0),(1.95,.95),(2.3,.8),(2.34,.5),(2.3,.46),(1.96,.46)]
                + _arc(1.45,.46,.51,0,math.pi)[1:-1] + [(.94,.46),(-.94,.46)] + _arc(-1.45,.46,.51,0,math.pi)[1:-1] + [(-1.96,.46)])
    extrude_profile("Carroçaria", body_pts, 1.74, .11, paint)
    extrude_profile("Vidros", [(-1.3,1.0),(-.95,1.03),(-.5,1.36),(.48,1.38),(.95,1.25),(1.33,.98)], 1.6, .03, glass, .02)
    def box(name, dims, loc, mat):
        bpy.ops.mesh.primitive_cube_add(size=1); o = bpy.context.object; o.name = name; o.scale = tuple(v*s for v in dims); o.location = tuple(v*s for v in loc)
        for c in o.users_collection: c.objects.unlink(o)
        col.objects.link(o); o.data.materials.append(mat); return o
    box("Tejadilho", (.92,1.46,.035), (0,0,1.435), paint); box("Splitter", (.18,1.82,.06), (2.3,0,.42), trim); box("Difusor", (.2,1.7,.1), (-2.26,0,.44), trim); box("Grelha", (.06,.78,.24), (2.34,0,.66), trim)
    for y in (1.02,-1.02): box("Espelho", (.2,.14,.09), (.9,y,1.08), paint)
    for y in (.6,-.6): box("Farol", (.05,.5,.1), (2.33,y,.82), head); box("Farolim", (.05,.62,.08), (-2.31,y,.86), tail)
    for x, y in ((1.45,.97),(1.45,-.97),(-1.45,.97),(-1.45,-.97)):
        for r_, d, mat, nm in ((.42,.3,tyre,"Pneu"),(.33,.31,rim,"Jante"),(.07,.34,hub,"Cubo")):
            bpy.ops.mesh.primitive_cylinder_add(radius=r_*s, depth=d*s, vertices=48, location=(x*s, y*s, .42*s), rotation=(math.pi/2,0,0)); o = bpy.context.object
            for c in o.users_collection: c.objects.unlink(o)
            col.objects.link(o); o.data.materials.append(mat); o.name = nm
            if nm == "Pneu": o.modifiers.new("bevel", "BEVEL").width = .03*s
    root = bpy.data.objects.new("CarroRoot", None); col.objects.link(root)
    for o in list(col.objects):
        if o is not root: o.parent = root
    return root

def load(L, glb_path):
    """Devolve (root, real: bool). Com GLB: mede o comprimento, escala para L, assenta no chão."""
    if os.path.exists(glb_path):
        try:
            before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=glb_path); new = [o for o in bpy.data.objects if o not in before]
            root = bpy.data.objects.new("CarroRoot", None); bpy.context.collection.objects.link(root)
            for o in new:
                if o.parent is None: o.parent = root
            pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
            xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
            length = max(max(xs)-min(xs), max(ys)-min(ys)); k = L/length; root.scale = (k, k, k); root.location.z = -min(zs)*k
            for o in new:
                if o.type == "MESH": o.cast_shadow = True if hasattr(o, "cast_shadow") else None
            print("carro: models/car.glb"); return root, True
        except Exception as e: print("car.glb falhou, carro provisório:", e)
    print("carro: PROVISÓRIO (procedural, genérico — não é o BMW)"); return procedural(L), False
