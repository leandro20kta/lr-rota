"""Estilo MapLibre "atlas impresso" sobre tiles vetoriais OpenFreeMap (esquema OpenMapTiles).
Cores de papel quente, florestas suaves, água teal, estradas com casing como num atlas rodoviário, rótulos grandes.
Atribuição obrigatória: Data from OpenStreetMap · OpenMapTiles · OpenFreeMap (gravada nos frames pelo overlay)."""

TILEJSON = "https://tiles.openfreemap.org/planet"
GLYPHS = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf"
PAPER = "#F1E7D2"

def _road(id_, classes, color, width, casing=None, cwidth=0, minzoom=0, dash=None):
    f = ["all", ["in", ["get", "class"], ["literal", classes]], ["!=", ["get", "brunnel"], "tunnel"]]
    layers = []
    if casing:
        layers.append({"id": id_ + "-casing", "type": "line", "source": "omt", "source-layer": "transportation", "minzoom": minzoom, "filter": f,
                       "layout": {"line-cap": "round", "line-join": "round"}, "paint": {"line-color": casing, "line-width": cwidth}})
    paint = {"line-color": color, "line-width": width}
    if dash: paint["line-dasharray"] = dash
    layers.append({"id": id_, "type": "line", "source": "omt", "source-layer": "transportation", "minzoom": minzoom, "filter": f,
                   "layout": {"line-cap": "round", "line-join": "round"}, "paint": paint})
    return layers

SCALE = 1.0  # escala "impressa": multiplica larguras e tipos (definida por style(scale))
def _w(base, k=1.0):
    # largura interpolada por zoom (px): base a z10, cresce até z15
    b = base*SCALE
    return ["interpolate", ["exponential", 1.4], ["zoom"], 8, b*0.5*k, 11, b*k, 15, b*3.2*k]

def _label(id_, layer, filt, size, font, color, halo, minzoom=0, field="name:latin", upper=False, maxw=8, letter=0.0, pad=4):
    text = ["coalesce", ["get", field], ["get", "name"]]
    if upper: text = ["upcase", text]
    return {"id": id_, "type": "symbol", "source": "omt", "source-layer": layer, "minzoom": minzoom, "filter": filt,
            "layout": {"text-field": text, "text-font": [font], "text-size": size, "text-max-width": maxw, "text-letter-spacing": letter, "text-padding": pad, "text-anchor": "center"},
            "paint": {"text-color": color, "text-halo-color": halo, "text-halo-width": round(1.6*SCALE,1), "text-halo-blur": 0.4}}

def style(scale=1.0):
    global SCALE; SCALE = scale; T = lambda px: round(px*scale, 1)
    L = []
    L.append({"id": "bg", "type": "background", "paint": {"background-color": PAPER}})
    L.append({"id": "landcover-wood", "type": "fill", "source": "omt", "source-layer": "landcover", "filter": ["in", ["get", "class"], ["literal", ["wood", "forest"]]],
              "paint": {"fill-color": "#C9D7A8", "fill-opacity": 0.75}})
    L.append({"id": "landcover-grass", "type": "fill", "source": "omt", "source-layer": "landcover", "filter": ["in", ["get", "class"], ["literal", ["grass", "farmland", "scrub", "wetland"]]],
              "paint": {"fill-color": "#DFE4BC", "fill-opacity": 0.55}})
    L.append({"id": "park", "type": "fill", "source": "omt", "source-layer": "park", "paint": {"fill-color": "#C6D9A3", "fill-opacity": 0.6}})
    L.append({"id": "landuse-res", "type": "fill", "source": "omt", "source-layer": "landuse", "filter": ["in", ["get", "class"], ["literal", ["residential", "suburb", "neighbourhood"]]],
              "paint": {"fill-color": "#E6D9C0", "fill-opacity": 0.7}})
    L.append({"id": "landuse-ind", "type": "fill", "source": "omt", "source-layer": "landuse", "filter": ["in", ["get", "class"], ["literal", ["industrial", "commercial", "retail", "railway"]]],
              "paint": {"fill-color": "#DCD0C4", "fill-opacity": 0.6}})
    L.append({"id": "water", "type": "fill", "source": "omt", "source-layer": "water", "filter": ["!=", ["get", "brunnel"], "tunnel"], "paint": {"fill-color": "#9FC4D4"}})
    L.append({"id": "waterway", "type": "line", "source": "omt", "source-layer": "waterway", "filter": ["!=", ["get", "brunnel"], "tunnel"],
              "paint": {"line-color": "#8FB8CB", "line-width": _w(1.2)}})
    L.append({"id": "buildings", "type": "fill", "source": "omt", "source-layer": "building", "minzoom": 13, "paint": {"fill-color": "#D5C5AE", "fill-opacity": 0.8, "fill-outline-color": "#C2AE93"}})
    L.append({"id": "aeroway", "type": "line", "source": "omt", "source-layer": "aeroway", "paint": {"line-color": "#CFC8BC", "line-width": T(2)}})
    L += _road("rd-track", ["track", "path", "service"], "#CDBFA6", _w(0.5), minzoom=12)
    L += _road("rd-minor", ["minor"], "#FFFFFF", _w(1.3), casing="#B9A98C", cwidth=_w(1.3, 1.5), minzoom=10)
    L += _road("rd-tertiary", ["tertiary"], "#FFFFFF", _w(1.9), casing="#A89877", cwidth=_w(1.9, 1.45))
    L += _road("rd-secondary", ["secondary"], "#FFF4C2", _w(2.6), casing="#9C8A5C", cwidth=_w(2.6, 1.4))
    L += _road("rd-primary", ["primary"], "#F9DD7B", _w(3.2), casing="#8F7638", cwidth=_w(3.2, 1.35))
    L += _road("rd-trunk", ["trunk"], "#F3A95F", _w(3.6), casing="#8D5A22", cwidth=_w(3.6, 1.35))
    L += _road("rd-motorway", ["motorway"], "#E8603C", _w(4.0), casing="#7A2E12", cwidth=_w(4.0, 1.35))
    L.append({"id": "rail", "type": "line", "source": "omt", "source-layer": "transportation", "filter": ["all", ["==", ["get", "class"], "rail"], ["!=", ["get", "brunnel"], "tunnel"]],
              "paint": {"line-color": "#6B6560", "line-width": _w(1.0), "line-dasharray": [3, 3]}})
    L.append({"id": "boundary", "type": "line", "source": "omt", "source-layer": "boundary", "filter": ["all", ["has", "admin_level"], ["<=", ["to-number", ["get", "admin_level"]], 4]],
              "paint": {"line-color": "#8F6E8E", "line-width": T(1.2), "line-dasharray": [4, 2, 1, 2], "line-opacity": 0.8}})
    # rótulos: estrada (ref), água, lugares — grandes, como num atlas
    L.append({"id": "road-ref", "type": "symbol", "source": "omt", "source-layer": "transportation_name", "minzoom": 9,
              "filter": ["all", ["has", "ref"], ["in", ["get", "class"], ["literal", ["motorway", "trunk", "primary", "secondary"]]]],
              "layout": {"symbol-placement": "line", "text-field": ["get", "ref"], "text-font": ["Noto Sans Bold"], "text-size": T(11), "text-letter-spacing": 0.05, "symbol-spacing": 420, "text-rotation-alignment": "viewport", "text-pitch-alignment": "viewport"},
              "paint": {"text-color": "#3A2A14", "text-halo-color": "#FFF8E6", "text-halo-width": 2}})
    L.append({"id": "road-name", "type": "symbol", "source": "omt", "source-layer": "transportation_name", "minzoom": 13,
              "filter": ["in", ["get", "class"], ["literal", ["primary", "secondary", "tertiary", "minor"]]],
              "layout": {"symbol-placement": "line", "text-field": ["coalesce", ["get", "name:latin"], ["get", "name"]], "text-font": ["Noto Sans Regular"], "text-size": T(10), "symbol-spacing": 300},
              "paint": {"text-color": "#4A3A26", "text-halo-color": "#FFF8E6", "text-halo-width": 1.5}})
    L.append({"id": "water-name", "type": "symbol", "source": "omt", "source-layer": "water_name", "minzoom": 9,
              "layout": {"symbol-placement": "line", "text-field": ["coalesce", ["get", "name:latin"], ["get", "name"]], "text-font": ["Noto Sans Italic"], "text-size": T(13), "text-letter-spacing": 0.15},
              "paint": {"text-color": "#2F6F85", "text-halo-color": "#DCEDF3", "text-halo-width": 1.2}})
    L.append(_label("place-village", "place", ["in", ["get", "class"], ["literal", ["village", "hamlet", "suburb", "neighbourhood"]]], T(11), "Noto Sans Regular", "#3B2F20", "#F6EEDD", minzoom=10))
    L.append(_label("place-town", "place", ["==", ["get", "class"], "town"], T(16), "Noto Sans Bold", "#2A1F12", "#F6EEDD", minzoom=8, upper=False, letter=0.04))
    L.append(_label("place-city", "place", ["==", ["get", "class"], "city"], T(24), "Noto Sans Bold", "#1E150C", "#F6EEDD", minzoom=5, upper=True, letter=0.12, maxw=10))
    L.append({"id": "peak", "type": "symbol", "source": "omt", "source-layer": "mountain_peak", "minzoom": 11,
              "layout": {"text-field": ["concat", ["coalesce", ["get", "name:latin"], ["get", "name"]], "\n", ["to-string", ["coalesce", ["get", "ele"], ""]], " m"], "text-font": ["Noto Sans Italic"], "text-size": T(9), "text-offset": [0, 0.6], "text-anchor": "top"},
              "paint": {"text-color": "#5A4A33", "text-halo-color": "#F6EEDD", "text-halo-width": 1}})
    return {"version": 8, "name": "LR Rota — atlas", "glyphs": GLYPHS, "sources": {"omt": {"type": "vector", "url": TILEJSON}}, "layers": L}
