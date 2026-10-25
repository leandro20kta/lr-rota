"""Módulo rotas: geocodificação (Nominatim) e percurso real por estrada (OSRM). Sem chaves."""
import json, time, urllib.parse, urllib.request
UA = "LR-Rota-Cinema-Studio/0.2 (YouTube Leandro na Rota; github.com/leandro20kta/lr-rota)"

def _get(url, retries=3):
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r: return r.read()
        except Exception:
            if i == retries - 1: raise
            time.sleep(1.5 * (i + 1))

def geocode(text):
    """'Ponte de Lima' → {name, lat, lon}. Usa o nome curto devolvido pelo Nominatim."""
    j = json.loads(_get("https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&accept-language=pt&q=" + urllib.parse.quote(text)))
    if not j: raise ValueError("Lugar não encontrado: " + text)
    h = j[0]; name = (h.get("name") or h["display_name"].split(",")[0]).strip()
    time.sleep(1.1)  # política Nominatim: ≤1 pedido/s
    return {"name": name, "lat": float(h["lat"]), "lon": float(h["lon"])}

def route(points):
    """points: lista de {lat, lon}. Devolve (coords [[lat,lon],...], distância m, duração s)."""
    coords = ";".join(f"{p['lon']},{p['lat']}" for p in points)
    j = json.loads(_get(f"https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=false"))
    if j.get("code") != "Ok": raise RuntimeError("OSRM: " + str(j)[:200])
    r = j["routes"][0]
    return [[c[1], c[0]] for c in r["geometry"]["coordinates"]], r["distance"], r["duration"]

def resolve_trip(trip):
    """Aceita origem/destino/paragens como texto ou {name,lat,lon}; devolve o trip completo com rota."""
    def pt(x): return geocode(x) if isinstance(x, str) else x
    t = dict(trip); t["origin"] = pt(trip["origin"]); t["dest"] = pt(trip["dest"]); t["stops"] = [pt(s) for s in trip.get("stops", [])]
    if not (t.get("route") and len(t["route"]) > 10):
        t["route"], t["distance"], t["duration"] = route([t["origin"]] + t["stops"] + [t["dest"]])
    return t
