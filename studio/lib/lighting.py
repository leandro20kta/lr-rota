"""Iluminação cinematográfica: chave quente suave (área grande), preenchimento azul-petróleo, contraluz, mundo escuro."""
import bpy, math

def setup(scene, map_m=20.0):
    bpy.ops.object.light_add(type='AREA'); key = bpy.context.object; key.name = 'Chave'
    key.data.energy = 2600; key.data.color = (1.0, 0.80, 0.60); key.data.size = 5.5; key.data.shape = 'SQUARE'
    key.location = (4.5, -4.0, 6.0); key.rotation_euler = (math.radians(42), 0, math.radians(48))
    bpy.ops.object.light_add(type='AREA'); fill = bpy.context.object; fill.name = 'Preenchimento'
    fill.data.energy = 900; fill.data.color = (0.38, 0.62, 1.0); fill.data.size = 9; fill.location = (-7, 6, 5); fill.rotation_euler = (math.radians(50), 0, math.radians(-130))
    bpy.ops.object.light_add(type='SPOT'); rim = bpy.context.object; rim.name = 'Contraluz'
    rim.data.energy = 1800; rim.data.color = (0.55, 0.78, 1.0); rim.data.spot_size = math.radians(60); rim.data.spot_blend = 0.6; rim.data.shadow_soft_size = 1.2
    rim.location = (-2, 7, 4); rim.rotation_euler = (math.radians(58), 0, math.radians(-165))
    scene.world = bpy.data.worlds.new('Mundo'); scene.world.use_nodes = True; wn = scene.world.node_tree; bg = wn.nodes['Background']
    bg.inputs['Color'].default_value = (0.010, 0.038, 0.072, 1); bg.inputs['Strength'].default_value = 0.45
    return key, fill, rim

def follow(key, fill, rim, cp, car_l):
    """As luzes acompanham o carro para manter a mesma direção de luz em toda a viagem."""
    key.location = (cp.x + car_l*3.5, cp.y - car_l*3.2, car_l*5.0); fill.location = (cp.x - car_l*6, cp.y + car_l*5, car_l*4.5); rim.location = (cp.x - car_l*1.5, cp.y + car_l*6, car_l*3.5)
