# Site — Pokémon Global Server

Estrutura inicial em Astro para o site do Pokémon Global Server.

## Como usar

Coloque a pasta `Site` na raiz do repositório:

```text
Pokemon-Global-Server-Definitivo/
├─ Site/
├─ Recursos/
├─ Codigo/
└─ SimuladorServerJogo/
```

Depois rode:

```bash
cd Site
npm install
npm run dev
```

O site deve abrir no endereço informado pelo terminal, normalmente:

```text
http://localhost:4321
```

## Imagens

As imagens não ficam dentro do site. Elas são importadas da pasta oficial do jogo:

```text
Recursos/Visual/Icones/GlobalServer/
├─ QuadroLogo.png
├─ Logo.png
└─ Icone.png
```

O alias `@recursos` é configurado em `astro.config.mjs`.

Exemplo:

```astro
---
import logo from "@recursos/Visual/Icones/GlobalServer/Logo.png";
---

<img src={logo.src} alt="Pokémon Global Server" />
```

## Organização

```text
src/Codigo      → JavaScript funcional
src/Estilos     → CSS
src/Componentes → blocos reutilizáveis Astro
src/pages       → páginas/rotas do site
```

## Rotas criadas

```text
/              → Início
/conta         → Conta
/download      → Download
/wiki          → Wiki
/wiki/pokemons → Wiki / Pokémons
/wiki/itens    → Wiki / Itens
/wiki/efeitos  → Wiki / Efeitos
/wiki/estadios → Wiki / Estádios
/wiki/mundo    → Wiki / Mundo
```
