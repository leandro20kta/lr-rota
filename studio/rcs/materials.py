"""Materiais (Blender): papel do mapa, pintura do carro, vidro, rota emissiva."""
import bpy

def principled(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]

def paper_map(image_path, strength_bump=0.05):
    """Mapa impresso: textura, fibras de papel (bump), sheen leve para o aspeto macro."""
    m, nt, b = principled("Papel")
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(image_path); tex.image.colorspace_settings.name = "sRGB"
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    fib = nt.nodes.new("ShaderNodeTexNoise"); fib.inputs["Scale"].default_value = 2600; fib.inputs["Detail"].default_value = 8; fib.inputs["Roughness"].default_value = 0.7
    wave = nt.nodes.new("ShaderNodeTexNoise"); wave.inputs["Scale"].default_value = 6; wave.inputs["Detail"].default_value = 2
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "FLOAT"; mix.inputs["Factor"].default_value = 0.35
    nt.links.new(fib.outputs["Fac"], mix.inputs[2]); nt.links.new(wave.outputs["Fac"], mix.inputs[3])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = strength_bump; bump.inputs["Distance"].default_value = 0.003
    nt.links.new(mix.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.62; b.inputs["Specular IOR Level"].default_value = 0.45
    b.inputs["Sheen Weight"].default_value = 0.25; b.inputs["Sheen Roughness"].default_value = 0.6
    return m

def car_paint(rgb=(0.010, 0.011, 0.014)):
    m, _, b = principled("Pintura")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Metallic"].default_value = 0.55; b.inputs["Roughness"].default_value = 0.24
    b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Coat Roughness"].default_value = 0.04; b.inputs["Specular IOR Level"].default_value = 0.6
    return m

def car_glass():
    m, _, b = principled("Vidro")
    b.inputs["Base Color"].default_value = (0.015, 0.03, 0.05, 1); b.inputs["Metallic"].default_value = 0.1; b.inputs["Roughness"].default_value = 0.05
    b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Specular IOR Level"].default_value = 0.8
    return m

def simple(name, rgb, rough=0.5, metal=0.0):
    m, _, b = principled(name); b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal; return m

def emissive(name, rgb, strength, base=None):
    m, _, b = principled(name); b.inputs["Base Color"].default_value = (*(base or rgb), 1)
    b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = strength; return m

def route_glow(rgb=(1.0, 0.36, 0.09), strength=5.0):
    """Rota luminosa: emissão pura (o brilho suave vem do bloom no compositor)."""
    m = bpy.data.materials.new("Rota"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*rgb, 1); em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs["Surface"]); return m
