import { infoHtml, criarListagemPaginada, formatarNumero, html, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";
const FRAME_MODULES = {
  ...import.meta.glob("@recursos/Visual/Pokemons/Animação/**/*.{png,PNG,jpg,JPG,jpeg,JPEG,webp,WEBP,gif,GIF}", {
    query: "?url",
    import: "default",
  }),
  ...import.meta.glob("@recursos/Visual/Pokemons/Animacao/**/*.{png,PNG,jpg,JPG,jpeg,JPEG,webp,WEBP,gif,GIF}", {
    query: "?url",
    import: "default",
  }),
};
const MAXIMOS_BARRAS = {
  Vida: 200,
  CrD: 75,
  CrC: 75,
};
const ATRIBUTOS_REGULARES = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int"];
let frameIndex = null;
const framesCache = new Map();
function ehRadiante(pokemon) {
  return normalizar(pokemon?.nome).includes("radiante");
}
function nomeExibicao(pokemon) {
  return String(pokemon?.nome || pokemon?.nomeExibicao || "Pokémon").replace(/\s+/g, " ").trim();
}
function nomeBaseRadiante(nome) {
  return String(nome ?? "")
    .replace(/\bradiante\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}
function candidatosPokemon(pokemon) {
  const codigo = String(pokemon?.code ?? pokemon?.id ?? "");
  const nome = String(pokemon?.nome ?? "");
  const nomeBase = nomeBaseRadiante(nome);
  const exibicao = nomeExibicao(pokemon);
  return [
    codigo,
    codigo.padStart(3, "0"),
    `pokemon${codigo}`,
    `poke${codigo}`,
    nome,
    pokemon?.slug,
    pokemon?.slugBase,
    nome.replace(/\s+/g, "_"),
    nome.replace(/\s+/g, "-"),
    nomeBase,
    exibicao,
    nomeBase.replace(/\s+/g, "_"),
    nomeBase.replace(/\s+/g, "-"),
    exibicao.replace(/\s+/g, "_"),
    exibicao.replace(/\s+/g, "-"),
  ]
    .filter(Boolean)
    .map(normalizar);
}
function criarIndiceFrames(modulos) {
  const indice = {};
  Object.entries(modulos).forEach(([caminho, carregador]) => {
    const partes = caminho.split(/[\\/]/).filter(Boolean);
    const pasta = partes.at(-2) ?? "";
    const chave = normalizar(pasta);
    if (!chave) return;
    if (!indice[chave]) indice[chave] = [];
    indice[chave].push({ caminho, carregador });
  });
  Object.values(indice).forEach((frames) => {
    frames.sort((a, b) => a.caminho.localeCompare(b.caminho, "pt-BR", { numeric: true, sensitivity: "base" }));
  });
  return indice;
}
async function carregarFramesPokemon(pokemon) {
  const cacheKey = String(pokemon?.id ?? pokemon?.nome ?? "");
  if (framesCache.has(cacheKey)) return framesCache.get(cacheKey);
  if (!frameIndex) frameIndex = criarIndiceFrames(FRAME_MODULES);
  for (const candidato of candidatosPokemon(pokemon)) {
    const frames = frameIndex[candidato];
    if (!frames?.length) continue;
    const carregados = await Promise.all(frames.map((frame) => frame.carregador()));
    framesCache.set(cacheKey, carregados);
    return carregados;
  }
  framesCache.set(cacheKey, []);
  return [];
}
function assetPokemon(pokemon, assetsPokemons) {
  return assetsPokemons?.[pokemon.id] ?? { imagem: null };
}
function classeChance(chance) {
  const valor = Number(chance);
  if (!Number.isFinite(valor)) return "chance-neutra";
  if (valor > 50) return "chance-ouro";
  if (valor === 50) return "chance-prata";
  return "chance-bronze";
}
function tipoBolinhaHtml(tipo, iconesTipos, pequeno = true) {
  const chave = normalizar(tipo.nome);
  const icone = iconesTipos?.[chave];
  return `<span class="tipo-bola ${pequeno ? "pequena" : ""} ${classeChance(tipo.chance)}" title="${html(tipo.nome)}${tipo.chance ? ` ${formatarNumero(tipo.chance, "%")}` : ""}">
    ${icone ? `<img src="${icone}" alt="${html(tipo.nome)}" loading="eager" decoding="async" />` : `<b>${html(String(tipo.nome || "?").slice(0, 1))}</b>`}
  </span>`;
}
function tipoBadgeHtml(tipo, iconesTipos) {
  const chave = normalizar(tipo.nome);
  const icone = iconesTipos?.[chave];
  return `<span class="tipo-badge ${classeChance(tipo.chance)}">
    <span class="tipo-icone">${icone ? `<img src="${icone}" alt="" loading="eager" decoding="async" />` : ""}</span>
    <strong>${html(tipo.nome)}</strong>
    ${tipo.chance ? `<em>${formatarNumero(tipo.chance, "%")}</em>` : ""}
  </span>`;
}
function tiposBolinhaHtml(pokemon, iconesTipos) {
  return pokemon.tipos.map((tipo) => tipoBolinhaHtml(tipo, iconesTipos)).join("");
}
function tiposBadgeHtml(pokemon, iconesTipos) {
  return pokemon.tipos.map((tipo) => tipoBadgeHtml(tipo, iconesTipos)).join("");
}
function larguraAtributo(chave, valor) {
  const maximo = MAXIMOS_BARRAS[chave] ?? 100;
  const numero = Number(valor) || 0;
  return Math.max(0, Math.min(100, (numero / maximo) * 100));
}
function focoPrincipal(pokemon) {
  let melhor = null;
  let melhorValor = -Infinity;
  ATRIBUTOS_REGULARES.forEach((atributo) => {
    const bruto = Number(pokemon?.atributos?.[atributo]) || 0;
    const valor = atributo === "Vida" ? bruto / 2 : bruto;
    if (valor > melhorValor) {
      melhorValor = valor;
      melhor = atributo;
    }
  });
  return melhor;
}
export function criarCardPokemon(pokemon, dados, origem = "wiki") {
  const asset = assetPokemon(pokemon, dados.assetsPokemons);
  const nomeVisivel = nomeExibicao(pokemon);
  const card = document.createElement("button");
  card.type = "button";
  card.className = `pokemon-card ${ehRadiante(pokemon) ? "pokemon-radiante" : ""}`;
  card.dataset.pokemonId = pokemon.id;
  card.dataset.origem = origem;
  card.innerHTML = `
    <span class="pokemon-card-codigo">#${html(pokemon.id)}</span>
    <span class="pokemon-card-arte">
      ${asset.imagem ? `<img class="${ehRadiante(pokemon) ? "sprite-radiante" : ""}" src="${asset.imagem}" alt="${html(nomeVisivel)}" loading="lazy" decoding="async" />` : `<span class="pokemon-card-sem-arte">${html(nomeVisivel.slice(0, 1))}</span>`}
    </span>
    <span class="pokemon-card-nome">${html(nomeVisivel)}</span>
    <span class="pokemon-card-meta">${html(pokemon.grupo)}</span>
    <span class="pokemon-card-tipos">${tiposBolinhaHtml(pokemon, dados.iconesTipos)}</span>
    <span class="pokemon-card-poder"><strong>${formatarNumero(pokemon.total)}</strong><small>Poder total</small></span>
  `;
  return card;
}
export function criarControladorDetalhe(dados, opcoes = {}) {
  const detalhe = document.querySelector(opcoes.seletorDetalhe || "[data-pokemon-detail]");
  let frameTimer = null;
  let pokemonAberto = null;
  const atributosBase = dados.atributosBase || [];
  function limparAnimacao() {
    if (frameTimer) window.clearInterval(frameTimer);
    frameTimer = null;
  }
  function familiaPokemon(pokemon) {
    return (dados.pokemons || [])
      .filter((item) => String(item.linhagem) === String(pokemon.linhagem))
      .sort((a, b) => {
        const ea = Number(a.estagio) || 99;
        const eb = Number(b.estagio) || 99;
        if (ea !== eb) return ea - eb;
        return a.ordem - b.ordem;
      });
  }
  function listaNavegacao() {
    const listaAtual = typeof opcoes.obterListaAtual === "function" ? opcoes.obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.pokemons || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }
  function abrirVizinho(direcao) {
    if (!pokemonAberto) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((item) => String(item.id) === String(pokemonAberto.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.id);
  }
  async function abrirDetalhe(id) {
    const pokemon = (dados.pokemons || []).find((item) => item.id === String(id));
    if (!pokemon || !detalhe) return;
    pokemonAberto = pokemon;
    limparAnimacao();
    const asset = assetPokemon(pokemon, dados.assetsPokemons);
    const nomeVisivel = nomeExibicao(pokemon);
    const imagem = detalhe.querySelector("[data-detail-image]");
    const fallback = detalhe.querySelector("[data-detail-fallback]");
    const codigo = detalhe.querySelector("[data-detail-code]");
    const nome = detalhe.querySelector("[data-detail-name]");
    const tags = detalhe.querySelector("[data-detail-tags]");
    const resumo = detalhe.querySelector("[data-detail-summary]");
    const stats = detalhe.querySelector("[data-detail-stats]");
    const info = detalhe.querySelector("[data-detail-info]");
    const linha = detalhe.querySelector("[data-detail-line]");
    const linhaCount = detalhe.querySelector("[data-detail-line-count]");
    const painelLinhagem = detalhe.querySelector("[data-detail-line-panel]");
    if (codigo) {
      codigo.textContent = `#${pokemon.id}`;
      codigo.classList.toggle("radiante", false);
    }
    if (nome) nome.textContent = nomeVisivel;
    if (tags) tags.innerHTML = tiposBadgeHtml(pokemon, dados.iconesTipos);
    if (resumo) {
      resumo.textContent = "";
      resumo.hidden = true;
    }
    if (imagem && fallback) {
      imagem.classList.toggle("sprite-radiante", ehRadiante(pokemon));
      const imagemBase = asset.imagem;
      if (imagemBase) {
        imagem.hidden = false;
        fallback.hidden = true;
        imagem.src = imagemBase;
        imagem.alt = nomeVisivel;
      } else {
        imagem.hidden = true;
        fallback.hidden = true;
        fallback.textContent = "";
      }
      const frames = opcoes.animarFrames === false ? [] : await carregarFramesPokemon(pokemon);
      if (pokemonAberto?.id !== pokemon.id) return;
      if (frames.length) {
        imagem.hidden = false;
        fallback.hidden = true;
        imagem.src = frames[0];
        imagem.alt = nomeVisivel;
      }
      if (frames.length > 1) {
        let frame = 0;
        frameTimer = window.setInterval(() => {
          if (pokemonAberto?.id !== pokemon.id) return;
          frame = (frame + 1) % frames.length;
          imagem.src = frames[frame];
        }, 40);
      }
    }
    if (stats) {
      stats.innerHTML = atributosBase.map((atributo) => {
        const valor = pokemon.atributos?.[atributo.chave] ?? 0;
        const largura = larguraAtributo(atributo.chave, valor);
        const icone = dados.iconesAtributos?.[normalizar(atributo.chave)] || dados.iconesAtributos?.[normalizar(atributo.rotulo)];
        return `<div class="atributo-linha">
          <span class="atributo-nome">${icone ? `<img src="${icone}" alt="" loading="lazy" decoding="async" />` : ""}${html(atributo.rotulo)}</span>
          <span class="atributo-barra"><i style="width:${largura}%"></i></span>
          <strong>${formatarNumero(valor)}</strong>
        </div>`;
      }).join("");
    }
    if (info) {
      const dadosInfo = [
        ["Altura média", formatarNumero(pokemon.altura, " m")],
        ["Peso médio", formatarNumero(pokemon.peso, " kg")],
        ["Tamanho", formatarNumero(pokemon.tamanho)],
        ["Grupo", pokemon.grupo],
        ["Estágio", pokemon.estagio],
        ["Raridade", pokemon.raridadeTexto || "-"],
        ["Foco", pokemon.focoAtributo || focoPrincipal(pokemon) || "-"],
        ["Poder total", formatarNumero(pokemon.total)],
        ["Habilidades", formatarNumero(pokemon.habilidades)],
        ["Equipáveis", formatarNumero(pokemon.equipaveis)],
      ];
      info.innerHTML = infoHtml(dadosInfo);
    }
    if (painelLinhagem) painelLinhagem.hidden = opcoes.mostrarLinhagem === false;
    if (linha && opcoes.mostrarLinhagem !== false) {
      const familia = familiaPokemon(pokemon);
      if (linhaCount) linhaCount.textContent = `${familia.length} forma${familia.length === 1 ? "" : "s"}`;
      linha.innerHTML = familia.map((item) => {
        const assetLinha = assetPokemon(item, dados.assetsPokemons);
        const nomeLinha = nomeExibicao(item);
        return `<button type="button" class="linhagem-card ${item.id === pokemon.id ? "ativo" : ""} ${ehRadiante(item) ? "pokemon-radiante" : ""}" data-line-pokemon="${html(item.id)}">
          <span>${assetLinha.imagem ? `<img class="${ehRadiante(item) ? "sprite-radiante" : ""}" src="${assetLinha.imagem}" alt="" loading="lazy" decoding="async" />` : html(nomeLinha.slice(0, 1))}</span>
          <strong>${html(nomeLinha)}</strong>
          <small>Estágio ${html(item.estagio)}${item.formaFinal ? ` • ${html(item.formaFinal)}` : ""}</small>
        </button>`;
      }).join("");
      linha.querySelectorAll("[data-line-pokemon]").forEach((botao) => {
        botao.addEventListener("click", () => abrirDetalhe(botao.dataset.linePokemon));
      });
    }
    detalhe.hidden = false;
    document.body.classList.add("detalhe-aberto");
    document.dispatchEvent(new CustomEvent("pokemon-detail-opened", { detail: { id: pokemon.id } }));
  }
  function fecharDetalhe() {
    limparAnimacao();
    if (detalhe) detalhe.hidden = true;
    document.body.classList.remove("detalhe-aberto");
    document.dispatchEvent(new CustomEvent("pokemon-detail-closed"));
  }
  detalhe?.querySelectorAll("[data-pokemon-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-pokemon-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-pokemon-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });
  return { abrirDetalhe, fecharDetalhe };
}
export function inicializarPokedex(idDados = "pokedex-data") {
  const dados = lerJson(idDados);
  const app = document.querySelector("[data-pokedex-app]");
  if (!dados || !app) return;
  const grid = app.querySelector("[data-pokedex-grid]");
  const busca = app.querySelector("[data-pokedex-search]");
  const ordenacao = app.querySelector("[data-pokedex-sort]");
  const botaoDirecao = app.querySelector("[data-pokedex-direction]");
  const filtroFoco = app.querySelector("[data-pokedex-focus]");
  const filtroGrupo = app.querySelector("[data-pokedex-group]");
  const filtroRaridade = app.querySelector("[data-pokedex-rarity]");
  const contador = app.querySelector("[data-pokedex-count]");
  const botaoLimpar = app.querySelector("[data-pokedex-clear]");
  const vazio = app.querySelector("[data-pokedex-empty]");
  const sentinela = app.querySelector("[data-pokedex-sentinel]");
  const chipsTipo = app.querySelectorAll("[data-type-chip]");
  const tiposSelecionados = [];
  let listagem;
  const detalheController = criarControladorDetalhe(dados, {
    mostrarLinhagem: true,
    animarFrames: true,
    obterListaAtual: () => listagem?.obterResultadoAtual() ?? [],
  });
  function atualizarChips() {
    chipsTipo.forEach((chip) => {
      const indice = tiposSelecionados.indexOf(chip.dataset.typeChip);
      chip.classList.toggle("ativo", indice !== -1);
      chip.dataset.ordem = indice === -1 ? "" : String(indice + 1);
    });
    if (botaoDirecao) botaoDirecao.setAttribute("aria-label", `Ordenação ${botaoDirecao.textContent.toLowerCase()}`);
  }
  function obterResultado(direcaoBotao) {
    const termo = normalizar(busca?.value ?? "");
    const foco = filtroFoco?.value ?? "";
    const grupo = filtroGrupo?.value ?? "";
    const raridade = filtroRaridade?.value ?? "";
    const sortBruto = ordenacao?.value ?? "ordem";
    const sort = sortBruto.replace(/-(asc|desc)$/g, "");
    const direcao = botaoDirecao ? direcaoBotao : (sortBruto.endsWith("-desc") ? "desc" : "asc");
    const filtrados = (dados.pokemons || []).filter((pokemon) => {
      if (termo && !pokemon.busca.includes(termo)) return false;
      if (tiposSelecionados.length && !tiposSelecionados.every((tipo) => pokemon.tipos.some((item) => normalizar(item.nome) === tipo))) return false;
      if (foco && normalizar(pokemon.focoAtributo || focoPrincipal(pokemon)) !== foco) return false;
      if (grupo && normalizar(pokemon.grupo) !== grupo) return false;
      if (raridade && normalizar(pokemon.raridadeTexto) !== raridade) return false;
      return true;
    });
    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => nomeExibicao(a).localeCompare(nomeExibicao(b), "pt-BR", { numeric: true }),
      vida: (a, b) => (a.vida ?? 0) - (b.vida ?? 0),
      atk: (a, b) => (a.atk ?? 0) - (b.atk ?? 0),
      def: (a, b) => (a.def ?? 0) - (b.def ?? 0),
      spa: (a, b) => (a.spa ?? 0) - (b.spa ?? 0),
      spd: (a, b) => (a.spd ?? 0) - (b.spd ?? 0),
      vel: (a, b) => (a.vel ?? 0) - (b.vel ?? 0),
      mag: (a, b) => (a.mag ?? 0) - (b.mag ?? 0),
      per: (a, b) => (a.per ?? 0) - (b.per ?? 0),
      ene: (a, b) => (a.ene ?? 0) - (b.ene ?? 0),
      int: (a, b) => (a.int ?? 0) - (b.int ?? 0),
      crd: (a, b) => (a.crd ?? 0) - (b.crd ?? 0),
      crc: (a, b) => (a.crc ?? 0) - (b.crc ?? 0),
      total: (a, b) => (a.total ?? 0) - (b.total ?? 0),
      altura: (a, b) => (a.altura ?? 0) - (b.altura ?? 0),
      peso: (a, b) => (a.peso ?? 0) - (b.peso ?? 0),
    };
    return ordenarComDirecao(filtrados, ordenadores, sort, direcao);
  }
  listagem = criarListagemPaginada({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao: botaoDirecao,
    controles: [busca, ordenacao, filtroFoco, filtroGrupo, filtroRaridade],
    botaoLimpar,
    pageSize: 24,
    renderDelay: 8,
    usarFallbackScroll: true,
    cardSelector: "[data-pokemon-id]",
    obterCardId: (card) => card.dataset.pokemonId,
    abrirDetalhe: (id) => {
      detalheController.abrirDetalhe(id);
      const url = new URL(window.location.href);
      url.searchParams.set("pokemon", id);
      window.history.replaceState({}, "", url);
    },
    criarCard: (pokemon) => criarCardPokemon(pokemon, dados),
    obterResultado,
    aoAtualizarEstado: atualizarChips,
    limparFiltros: () => {
      if (busca) busca.value = "";
      if (ordenacao) ordenacao.value = "ordem";
      if (botaoDirecao) botaoDirecao.dataset.sortDirection = "asc";
      if (filtroFoco) filtroFoco.value = "";
      if (filtroGrupo) filtroGrupo.value = "";
      if (filtroRaridade) filtroRaridade.value = "";
      tiposSelecionados.splice(0, tiposSelecionados.length);
    },
  });
  chipsTipo.forEach((chip) => {
    chip.addEventListener("click", () => {
      const tipo = chip.dataset.typeChip;
      const indice = tiposSelecionados.indexOf(tipo);
      if (indice !== -1) tiposSelecionados.splice(indice, 1);
      else {
        if (tiposSelecionados.length >= 3) tiposSelecionados.shift();
        tiposSelecionados.push(tipo);
      }
      listagem.renderLista(true);
    });
  });
  listagem.iniciar();
  const pokemonInicial = new URLSearchParams(window.location.search).get("pokemon");
  if (pokemonInicial) detalheController.abrirDetalhe(pokemonInicial);
}
export function inicializarCarrosselHome(idDados = "pokemon-home-data") {
  const dados = lerJson(idDados);
  const carrossel = document.querySelector("[data-home-pokemon-carousel]");
  if (!dados || !carrossel) return;
  const detalheController = criarControladorDetalhe(dados, {
    seletorDetalhe: "[data-home-pokemon-detail]",
    mostrarLinhagem: false,
    animarFrames: false,
  });
  carrossel.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-home-pokemon-id]");
    if (!card) return;
    detalheController.abrirDetalhe(card.dataset.homePokemonId);
    carrossel.classList.add("pausado");
  });
  document.addEventListener("pokemon-detail-closed", () => {
    carrossel.classList.remove("pausado");
  });
}
