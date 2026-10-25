"""Materiais (Blender/Cycles): papel impresso, pintura automóvel, vidro, borracha, jantes, luzes, rota."""
import bpy

def principled(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']; return m, nt, b

def image(nt, path, colorspace='sRGB'):
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(path); n.image.colorspace_settings.name = colorspace; return n

def paper(name, image_path, with_alpha=False, folds=True):
    """Mapa impresso: cor da imagem, verniz acetinado leve, fibra de papel e vincos de dobra."""
    m, nt, b = principled(name); tex = image(nt, image_path)
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    if with_alpha: nt.links.new(tex.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.52; b.inputs['Specular IOR Level'].default_value = 0.35
    b.inputs['Coat Weight'].default_value = 0.12; b.inputs['Coat Roughness'].default_value = 0.35
    # fibra: ruído fino
    fib = nt.nodes.new('ShaderNodeTexNoise'); fib.inputs['Scale'].default_value = 1400; fib.inputs['Detail'].default_value = 8; fib.inputs['Roughness'].default_value = 0.7
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.045; bump.inputs['Distance'].default_value = 0.0015
    nt.links.new(fib.outputs['Fac'], bump.inputs['Height'])
    if folds:
        # vincos: duas dobras suaves (wave) misturadas com a fibra
        wave = nt.nodes.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'X'; wave.inputs['Scale'].default_value = 0.11; wave.inputs['Distortion'].default_value = 0.3
        ramp = nt.nodes.new('ShaderNodeMapRange'); ramp.inputs['From Min'].default_value = 0.985; ramp.inputs['From Max'].default_value = 1.0
        nt.links.new(wave.outputs['Fac'], ramp.inputs['Value'])
        mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'ADD'; nt.links.new(fib.outputs['Fac'], mix.inputs[0]); nt.links.new(ramp.outputs['Result'], mix.inputs[1])
        nt.links.new(mix.outputs['Value'], bump.inputs['Height']); bump.inputs['Strength'].default_value = 0.09
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    if with_alpha and hasattr(m, 'blend_method'): m.blend_method = 'BLEND'
    return m

def table(name='Mesa'):
    m, nt, b = principled(name); b.inputs['Base Color'].default_value = (0.025, 0.03, 0.04, 1); b.inputs['Roughness'].default_value = 0.65; return m

def car_paint(name='Pintura', color=(0.010, 0.011, 0.014)):
    m, nt, b = principled(name); b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Metallic'].default_value = 0.55; b.inputs['Roughness'].default_value = 0.24
    b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.03; b.inputs['Specular IOR Level'].default_value = 0.6; return m

def car_glass(name='Vidro'):
    m, nt, b = principled(name); b.inputs['Base Color'].default_value = (0.015, 0.03, 0.05, 1); b.inputs['Metallic'].default_value = 0.25; b.inputs['Roughness'].default_value = 0.04; b.inputs['Coat Weight'].default_value = 1.0; return m

def plastic(name='Plastico'):
    m, nt, b = principled(name); b.inputs['Base Color'].default_value = (0.018, 0.018, 0.02, 1); b.inputs['Roughness'].default_value = 0.5; return m

def rubber(name='Pneu'):
    m, nt, b = principled(name); b.inputs['Base Color'].default_value = (0.012, 0.012, 0.012, 1); b.inputs['Roughness'].default_value = 0.85; return m

def rim(name='Jante'):
    m, nt, b = principled(name); b.inputs['Base Color'].default_value = (0.78, 0.8, 0.83, 1); b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.2; return m

def lamp(name, color, strength, base=(0.9, 0.95, 1.0)):
    m, nt, b = principled(name); b.inputs['Base Color'].default_value = (*base, 1); b.inputs['Emission Color'].default_value = (*color, 1); b.inputs['Emission Strength'].default_value = strength; return m

def emission(name, color, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], out.inputs['Surface']); return m
