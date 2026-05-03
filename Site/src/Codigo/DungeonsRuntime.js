import { criarCardPokemon, criarControladorDetalhe as criarControladorPokemonDetalhe } from "./PokedexRuntime.js";

function lerJson(id) {
  const node = document.getElementById(id);
  if (!node) return null;
  try {
    return JSON.parse(node.textContent || "{}");
  } catch (erro) {
    console.error(`[Wiki Dungeons] Não consegui ler os dados de ${id}.`, erro);
    return null;
  }
}

function html(valor) {
  return String(valor ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#039;",
    '"': "&quot;",
  })[char]);
}

function normalizar(valor) {
  return String(valor ?? "")
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function formatarNumero(valor) {
  if (valor === null || valor === undefined || valor === "" || Number.isNaN(Number(valor))) return "-";
  const numero = Number(valor);
  return Number.isInteger(numero) ? String(numero) : numero.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

function assetDungeon(dungeon, dados) {
  return dados.assetsDungeons?.[dungeon.id] ?? { imagem: null };
}

function chips(lista) {
  if (!lista?.length) return `<span class="tag-extra">-</span>`;
  return lista.map((item) => `<span class="tag-extra">${html(item)}</span>`).join("");
}

function criarCardDungeon(dungeon, dados) {
  const asset = assetDungeon(dungeon, dados);
  const card = document.createElement("button");
  card.type = "button";
  card.className = "item-card dungeon-card";
  card.dataset.dungeonId = dungeon.id;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(dungeon.id)}</span>
    <span class="item-card-arte dungeon-card-arte">
      ${asset.imagem ? `<img src="${asset.imagem}" alt="${html(dungeon.nome)}" loading="lazy" decoding="async" />` : `<span class="item-card-sem-arte">${html(dungeon.nome.slice(0, 1))}</span>`}
    </span>
    <span class="item-card-nome">${html(dungeon.nome)}</span>
    <span class="item-card-linha"><strong>${html(dungeon.dificuldadeRotulo)}</strong><small>Dificuldade</small></span>
  `;
  return card;
}

function encontrarPokemon(nome, pokedex) {
  const chave = normalizar(nome);
  return (pokedex.pokemons || []).find((pokemon) => {
    return normalizar(pokemon.nome) === chave || normalizar(pokemon.nomeExibicao) === chave || normalizar(pokemon.slug) === chave || normalizar(pokemon.slugBase) === chave;
  });
}

function preencherPokemonGrid(node, nomes, pokedex, origem) {
  if (!node) return;
  node.replaceChildren();
  if (!nomes?.length) {
    node.innerHTML = `<p class="wiki-vazio-texto">Nenhum Pokémon cadastrado.</p>`;
    return;
  }

  nomes.forEach((nome) => {
    const pokemon = encontrarPokemon(nome, pokedex);
    if (pokemon) {
      node.appendChild(criarCardPokemon(pokemon, pokedex, origem));
      return;
    }
    const vazio = document.createElement("article");
    vazio.className = "pokemon-card dungeon-pokemon-nao-encontrado";
    vazio.innerHTML = `
      <span class="pokemon-card-codigo">?</span>
      <span class="pokemon-card-arte"><span class="pokemon-card-sem-arte">${html(nome.slice(0, 1))}</span></span>
      <span class="pokemon-card-nome">${html(nome)}</span>
      <span class="pokemon-card-meta">Não encontrado na Pokédex</span>
    `;
    node.appendChild(vazio);
  });
}

function criarControladorDetalhe(dados, pokedex, obterListaAtual) {
  const detalhe = document.querySelector("[data-dungeon-detail]");
  let dungeonAberta = null;

  function listaNavegacao() {
    const listaAtual = typeof obterListaAtual === "function" ? obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.dungeons || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }

  function abrirVizinho(direcao) {
    if (!dungeonAberta) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((item) => String(item.id) === String(dungeonAberta.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proxima = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proxima) abrirDetalhe(proxima.id);
  }

  function abrirDetalhe(id) {
    const dungeon = (dados.dungeons || []).find((atual) => atual.id === String(id));
    if (!dungeon || !detalhe) return;
    dungeonAberta = dungeon;
    const asset = assetDungeon(dungeon, dados);
    const imagem = detalhe.querySelector("[data-dungeon-image]");
    const codigo = detalhe.querySelector("[data-dungeon-code]");
    const nome = detalhe.querySelector("[data-dungeon-name]");
    const tags = detalhe.querySelector("[data-dungeon-tags]");
    const info = detalhe.querySelector("[data-dungeon-info]");
    const pokemons = detalhe.querySelector("[data-dungeon-pokemons]");
    const servos = detalhe.querySelector("[data-dungeon-servos]");

    if (codigo) codigo.textContent = `#${dungeon.id}`;
    if (nome) nome.textContent = dungeon.nome;

    if (imagem) {
      if (asset.imagem) {
        imagem.hidden = false;
        imagem.src = asset.imagem;
        imagem.alt = dungeon.nome;
      } else {
        imagem.hidden = true;
        imagem.removeAttribute("src");
      }
    }

    if (tags) {
      tags.innerHTML = `
        <span class="tag-extra">${html(dungeon.dificuldadeRotulo)}</span>
        <span class="tag-extra">${html(dungeon.tamanhoRotulo)}</span>
        ${chips(dungeon.biomas)}
      `;
    }

    if (info) {
      const linhas = [
        ["Tamanho", dungeon.tamanhoRotulo],
        ["Dificuldade", dungeon.dificuldadeRotulo],
        ["Entradas", formatarNumero(dungeon.entradas)],
        ["Biomas", dungeon.biomas?.join(" / ") || "-"],
      ];
      info.innerHTML = linhas.map(([chave, valor]) => `<div><dt>${html(chave)}</dt><dd>${html(valor)}</dd></div>`).join("");
    }

    preencherPokemonGrid(pokemons, dungeon.pokemons, pokedex, "dungeon");
    preencherPokemonGrid(servos, dungeon.servos, pokedex, "dungeon-servo");

    detalhe.hidden = false;
    document.body.classList.add("detalhe-aberto");
  }

  function fecharDetalhe() {
    if (detalhe) detalhe.hidden = true;
    document.body.classList.remove("detalhe-aberto");
  }

  detalhe?.querySelectorAll("[data-dungeon-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-dungeon-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-dungeon-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });

  return { abrirDetalhe };
}

export function inicializarWikiDungeons(idDados = "dungeons-data") {
  const dados = lerJson(idDados);
  const pokedex = lerJson("dungeons-pokedex-data");
  const app = document.querySelector("[data-dungeons-app]");
  if (!dados || !pokedex || !app) return;

  const grid = app.querySelector("[data-dungeons-grid]");
  const busca = app.querySelector("[data-dungeons-search]");
  const ordenacao = app.querySelector("[data-dungeons-sort]");
  const direcaoBotao = app.querySelector("[data-dungeons-direction]");
  const filtroDificuldade = app.querySelector("[data-dungeons-difficulty]");
  const filtroTamanho = app.querySelector("[data-dungeons-size]");
  const filtroBioma = app.querySelector("[data-dungeons-biome]");
  const contador = app.querySelector("[data-dungeons-count]");
  const botaoLimpar = app.querySelector("[data-dungeons-clear]");
  const vazio = app.querySelector("[data-dungeons-empty]");
  const sentinela = app.querySelector("[data-dungeons-sentinel]");
  const PAGE_SIZE = 36;
  let visiveis = 0;
  let resultadoAtual = [];

  if (direcaoBotao && !direcaoBotao.dataset.sortDirection) direcaoBotao.dataset.sortDirection = "asc";
  const detalheController = criarControladorDetalhe(dados, pokedex, () => resultadoAtual);
  const pokemonController = criarControladorPokemonDetalhe(pokedex, {
    seletorDetalhe: "[data-dungeon-pokemon-detail]",
    mostrarLinhagem: true,
    animarFrames: true,
  });

  function direcaoAtual() {
    return direcaoBotao?.dataset.sortDirection === "desc" ? "desc" : "asc";
  }

  function atualizarDirecao() {
    if (!direcaoBotao) return;
    direcaoBotao.textContent = direcaoAtual() === "asc" ? "Crescente" : "Descrescente";
  }

  function obterResultado() {
    const termo = normalizar(busca?.value ?? "");
    const dificuldade = filtroDificuldade?.value ?? "";
    const tamanho = filtroTamanho?.value ?? "";
    const bioma = filtroBioma?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
    const direcao = direcaoAtual();

    const filtrados = (dados.dungeons || []).filter((dungeon) => {
      if (termo && !dungeon.busca.includes(termo)) return false;
      if (dificuldade && String(dungeon.dificuldade ?? "") !== dificuldade) return false;
      if (tamanho && String(dungeon.tamanho ?? "") !== tamanho) return false;
      if (bioma && !dungeon.biomasBusca.includes(bioma)) return false;
      return true;
    });

    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
      dificuldade: (a, b) => (a.dificuldade ?? 0) - (b.dificuldade ?? 0),
      tamanho: (a, b) => (a.tamanho ?? 0) - (b.tamanho ?? 0),
      bioma: (a, b) => (a.biomas?.[0] || "").localeCompare(b.biomas?.[0] || "", "pt-BR", { numeric: true }),
    };

    const ordenador = ordenadores[sort] ?? ordenadores.ordem;
    return [...filtrados].sort((a, b) => {
      const principal = ordenador(a, b);
      const final = principal === 0 ? a.ordem - b.ordem : principal;
      return direcao === "desc" ? -final : final;
    });
  }

  function atualizarEstado() {
    if (contador) contador.textContent = String(resultadoAtual.length);
    if (vazio) vazio.hidden = resultadoAtual.length !== 0;
    if (sentinela) sentinela.hidden = resultadoAtual.length === 0 || visiveis >= resultadoAtual.length;
    atualizarDirecao();
  }

  function renderLista() {
    if (!grid) return;
    resultadoAtual = obterResultado();
    visiveis = Math.min(PAGE_SIZE, resultadoAtual.length);
    grid.replaceChildren();
    resultadoAtual.slice(0, visiveis).forEach((dungeon) => {
      const card = criarCardDungeon(dungeon, dados);
      card.classList.add("pokemon-card-entrando");
      grid.appendChild(card);
    });
    atualizarEstado();
  }

  function carregarMais() {
    if (!grid || visiveis >= resultadoAtual.length) return;
    const fim = Math.min(visiveis + PAGE_SIZE, resultadoAtual.length);
    resultadoAtual.slice(visiveis, fim).forEach((dungeon) => grid.appendChild(criarCardDungeon(dungeon, dados)));
    visiveis = fim;
    atualizarEstado();
  }

  [busca, ordenacao, filtroDificuldade, filtroTamanho, filtroBioma].forEach((controle) => {
    controle?.addEventListener("input", renderLista);
    controle?.addEventListener("change", renderLista);
  });

  direcaoBotao?.addEventListener("click", () => {
    direcaoBotao.dataset.sortDirection = direcaoAtual() === "asc" ? "desc" : "asc";
    renderLista();
  });

  botaoLimpar?.addEventListener("click", () => {
    if (busca) busca.value = "";
    if (ordenacao) ordenacao.value = "ordem";
    if (filtroDificuldade) filtroDificuldade.value = "";
    if (filtroTamanho) filtroTamanho.value = "";
    if (filtroBioma) filtroBioma.value = "";
    if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    renderLista();
  });

  grid?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-dungeon-id]");
    if (!card) return;
    detalheController.abrirDetalhe(card.dataset.dungeonId);
  });

  document.querySelector("[data-dungeon-detail]")?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-pokemon-id]");
    if (!card) return;
    pokemonController.abrirDetalhe(card.dataset.pokemonId);
  });

  if (sentinela && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entradas) => {
      if (entradas.some((entrada) => entrada.isIntersecting)) carregarMais();
    }, { rootMargin: "360px 0px" });
    observer.observe(sentinela);
  }

  renderLista();
}
