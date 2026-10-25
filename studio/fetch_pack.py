"""Pacote de mapa offline para uma viagem (para renderizar localmente sem rede, ex.: no PC ou num servidor isolado).
Lê studio/pack.json: {"name": "...", "points": ["Ponte de Lima", "Valença", "Tui", "Vigo"], "buffer_km": 4}
Escreve studio/packs/<name>/:
  route.json      percurso OSRM (com passos: nomes e referências das estradas, ex. A3, A-55)
  tilejson.json   + tiles/{z}/{x}/{y}.pbf  (OpenFreeMap / OpenMapTiles, z0–13 na caixa, z14 no corredor da rota)
  glyphs/{fonte}/{intervalo}.pbf
  dem/{z}/{x}/{y}.png  altitude Terrarium (AWS Terrain Tiles, dados abertos) z8–12 no corredor
Atribuição obrigatória nos vídeos: © OpenStreetMap contributors · OpenMapTiles · OpenFreeMap; altitude: Mapzen/AWS Terrain Tiles.
"""
import gzip, json, math, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from rcs import routes

UA = routes.UA
CFG = json.load(open(os.path.join(HERE, "pack.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "packs", CFG["name"]); os.makedirs(OUT, exist_ok=True)
BUF = float(CFG.get("buffer_km", 4))

def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}), timeout=40) as r:
                b = r.read()
                return gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(2 * (i + 1))
        except Exception:
            if i == tries - 1: raise
            time.sleep(2 * (i + 1))

def tile_of(lat, lon, z):
    n = 2 ** z; x = int((lon + 180) / 360 * n); r = math.radians(lat)
    y = int((1 - math.asinh(math.tan(r)) / math.pi) / 2 * n); return x, y

# 1) pontos e percurso com passos
pts = [routes.geocode(p) if isinstance(p, str) else p for p in CFG["points"]]
coords = ";".join(f"{p['lon']},{p['lat']}" for p in pts)
j = json.loads(get(f"https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=true"))
r = j["routes"][0]
steps = [{"name": s.get("name", ""), "ref": s.get("ref", ""), "dist": s["distance"], "dur": s["duration"], "at": s["maneuver"]["location"][::-1], "type": s["maneuver"]["type"], "mod": s["maneuver"].get("modifier", "")} for leg in r["legs"] for s in leg["steps"]]
line = [[c[1], c[0]] for c in r["geometry"]["coordinates"]]
json.dump({"points": pts, "route": line, "distance": r["distance"], "duration": r["duration"], "steps": steps}, open(os.path.join(OUT, "route.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(f"rota: {r['distance']/1000:.1f} km, {len(line)} pontos, {len(steps)} passos")

# 2) caixa e corredor
lats = [p[0] for p in line]; lons = [p[1] for p in line]
dlat = BUF * 2.5 / 111.0; dlon = dlat / math.cos(math.radians(sum(lats) / len(lats)))
S, N, Wl, E = min(lats) - dlat, max(lats) + dlat, min(lons) - dlon, max(lons) + dlon
def corridor(z, km):
    s = set(); step = max(1, len(line) // 4000); d = km / 111.0
    for la, lo in line[::step]:
        for a in (-d, 0, d):
            for b in (-d, 0, d):
                s.add(tile_of(la + a, lo + b / math.cos(math.radians(la)), z))
    return s
def box(z):
    x0, y0 = tile_of(N, Wl, z); x1, y1 = tile_of(S, E, z)
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}

# 3) tiles vetoriais OpenFreeMap
tj = json.loads(get("https://tiles.openfreemap.org/planet")); json.dump(tj, open(os.path.join(OUT, "tilejson.json"), "w"))
tmpl = tj["tiles"][0]; want = []
for z in range(0, 14): want += [(z, x, y) for x, y in box(z)]
want += [(14, x, y) for x, y in corridor(14, BUF)]
n = 0; size = 0
for z, x, y in want:
    p = os.path.join(OUT, "tiles", str(z), str(x), f"{y}.pbf")
    if os.path.exists(p): continue
    b = get(tmpl.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y)))
    if b is None: continue
    os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b); n += 1; size += len(b)
print(f"tiles vetoriais: {n} ({size/1e6:.1f} MB)")

# 4) glifos das fontes (latim + pontuação)
for fs in ("Noto Sans Regular", "Noto Sans Bold", "Noto Sans Italic"):
    for rg in ("0-255", "256-511", "8192-8447"):
        b = get(f"https://tiles.openfreemap.org/fonts/{urllib.request.quote(fs)}/{rg}.pbf")
        if b:
            p = os.path.join(OUT, "glyphs", fs, f"{rg}.pbf"); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b)

# 5) altitude (Terrarium PNG, dados abertos)
m = 0
for z in range(8, 13):
    for x, y in (box(z) if z <= 10 else corridor(z, BUF)):
        p = os.path.join(OUT, "dem", str(z), str(x), f"{y}.png")
        if os.path.exists(p): continue
        b = get(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png")
        if b: os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b); m += 1
print(f"altitude: {m} tiles")
open(os.path.join(OUT, "ATRIBUICAO.txt"), "w", encoding="utf-8").write("© OpenStreetMap contributors (ODbL) · OpenMapTiles · OpenFreeMap\nAltitude: Mapzen Terrain Tiles (AWS Open Data), fontes SRTM/EU-DEM e outras\nRotas: OSRM (project-osrm.org)\n")
