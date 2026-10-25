"""Iluminação cinematográfica: sol dourado baixo (frente-direita), contraluz azul-petróleo, mundo escuro teal, bloom no compositor."""
import math
import bpy

def setup(scene, map_m):
    bpy.ops.object.light_add(type="SUN"); sun = bpy.context.object; sun.name = "Sol"
    sun.data.energy = 0.55; sun.data.color = (1.0, 0.84, 0.64); sun.data.angle = math.radians(2.5)
    sun.rotation_euler = (math.radians(62), 0, math.radians(-40))  # baixo e lateral: sombras longas, brilho na carroçaria
    bpy.ops.object.light_add(type="AREA"); rim = bpy.context.object; rim.name = "ContraluzAzul"
    rim.data.energy = 3800; rim.data.color = (0.30, 0.58, 1.0); rim.data.size = 12
    rim.location = (-map_m*0.35, map_m*0.55, map_m*0.3); rim.rotation_euler = (math.radians(58), 0, math.radians(-145))
    bpy.ops.object.light_add(type="AREA"); fill = bpy.context.object; fill.name = "Preenchimento"
    fill.data.energy = 30; fill.data.color = (0.9, 0.85, 0.8); fill.data.size = 20; fill.location = (map_m*0.2, -map_m*0.3, map_m*0.5); fill.rotation_euler = (math.radians(30), 0, math.radians(20))
    bpy.ops.object.light_add(type="SPOT"); spot = bpy.context.object; spot.name = "PoçoDeLuz"
    spot.data.energy = 1600; spot.data.color = (1.0, 0.86, 0.68); spot.data.spot_size = math.radians(30); spot.data.spot_blend = 0.85; spot.data.shadow_soft_size = 0.4
    w = bpy.data.worlds.new("Mundo"); scene.world = w; w.use_nodes = True; bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.010, 0.040, 0.075, 1); bg.inputs["Strength"].default_value = 0.3
    return sun, rim, spot

def follow(sun, point, car_len, spot=None, ahead=None):
    """Sol e poço de luz acompanham o carro: o mapa à volta cai para a sombra (efeito miniatura de estúdio)."""
    sun.location = (point.x + car_len*3, point.y - car_len*2, car_len*6)
    if spot is not None:
        tgt = point if ahead is None else point.lerp(ahead, 0.5)
        spot.location = (tgt.x + car_len*1.2, tgt.y - car_len*1.6, car_len*7)
        d = tgt - spot.location; spot.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def color_management(scene):
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"; scene.view_settings.exposure = -0.9
    scene.view_settings.gamma = 1.0

def bloom(scene, threshold=1.6, strength=0.45, size=0.8):
    try:
        if hasattr(scene, "compositing_node_group"):
            ct = bpy.data.node_groups.new("Composicao", "CompositorNodeTree"); scene.compositing_node_group = ct
            ct.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor"); outn = ct.nodes.new("NodeGroupOutput")
        else:
            scene.use_nodes = True; ct = scene.node_tree; ct.nodes.clear(); outn = ct.nodes.new("CompositorNodeComposite")
        rl = ct.nodes.new("CompositorNodeRLayers"); gl = ct.nodes.new("CompositorNodeGlare")
        try: gl.glare_type = "BLOOM"
        except Exception:
            try: gl.inputs["Type"].default_value = "Bloom"
            except Exception: pass
        for k, v in (("Threshold", threshold), ("Strength", strength), ("Size", size), ("Quality", "High")):
            try: gl.inputs[k].default_value = v
            except Exception: pass
        ct.links.new(rl.outputs["Image"], gl.inputs["Image"]); ct.links.new(gl.outputs["Image"], outn.inputs[0]); print("compositor: bloom ok")
    except Exception as e: print("compositor:", e)
