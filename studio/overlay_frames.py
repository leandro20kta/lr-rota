#!/usr/bin/env python3
"""Rota Cinema Studio — passo 3: sobreposição 2D nos frames renderizados.
Chip "LEANDRO NA ROTA", título manuscrito, contador km/custo e crédito OpenStreetMap (obrigatório).
Uso: python studio/overlay_frames.py [pasta_frames] — grava *.ov.png ao lado dos originais.
"""
import json, os, sys, glob, math, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.environ.get('OUTDIR', os.path.join(ROOT, 'out'))
FR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'frames')
S = json.load(open(os.path.join(OUT, 'scene.json'), encoding='utf-8'))
try: settings = json.load(open(os.path.join(ROOT, 'settings.json')))
except Exception: settings = {}
cons, price, fuel = settings.get('cons', 6.5), settings.get('price', 1.72), settings.get('fuel', 'Gasóleo')

def font(name, size):
    cands = {'hand': ['Caveat-Bold.ttf', '/usr/share/fonts/truetype/caveat/Caveat-Bold.ttf'], 'sans': ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'DejaVuSans-Bold.ttf', 'Inter-Bold.ttf']}[name]
    for c in cands:
        for p in (os.path.join(ROOT, 'fonts', c), c):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()

def eur(n): return '€' + f'{n:.2f}'.replace('.', ',')
def km(m): return (f'{m/1000:.1f}' if m < 10000 else f'{round(m/1000)}').replace('.', ',') + ' km'
def ease(t): return 4*t*t*t if t < .5 else 1 - ((-2*t+2)**3)/2
def smooth(a, b, t): return min(1, max(0, (t-a)/(b-a)))

def overlay(path, p):
    im = Image.open(path).convert('RGBA'); W, H = im.size; k = W/1280
    # vinheta
    vg = Image.new('L', (W, H), 0); ImageDraw.Draw(vg).ellipse([-W*.15, -H*.35, W*1.15, H*1.35], fill=255); vg = vg.filter(ImageFilter.GaussianBlur(W*.12))
    dark = Image.new('RGBA', (W, H), (2, 8, 16, 150)); im = Image.composite(im, Image.alpha_composite(im, dark), vg)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([32*k, 32*k, 332*k, 86*k], radius=27*k, fill=(10, 91, 214, 255)); d.text((58*k, 46*k), 'LEANDRO NA ROTA', font=font('sans', int(19*k)), fill='white')
    fh = font('hand', int(60*k)); t1 = S['origin']['name'] + '  '; t2 = '  ' + S['dest']['name']; w1 = d.textlength(t1, font=fh); aw = 54*k
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh); sd.text((38*k, 96*k), t1, font=fh, fill=(0, 0, 0, 170)); sd.text((38*k + w1 + aw, 96*k), t2, font=fh, fill=(0, 0, 0, 170))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(6*k))); d = ImageDraw.Draw(im)
    d.text((36*k, 94*k), t1, font=fh, fill=(255, 246, 226, 255)); d.text((36*k + w1 + aw, 94*k), t2, font=fh, fill=(255, 246, 226, 255))
    ay = 94*k + 40*k; ax = 36*k + w1; d.line([(ax, ay), (ax + aw - 6*k, ay)], fill=(255, 246, 226, 255), width=int(4*k)); d.line([(ax + aw - 18*k, ay - 12*k), (ax + aw - 4*k, ay), (ax + aw - 18*k, ay + 12*k)], fill=(255, 246, 226, 255), width=int(4*k), joint='curve')
    q = ease(smooth(.22, .86, p)); dd = S['distance']*q
    txt = f"{km(dd)} · {eur(dd/1000*cons/100*price)} {fuel.lower()} · {round(S['duration']/60)} min"; fs = font('sans', int(21*k)); tw = d.textlength(txt, font=fs) + 40*k
    d.rounded_rectangle([32*k, H-86*k, 32*k+tw, H-32*k], radius=14*k, fill=(10, 16, 28, 205), outline=(255, 106, 42, 210), width=int(2*k)); d.text((52*k, H-70*k), txt, font=fs, fill='white')
    cred = 'Data from OpenStreetMap · OpenMapTiles · OpenFreeMap · openstreetmap.org/copyright'; fc = font('sans', int(13*k)); cw = d.textlength(cred, font=fc)
    d.rounded_rectangle([W-cw-44*k, H-52*k, W-16*k, H-20*k], radius=8*k, fill=(0, 0, 0, 120)); d.text((W-cw-30*k, H-44*k), cred, font=fc, fill=(255, 255, 255, 230))
    return im.convert('RGB')

files = sorted(glob.glob(os.path.join(FR, 'f*.png')) + glob.glob(os.path.join(FR, 'still_*.png')))
files = [f for f in files if not f.endswith('.ov.png')]
nf = len([f for f in files if os.path.basename(f).startswith('f')]) or 1
for f in files:
    b = os.path.basename(f)
    p = int(b[6:9])/100 if b.startswith('still_') else (int(b[1:5])-1)/max(1, nf-1)
    overlay(f, p).save(f[:-4] + '.ov.png'); print('ov', b)
