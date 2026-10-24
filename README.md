# LR Rota — Leandro na Rota

App web instalável no iPhone (PWA) para planear rotas turísticas, estimar combustível e portagens, registar custos e gerar o vídeo animado e a capa do trajeto para o canal **Leandro na Rota**.

Fase 1 (esta versão): tudo corre no telemóvel, sem servidor. Mapa OpenStreetMap, rotas por estrada (OSRM), pontos turísticos e restaurantes do mapa (Overpass), guia por IA opcional (chave Claude), vídeo e capa gerados no próprio telemóvel.

## Ficheiros

| Ficheiro | Para que serve |
|---|---|
| `index.html` | O app inteiro (ecrãs, CSS e JavaScript) |
| `manifest.webmanifest` | Nome, ícone e cor para instalar na tela inicial |
| `sw.js` | Service worker: abre offline e guarda os mapas já vistos |
| `icons/car.png` | O seu carro no mapa (ícone 256 px) |
| `icons/icon-192.png` | Ícone do app |
| `.github/workflows/pages.yml` | Publica sozinho no GitHub Pages a cada `git push` |

## Publicar (GitHub Pages, grátis)

1. Crie um repositório no GitHub chamado `lr-rota` (público).
2. Envie estes ficheiros para o ramo `main`.
3. Em 1–2 minutos o site fica em `https://SEU-USUARIO.github.io/lr-rota/`.
   O workflow liga o Pages sozinho na primeira vez.

Qualquer `git push` para `main` publica a nova versão.

## Instalar no iPhone

1. Abra o endereço no **Safari** (tem de ser o Safari).
2. Toque em **Partilhar** (quadrado com seta) → **Adicionar ao ecrã principal**.
3. Abra o LR Rota pelo ícone. Na primeira vez, aceite a **localização** — sem ela o app não entra.

## O que configurar na primeira abertura

Em **Veículo** (aba de baixo): nome do carro, gasóleo, consumo (L/100 km), preço do litro, Via Verde.
Opcional: chave Claude (`sk-ant-…`) para gerar o guia do destino com IA.

## Limites desta versão web (honestos)

- O GPS só grava com o ecrã ligado. O app mantém o ecrã aceso durante a viagem.
- Não há Dynamic Island nem gravação em segundo plano — isso é a Fase 2 (app nativo, exige conta Apple Developer).
- Portagens são estimativa: km em autoestrada × preço por km configurado.
- Dados ficam só no telemóvel. Use **Exportar backup** de vez em quando.

## Fase 2 (planeada)

App nativo iOS com GPS em segundo plano, Live Activity, Google Maps SDK e modelo 3D do carro. Depende de conta Apple Developer (99 €/ano).
