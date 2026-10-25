"""Iluminação cinematográfica: sol dourado baixo (frente-direita), contraluz azul-petróleo, mundo escuro teal, bloom no compositor."""
import math
import bpy

def setup(scene, map_m):
    bpy.ops.object.light_add(type="SUN"); sun = bpy.context.object; sun.name = "Sol"
    sun.data.energy = 2.4; sun.data.color = (1.0, 0.84, 0.64); sun.data.angle = math.radians(2.5)
    sun.rotation_euler = (math.radians(62), 0, math.radians(-40))  # baixo e lateral: sombras longas, brilho na carroçaria
    bpy.ops.object.light_add(type="AREA"); rim = bpy.context.object; rim.name = "ContraluzAzul"
    rim.data.energy = 2200; rim.data.color = (0.30, 0.58, 1.0); rim.data.size = 12
    rim.location = (-map_m*0.35, map_m*0.55, map_m*0.3); rim.rotation_euler = (math.radians(58), 0, math.radians(-145))
    bpy.ops.object.light_add(type="AREA"); fill = bpy.context.object; fill.name = "Preenchimento"
    fill.data.energy = 500; fill.data.color = (0.9, 0.85, 0.8); fill.data.size = 20; fill.location = (map_m*0.2, -map_m*0.3, map_m*0.5); fill.rotation_euler = (math.radians(30), 0, math.radians(20))
    w = bpy.data.worlds.new("Mundo"); scene.world = w; w.use_nodes = True; bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.010, 0.040, 0.075, 1); bg.inputs["Strength"].default_value = 0.5
    return sun, rim

def follow(sun, point, car_len):
    """Sol e sombra acompanham o carro para manter a sombra nítida perto da câmara."""
    sun.location = (point.x + car_len*3, point.y - car_len*2, car_len*6)

def color_management(scene):
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"; scene.view_settings.exposure = -0.2
    scene.view_settings.gamma = 1.0

def bloom(scene, threshold=1.3, strength=0.5, size=0.85):
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
