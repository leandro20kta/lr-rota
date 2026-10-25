#!/usr/bin/env python3
"""Rota Cinema Studio — passo 1: dados reais.
Lê studio/trip.json (origem, destino, paragens[, route]), pede a rota real ao OSRM quando falta,
descarrega tiles OpenStreetMap e compõe: out/map.png (base, toda a área), out/detail.png (corredor da
rota com 4x detalhe) e out/scene.json (rota e paragens em unidades de cena; plano do mapa = 20 m).
"""
import json, math, os, sys, time, urllib.request
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'out'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'LR-Rota-Cinema-Studio/0.1 (YouTube Leandro na Rota; github.com/leandro20kta/lr-rota)'}
TEX = int(os.environ.get('TEX', '4096')); MAP_M = 20.0

def get(url, retries=3):
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r: return r.read()
        except Exception:
            if i == retries-1: raise
            time.sleep(1.5*(i+1))

def lon2x(lon, z): return (lon+180)/360 * 2**z * 256
def lat2y(lat, z):
    r = math.radians(lat); return (1 - math.log(math.tan(r) + 1/math.cos(r))/math.pi)/2 * 2**z * 256

def paper(img):
    img = ImageEnhance.Color(img).enhance(1.7); img = ImageEnhance.Contrast(img).enhance(1.25); img = ImageEnhance.Brightness(img).enhance(0.96)
    r, g, b = img.split()
    return Image.merge('RGB', (r.point(lambda v: v*0.95), g.point(lambda v: v*0.90), b.point(lambda v: v*0.78)))

def main():
    trip = json.load(open(os.path.join(ROOT, 'trip.json'), encoding='utf-8'))
    pts = [trip['origin']] + trip.get('stops', []) + [trip['dest']]
    if 'route' in trip and len(trip['route']) > 10:
        route = trip['route']; dist = trip.get('distance', 0); dur = trip.get('duration', 0)
    else:
        coords = ';'.join(f"{p['lon']},{p['lat']}" for p in pts)
        j = json.loads(get(f'https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson'))
        if j.get('code') != 'Ok': sys.exit('OSRM: ' + str(j))
        r = j['routes'][0]; route = [[c[1], c[0]] for c in r['geometry']['coordinates']]; dist = r['distance']; dur = r['duration']
    lats = [p[0] for p in route]; lons = [p[1] for p in route]
    b = dict(minLat=min(lats), maxLat=max(lats), minLon=min(lons), maxLon=max(lons))
    z = 18
    while z > 3:
        w = lon2x(b['maxLon'], z) - lon2x(b['minLon'], z); h = lat2y(b['minLat'], z) - lat2y(b['maxLat'], z)
        if max(w, h) < TEX*0.55: break
        z -= 1
    cx = (lon2x(b['minLon'], z) + lon2x(b['maxLon'], z))/2; cy = (lat2y(b['minLat'], z) + lat2y(b['maxLat'], z))/2
    ox, oy = cx - TEX/2, cy - TEX/2
    # base
    img = Image.new('RGB', (TEX, TEX), (232, 224, 208)); n = 0
    for tx in range(int(ox//256), int((ox+TEX)//256)+1):
        for ty in range(int(oy//256), int((oy+TEX)//256)+1):
            try:
                im = Image.open(BytesIO(get(f'https://tile.openstreetmap.org/{z}/{tx}/{ty}.png'))).convert('RGB')
                img.paste(im, (int(tx*256-ox), int(ty*256-oy))); n += 1
            except Exception as e: print('tile', z, tx, ty, e)
    print(f'base z={z}: {n} tiles')
    img = paper(img)
    vign = Image.new('L', img.size, 0); ImageDraw.Draw(vign).ellipse([-TEX*0.1, -TEX*0.1, TEX*1.1, TEX*1.1], fill=255); vign = vign.filter(ImageFilter.GaussianBlur(TEX*0.12))
    img = Image.composite(img, Image.new('RGB', img.size, (46, 34, 22)), vign.point(lambda v: 90 + v*165//255))
    img.save(os.path.join(OUT, 'map.png'), optimize=True)
    # detalhe: tiles z+2 (4x) no corredor, num atlas próprio à resolução nativa
    zd = z + 2; F = 4; S = 256/F; want = set()
    for i in range(0, len(route), 2):
        px = lon2x(route[i][1], z) - ox; py = lat2y(route[i][0], z) - oy
        tx0 = int(px*F//256); ty0 = int(py*F//256)
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                if dx*dx+dy*dy <= 30: want.add((tx0+dx, ty0+dy))
    txs = [t[0] for t in want]; tys = [t[1] for t in want]; mtx, mty = min(txs), min(tys)
    aw, ah = (max(txs)-mtx+1)*256, (max(tys)-mty+1)*256
    atlas = Image.new('RGBA', (aw, ah), (0, 0, 0, 0)); m = 0
    for (tx, ty) in sorted(want):
        try:
            im = Image.open(BytesIO(get(f'https://tile.openstreetmap.org/{zd}/{tx}/{ty}.png'))).convert('RGB')
            atlas.paste(paper(im).convert('RGBA'), ((tx-mtx)*256, (ty-mty)*256)); m += 1
        except Exception as e: print('tile', zd, tx, ty, e)
    print(f'detail z={zd}: {m} tiles, atlas {aw}x{ah}')
    atlas.save(os.path.join(OUT, 'detail.png'), optimize=True)
    # unidades de cena: plano de MAP_M metros centrado; x para este, y para norte
    def w(px, py): return [round((px/TEX - .5)*MAP_M, 4), round(-(py/TEX - .5)*MAP_M, 4)]
    def wll(p): return w(lon2x(p[1], z) - ox, lat2y(p[0], z) - oy)
    # o atlas cobre, em px da base, [mtx*S, (mtx+aw/256)*S] etc.
    dx0, dy0 = mtx*S - ox, mty*S - oy; dw, dh = aw/256*S, ah/256*S
    scene = dict(origin=trip['origin'], dest=trip['dest'], stops=[dict(s, xy=wll([s['lat'], s['lon']])) for s in trip.get('stops', [])],
                 distance=dist, duration=dur, route=[wll(p) for p in route], tex=TEX, zoom=z, map_m=MAP_M,
                 detail=dict(x0=w(dx0, dy0)[0], y0=w(dx0, dy0)[1], w=dw/TEX*MAP_M, h=dh/TEX*MAP_M),
                 car_glb=os.path.exists(os.path.join(ROOT, '..', 'models', 'car.glb')))
    json.dump(scene, open(os.path.join(OUT, 'scene.json'), 'w'), ensure_ascii=False)
    print('ok', len(route), 'pontos', round(dist/1000, 1), 'km')

if __name__ == '__main__': main()
