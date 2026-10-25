#!/usr/bin/env python3
"""Rota Cinema Studio — passo 1: dados reais.
trip.json (origem/destino/paragens como texto ou coordenadas) → rota real (OSRM) + textura do mapa (OpenFreeMap via MapLibre)
→ out/map.png, out/scene.json (rota e paragens em unidades de cena; plano do mapa = MAP_M).
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcs import routes, maps

ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.environ.get("OUTDIR", os.path.join(ROOT, "out")); os.makedirs(OUT, exist_ok=True)
MAP_M = 20.0; SIZE = int(os.environ.get("MAP_PX", "6144")); SCALE = float(os.environ.get("MAP_SCALE", "1.35"))

def main():
    t0 = time.time()
    trip = json.load(open(os.path.join(ROOT, "trip.json"), encoding="utf-8"))
    trip = routes.resolve_trip(trip)
    print(f"rota: {trip['origin']['name']} → {trip['dest']['name']}, {len(trip['route'])} pontos, {trip['distance']/1000:.1f} km, {trip['duration']/60:.0f} min")
    m = maps.build(trip["route"], OUT, size_px=SIZE, scale=SCALE, log=print)
    css = m["css"]
    def w(lat, lon):
        px, py = m["to_px"](lat, lon); return [round((px/css - .5)*MAP_M, 4), round(-(py/css - .5)*MAP_M, 4)]
    scene = dict(origin=trip["origin"], dest=trip["dest"], stops=[dict(s, xy=w(s["lat"], s["lon"])) for s in trip["stops"]],
                 distance=trip["distance"], duration=trip["duration"], route=[w(p[0], p[1]) for p in trip["route"]],
                 map_px=m["px"], zoom=round(m["zoom"], 3), map_m=MAP_M, source="OpenFreeMap / OpenMapTiles / OpenStreetMap",
                 car_glb=os.path.exists(os.path.join(ROOT, "..", "models", "car.glb")))
    json.dump(scene, open(os.path.join(OUT, "scene.json"), "w"), ensure_ascii=False)
    print(f"ok em {time.time()-t0:.0f}s")

if __name__ == "__main__": main()
