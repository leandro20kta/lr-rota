"""Módulo mapas: renderiza a textura do mapa (atlas impresso) com MapLibre GL em Chromium headless.
Fonte: tiles vetoriais OpenFreeMap (grátis, sem chave, uso automatizado permitido com User-Agent; atribuição obrigatória).
Saída: PNG quadrado de `size` px cobrindo um quadrado Web-Mercator centrado em (lat, lon) ao zoom calculado.
"""
import json, math, os, sys, time
from .style_atlas import style, PAPER

UA = "LR-Rota-Cinema-Studio/0.2 (YouTube Leandro na Rota; github.com/leandro20kta/lr-rota)"
HERE = os.path.dirname(os.path.abspath(__file__)); VENDOR = os.path.join(HERE, "..", "vendor", "maplibre")

def lon2x(lon, z): return (lon + 180) / 360 * 512 * 2**z
def lat2y(lat, z):
    r = math.radians(lat); return (1 - math.log(math.tan(r) + 1/math.cos(r)) / math.pi) / 2 * 512 * 2**z

def fit_zoom(bounds, size, fill=0.72):
    """zoom fracionário para que a bbox ocupe `fill` do lado do quadrado de `size` px (CSS)."""
    z = 0.0
    w = lon2x(bounds["maxLon"], z) - lon2x(bounds["minLon"], z); h = lat2y(bounds["minLat"], z) - lat2y(bounds["maxLat"], z)
    return math.log2(size * fill / max(w, h, 1e-9))

def render(center_lat, center_lon, zoom, css_size, pixel_ratio, out_png, style_obj=None, timeout_s=240, log=print):
    from playwright.sync_api import sync_playwright
    st = json.dumps(style_obj or style())
    html = f"""<!doctype html><html><head><meta charset=utf-8>
<link rel=stylesheet href="file://{VENDOR}/maplibre-gl.css"><script src="file://{VENDOR}/maplibre-gl.js"></script>
<style>html,body{{margin:0;background:{PAPER}}}#m{{width:{css_size}px;height:{css_size}px}}</style></head><body><div id=m></div>
<script>
window.__errors=[]; window.__done=false;
const map = new maplibregl.Map({{container:'m', style:{st}, center:[{center_lon},{center_lat}], zoom:{zoom}, pixelRatio:{pixel_ratio},
  interactive:false, attributionControl:false, fadeDuration:0, canvasContextAttributes:{{preserveDrawingBuffer:true, antialias:true}}, maxTileCacheSize:4000, maxCanvasSize:[8192,8192]}});
map.on('error', e => {{ const m = e && e.error ? (e.error.message || String(e.error)) : JSON.stringify(e); window.__errors.push(m); }});
map.once('load', () => {{ map.once('idle', () => {{ window.__done = true; }}); }});
</script></body></html>"""
    tmp = os.path.join(os.path.dirname(out_png), "_map.html"); open(tmp, "w", encoding="utf-8").write(html)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"])
        ctx = b.new_context(viewport={"width": css_size, "height": css_size}, device_scale_factor=pixel_ratio, user_agent=UA)
        page = ctx.new_page(); page.on("console", lambda m: log("  [browser]", m.text[:160]) if m.type in ("error", "warning") else None)
        page.goto("file://" + tmp); t0 = time.time()
        while time.time() - t0 < timeout_s:
            if page.evaluate("window.__done"): break
            page.wait_for_timeout(500)
        else:
            errs = page.evaluate("window.__errors"); b.close(); raise RuntimeError("mapa: timeout a carregar tiles; erros: " + "; ".join(errs[:5]))
        errs = page.evaluate("window.__errors")
        bad = [e for e in errs if "tile" not in e.lower() and "404" not in e]
        if bad: log("  avisos MapLibre:", bad[:5])
        page.wait_for_timeout(300)
        data = page.evaluate("document.querySelector('#m canvas').toDataURL('image/png')")
        b.close()
    import base64; open(out_png, "wb").write(base64.b64decode(data.split(",", 1)[1]))
    log(f"  mapa {css_size*pixel_ratio}px @z{zoom:.2f} em {time.time()-t0:.0f}s, {os.path.getsize(out_png)//1024} KB")
    return out_png

def build(route, out_dir, size_px=6144, scale=2.2, fill=0.78, log=print):
    """Renderiza a textura para a rota (lista [lat, lon]). Devolve dict com zoom, centro, lado em px e função lat/lon→px."""
    lats = [p[0] for p in route]; lons = [p[1] for p in route]
    b = dict(minLat=min(lats), maxLat=max(lats), minLon=min(lons), maxLon=max(lons))
    pr = 2 if size_px > 4096 else 1; css = size_px // pr
    z = fit_zoom(b, css, fill); z = max(4.0, min(16.0, z))
    cx = (lon2x(b["minLon"], z) + lon2x(b["maxLon"], z)) / 2; cy = (lat2y(b["minLat"], z) + lat2y(b["maxLat"], z)) / 2
    clat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * cy / (512 * 2**z))))); clon = cx / (512 * 2**z) * 360 - 180
    out = os.path.join(out_dir, "map.png")
    st = style(scale)
    try: render(clat, clon, z, css, pr, out, style_obj=st, log=log)
    except Exception as e:
        if pr > 1:
            log("  ", size_px, "falhou (", str(e)[:80], ") → ", css); pr = 1; size_px = css; render(clat, clon, z, css, 1, out, style_obj=st, log=log)
        else: raise
    ox, oy = cx - css / 2, cy - css / 2
    def to_px(lat, lon):  # px CSS no quadrado (0..css)
        return lon2x(lon, z) - ox, lat2y(lat, z) - oy
    return dict(zoom=z, center=[clat, clon], css=css, px=size_px, to_px=to_px, bounds=b)
