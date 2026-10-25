# Rota Cinema Studio

Render **offline** (Blender / Cycles) dos vídeos de rota para o YouTube. Separado do app GPS: nada aqui corre no iPhone.

Pipeline (3 passos, todos reproduzíveis):

| Passo | Ficheiro | O que faz |
|---|---|---|
| 1 | `build_assets.py` | Rota real (OSRM) + tiles reais OpenStreetMap → `out/map.png`, `out/detail.png` (corredor 4×), `out/scene.json` |
| 2 | `render_blender.py` | Cena Cycles: mapa de papel com relevo, rota emissiva revelada progressivamente, carro, sol + luz azul, DOF física, AgX, bloom. 5 cenas de câmara. |
| 3 | `overlay_frames.py` | Chip, título manuscrito, km/custo e **crédito OpenStreetMap** (obrigatório) nos frames |

`trip.json` define a viagem (origem, destino, paragens). O app GPS pode exportar este ficheiro.

## Carro

- Com `models/car.glb` presente, usa esse modelo (o seu). Sem ele, usa um coupé **provisório e genérico**, identificado como tal no log.
- O modelo do BMW 420 M não é fornecido aqui por licença. Compre um `.glb` com licença para vídeo (ver `models/README.md`).

## Render na nuvem (GitHub Actions, grátis, CPU)

Qualquer push que altere `studio/**` com `[render stills]` ou `[render clip]` na mensagem do commit, ou "Run workflow" em Actions → *Rota Cinema Studio*. Resultado em `studio/renders/<data>-<modo>-<res>/`.
Limites: CPU de 4 núcleos; 1280×720 a 64 amostras ≈ 1–2 min por frame. Um clip de 5 s a 24 fps ≈ 2–3 h. Bom para validar; lento para produção.

## Render local na RTX 4070 Ti SUPER (produção, 4K)

1. Instalar **Blender 5.2 LTS** (blender.org). Python 3.11+ com `pip install pillow`. `winget install ffmpeg`.
2. Na pasta do repositório:
   `powershell -ExecutionPolicy Bypass -File studio\render_local.ps1 -Mode clip -W 3840 -H 2160 -Samples 256 -Dur 20 -Fps 30`
3. MP4 em `studio\out\cinema_3840x2160.mp4`. Em OptiX, um frame 4K a 256 amostras com denoise demora ~5–10 s → 20 s de vídeo ≈ 1 h.

Opções: `-Mode stills` (3 imagens de validação em segundos), `-Samples 64` para testes rápidos.

## Mapas: condições

- Tiles de `tile.openstreetmap.org` com User-Agent próprio (política de uso). Sem pré-descarga em massa: só o corredor da rota (~250 tiles por viagem).
- Crédito obrigatório no vídeo e na descrição do YouTube: **© OpenStreetMap contributors — openstreetmap.org/copyright** (dados ODbL). O passo 3 já o grava no canto do frame.
