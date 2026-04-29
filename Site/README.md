# Site inicial — Pokémon Global Server

Coloque esta pasta `Site` na raiz do seu repositório:

```text
Pokemon-Global-Server-Definitivo/
├─ Site/
│  ├─ index.html
│  ├─ style.css
│  ├─ script.js
│  ├─ index.astro
│  └─ README.md
└─ Recursos/Visual/Icones/GlobalServer/
   ├─ QuadroLogo.png
   ├─ Logo.png
   └─ Icone.png
```

## Como testar agora

Abra o arquivo:

```text
Site/index.html
```

Ele usa as imagens por caminho relativo:

```text
../Recursos/Visual/Icones/GlobalServer/Logo.png
../Recursos/Visual/Icones/GlobalServer/QuadroLogo.png
../Recursos/Visual/Icones/GlobalServer/Icone.png
```

## O que cada arquivo faz

- `index.html`: página normal que você pode abrir direto no navegador.
- `style.css`: aparência da página.
- `script.js`: interações simples, como trocar a logo e testar um botão.
- `index.astro`: a mesma ideia em formato Astro, com variáveis no topo.

## Observação sobre Astro

Para respeitar seu pedido de não criar subpastas, deixei tudo solto dentro de `Site`.

Em um projeto Astro real, o arquivo `index.astro` normalmente ficaria em:

```text
Site/src/pages/index.astro
```

Por enquanto, use o `index.html` para ver a tela funcionando imediatamente.
