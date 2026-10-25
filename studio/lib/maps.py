"""Mapas — render MapLibre GL (OpenFreeMap, tiles vetoriais OSM) com estilo "papel impresso".
Produz: base.png (toda a área), detail.png (corredor da rota, alta resolução) e a projeção exata lon/lat→px
feita pelo próprio MapLibre, para que a rota no Blender fique exatamente sobre as estradas desenhadas.
Licença/atribuição: OpenFreeMap permite uso comercial e descarga até 3 000 tiles por pedido com User-Agent
próprio; crédito obrigatório "© OpenStreetMap contributors · OpenMapTiles · OpenFreeMap".
"""
import json, os, asyncio

STYLE_URL = os.environ.get('MAP_STYLE', 'https://tiles.openfreemap.org/styles/liberty')
UA = 'LR-Rota-Cinema-Studio/0.2 (YouTube Leandro na Rota; github.com/leandro20kta/lr-rota)'

PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<style>__CSS__</style>
<style>html,body{margin:0;background:#E8DFCB}#map{width:__W__px;height:__H__px}</style></head>
<body><div id="map"></div>
<script>__JS__</script>
<script>
const PAPER = {
  bg: '#E9E0CC', water: '#A7BFC8', wood: '#B7C094', green: '#CBD2A8', farm: '#DED8B8', residential: '#E3D9C3', building: '#D3C8AF',
  motorway: '#C4684C', trunk: '#CF7A4E', primary: '#D9A24A', secondary: '#E9D9A8', minor: '#FFFFFF', casing: '#B6AA91', rail: '#8E8574',
  path: '#B9AA8D', boundary: '#A38F78', river: '#8FB0BF', text: '#39302A', halo: '#EFE7D4'
};
function paperize(map){
  const st = map.getStyle();
  for(const l of st.layers){
    const id = l.id.toLowerCase(), t = l.type, set = (k, v) => { try{ map.setPaintProperty(l.id, k, v); }catch(e){} };
    if(t === 'background') set('background-color', PAPER.bg);
    else if(t === 'fill'){
      if(/water|ocean|lake|river/.test(id)) set('fill-color', PAPER.water);
      else if(/wood|forest/.test(id)) set('fill-color', PAPER.wood);
      else if(/park|grass|green|cemetery|golf|pitch|garden|scrub|meadow|landcover/.test(id)) set('fill-color', PAPER.green);
      else if(/farm|orchard|vineyard|agri/.test(id)) set('fill-color', PAPER.farm);
      else if(/building/.test(id)) { set('fill-color', PAPER.building); set('fill-outline-color', '#C2B59C'); }
      else if(/residential|urban|industrial|commercial|retail|landuse/.test(id)) set('fill-color', PAPER.residential);
      else if(/sand|beach|glacier|ice/.test(id)) set('fill-color', '#EADFBD');
      else set('fill-color', '#E0D6BE');
      set('fill-opacity', 1);
    }
    else if(t === 'line'){
      if(/motorway/.test(id)) set('line-color', /casing/.test(id) ? '#8E3F2A' : PAPER.motorway);
      else if(/trunk/.test(id)) set('line-color', /casing/.test(id) ? '#8E4F2A' : PAPER.trunk);
      else if(/primary/.test(id)) set('line-color', /casing/.test(id) ? '#9A6E2B' : PAPER.primary);
      else if(/secondary|tertiary/.test(id)) set('line-color', /casing/.test(id) ? PAPER.casing : PAPER.secondary);
      else if(/rail|transit/.test(id)) set('line-color', PAPER.rail);
      else if(/water|river|stream|canal/.test(id)) set('line-color', PAPER.river);
      else if(/boundary|admin/.test(id)) set('line-color', PAPER.boundary);
      else if(/path|footway|track|cycle|steps|pedestrian/.test(id)) set('line-color', PAPER.path);
      else if(/casing/.test(id)) set('line-color', PAPER.casing);
      else if(/road|street|minor|service|highway|link/.test(id)) set('line-color', PAPER.minor);
      else set('line-color', '#C9BFA6');
    }
    else if(t === 'symbol'){ set('text-color', PAPER.text); set('text-halo-color', PAPER.halo); set('text-halo-width', 1.4); set('icon-opacity', 0.6); }
    else if(t === 'fill-extrusion'){ try{ map.setLayoutProperty(l.id, 'visibility', 'none'); }catch(e){} }
  }
}
window.__ready = false; window.__err = null;
const route = __ROUTE__, pts = __POINTS__, pad = __PAD__;
const lons = route.map(p => p[1]), lats = route.map(p => p[0]);
const map = new maplibregl.Map({ container: 'map', style: __STYLE__, attributionControl: false, interactive: false, preserveDrawingBuffer: true, fadeDuration: 0, pixelRatio: __DPR__ });
map.on('error', e => { window.__err = (e && e.error && e.error.message) || String(e); });
map.on('load', () => {
  paperize(map);
  map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: pad, duration: 0 });
  map.once('idle', () => setTimeout(() => {
    const proj = p => { const q = map.project([p[1], p[0]]); return [q.x, q.y]; };
    const b = map.getBounds();
    window.__out = { zoom: map.getZoom(), route: route.map(proj), points: pts.map(proj), bounds: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
      corners: { nw: proj([b.getNorth(), b.getWest()]), se: proj([b.getSouth(), b.getEast()]) } };
    window.__ready = true;
  }, 1500));
});
</script></body></html>"""

async def _render(route, points, w, h, dpr, pad, style, out_png, timeout=240):
    from playwright.async_api import async_playwright
    VEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vendor', 'maplibre')
    html = PAGE.replace('__CSS__', open(os.path.join(VEND, 'maplibre-gl.css'), encoding='utf-8').read()).replace('__JS__', open(os.path.join(VEND, 'maplibre-gl.js'), encoding='utf-8').read()).replace('__W__', str(w)).replace('__H__', str(h)).replace('__ROUTE__', json.dumps(route)).replace('__POINTS__', json.dumps(points)).replace('__PAD__', str(pad)).replace('__STYLE__', json.dumps(style)).replace('__DPR__', str(dpr))
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        ctx = await browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=dpr, user_agent=UA)
        page = await ctx.new_page(); await page.set_content(html, wait_until='load')
        for _ in range(timeout*2):
            if await page.evaluate('window.__ready'): break
            err = await page.evaluate('window.__err')
            if err and 'style' in str(err).lower(): raise RuntimeError('MapLibre: ' + str(err))
            await asyncio.sleep(0.5)
        else: raise TimeoutError('MapLibre não terminou de carregar os tiles')
        out = await page.evaluate('window.__out')
        await page.evaluate("map.triggerRepaint()"); await asyncio.sleep(0.5)
        await page.locator('#map').screenshot(path=out_png, type='png', animations='disabled')
        await browser.close()
    out['w'] = w*dpr; out['h'] = h*dpr; out['dpr'] = dpr
    out['route'] = [[x*dpr, y*dpr] for x, y in out['route']]; out['points'] = [[x*dpr, y*dpr] for x, y in out['points']]
    out['corners'] = {k: [v[0]*dpr, v[1]*dpr] for k, v in out['corners'].items()}
    return out

def render_maps(route, points, out_dir, style=STYLE_URL, base_px=4096, detail_px=6144):
    """route: [[lat,lon],...]; points: [[lat,lon],...] (origem, paragens, destino). Escreve base.png e detail.png."""
    base = asyncio.run(_render(route, points, base_px//2, base_px//2, 2, int(base_px//2*0.22), style, os.path.join(out_dir, 'map.png')))
    detail = asyncio.run(_render(route, points, detail_px//2, detail_px//2, 2, int(detail_px//2*0.08), style, os.path.join(out_dir, 'detail.png')))
    return base, detail

ATTRIBUTION = '© OpenStreetMap contributors · OpenMapTiles · OpenFreeMap'
