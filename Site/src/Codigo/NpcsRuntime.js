import { criarCardPokemon, criarControladorDetalhe as criarControladorPokemonDetalhe } from "./PokedexRuntime.js";

function lerJson(id) {
  const node = document.getElementById(id);
  if (!node) return null;
  try {
    return JSON.parse(node.textContent || "{}");
  } catch (erro) {
    console.error(`[Wiki NPCs] Não consegui ler os dados de ${id}.`, erro);
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

function assetNpc(npc, dados) {
  return dados.assetsNpcs?.[npc.id] ?? { imagem: null };
}

export function criarCardNpc(npc, dados, origem = "wiki") {
  const asset = assetNpc(npc, dados);
  const card = document.createElement("button");
  card.type = "button";
  card.className = `item-card npc-card npc-card-${npc.tipo}`;
  card.dataset.npcId = npc.id;
  card.dataset.origem = origem;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(npc.codigo)}</span>
    <span class="item-card-arte npc-card-arte">
      ${asset.imagem ? `<img src="${asset.imagem}" alt="${html(npc.nome)}" loading="lazy" decoding="async" />` : `<span class="item-card-sem-arte">${html(npc.nome.slice(0, 1))}</span>`}
    </span>
    <span class="item-card-nome">${html(npc.nome)}</span>
    <span class="item-card-meta">${html(npc.tipoRotulo)}</span>
  `;
  return card;
}

function encontrarPokemon(nome, pokedex) {
  const chave = normalizar(nome);
  return (pokedex.pokemons || []).find((pokemon) => (
    normalizar(pokemon.nome) === chave ||
    normalizar(pokemon.nomeExibicao) === chave ||
    normalizar(pokemon.slug) === chave ||
    normalizar(pokemon.slugBase) === chave
  ));
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

function tagsNpc(npc) {
  const extras = [npc.tipoRotulo];
  if (npc.tipo === "combatente") {
    if (npc.cargo) extras.push(npc.cargo);
    if (npc.estadio) extras.push(`Estádio ${npc.estadio}`);
  } else if (npc.categoria) {
    extras.push(npc.categoria);
  }
  return extras.map((item) => `<span class="tag-extra">${html(item)}</span>`).join("");
}

export function criarControladorDetalheNpc(dados, pokedex, opcoes = {}) {
  const detalhe = document.querySelector(opcoes.seletorDetalhe || "[data-npc-detail]");
  let npcAberto = null;

  function listaNavegacao() {
    const listaAtual = typeof opcoes.obterListaAtual === "function" ? opcoes.obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.npcs || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }

  function abrirVizinho(direcao) {
    if (!npcAberto) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((npc) => String(npc.id) === String(npcAberto.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.id);
  }

  function abrirDetalhe(id) {
    const npc = (dados.npcs || []).find((atual) => atual.id === String(id));
    if (!npc || !detalhe) return;
    npcAberto = npc;
    const asset = assetNpc(npc, dados);
    const imagem = detalhe.querySelector("[data-npc-image]");
    const codigo = detalhe.querySelector("[data-npc-code]");
    const nome = detalhe.querySelector("[data-npc-name]");
    const tags = detalhe.querySelector("[data-npc-tags]");
    const info = detalhe.querySelector("[data-npc-info]");
    const equipePainel = detalhe.querySelector("[data-npc-team-panel]");
    const equipe = detalhe.querySelector("[data-npc-team]");

    if (codigo) codigo.textContent = `#${npc.codigo}`;
    if (nome) nome.textContent = npc.nome;
    if (tags) tags.innerHTML = tagsNpc(npc);

    if (imagem) {
      if (asset.imagem) {
        imagem.hidden = false;
        imagem.src = asset.imagem;
        imagem.alt = npc.nome;
      } else {
        imagem.hidden = true;
        imagem.removeAttribute("src");
      }
    }

    if (info) {
      const linhas = [
        ["Tipo", npc.tipoRotulo],
        ["Nível", formatarNumero(npc.nivel)],
      ];
      if (npc.tipo === "vendedor") {
        linhas.push(["Categoria", npc.categoria || "-"]);
      } else {
        linhas.push(["Cargo", npc.cargo || "-"]);
        linhas.push(["Estádio", npc.estadio ? `Estádio ${npc.estadio}` : "-"]);
        linhas.push(["Batalhas", formatarNumero(npc.batalhas)]);
      }
      info.innerHTML = linhas.map(([chave, valor]) => `<div><dt>${html(chave)}</dt><dd>${html(valor)}</dd></div>`).join("");
    }

    if (equipePainel) equipePainel.hidden = npc.tipo !== "combatente";
    if (npc.tipo === "combatente") preencherPokemonGrid(equipe, npc.pokemons, pokedex, "npc");
    else if (equipe) equipe.replaceChildren();

    detalhe.hidden = false;
    document.body.classList.add("detalhe-aberto");
  }

  function fecharDetalhe() {
    if (detalhe) detalhe.hidden = true;
    document.body.classList.remove("detalhe-aberto");
  }

  detalhe?.querySelectorAll("[data-npc-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-npc-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-npc-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });

  return { abrirDetalhe, fecharDetalhe };
}

export function inicializarWikiNpcs(idDados = "npcs-data") {
  const dados = lerJson(idDados);
  const pokedex = lerJson("npcs-pokedex-data");
  const app = document.querySelector("[data-npcs-app]");
  if (!dados || !pokedex || !app) return;

  const grid = app.querySelector("[data-npcs-grid]");
  const busca = app.querySelector("[data-npcs-search]");
  const ordenacao = app.querySelector("[data-npcs-sort]");
  const direcaoBotao = app.querySelector("[data-npcs-direction]");
  const filtroTipo = app.querySelector("[data-npcs-kind]");
  const filtroCategoria = app.querySelector("[data-npcs-category]");
  const filtroCargo = app.querySelector("[data-npcs-role]");
  const tipoChips = [...app.querySelectorAll("[data-npcs-type-chip]")];
  const tipoArea = app.querySelector("[data-npcs-type-filters]");
  const vendedorControles = [...app.querySelectorAll("[data-npcs-vendor-only]")];
  const combatenteControles = [...app.querySelectorAll("[data-npcs-combat-only]")];
  const contador = app.querySelector("[data-npcs-count]");
  const botaoLimpar = app.querySelector("[data-npcs-clear]");
  const vazio = app.querySelector("[data-npcs-empty]");
  const sentinela = app.querySelector("[data-npcs-sentinel]");
  const PAGE_SIZE = 36;
  let tipagemSelecionada = "";
  let visiveis = 0;
  let resultadoAtual = [];

  if (direcaoBotao && !direcaoBotao.dataset.sortDirection) direcaoBotao.dataset.sortDirection = "asc";
  const detalheController = criarControladorDetalheNpc(dados, pokedex, { obterListaAtual: () => resultadoAtual });
  const pokemonController = criarControladorPokemonDetalhe(pokedex, {
    seletorDetalhe: "[data-npc-pokemon-detail]",
    mostrarLinhagem: true,
    animarFrames: true,
  });

  function direcaoAtual() {
    return direcaoBotao?.dataset.sortDirection === "desc" ? "desc" : "asc";
  }

  function atualizarDirecao() {
    if (direcaoBotao) direcaoBotao.textContent = direcaoAtual() === "asc" ? "Crescente" : "Descrescente";
  }

  function atualizarControlesCondicionais() {
    const tipo = filtroTipo?.value ?? "";
    vendedorControles.forEach((controle) => { controle.hidden = tipo !== "vendedor"; });
    combatenteControles.forEach((controle) => { controle.hidden = tipo !== "combatente"; });
    if (tipoArea) tipoArea.hidden = tipo !== "combatente";
    if (tipo !== "vendedor" && filtroCategoria) filtroCategoria.value = "";
    if (tipo !== "combatente") {
      if (filtroCargo) filtroCargo.value = "";
      tipagemSelecionada = "";
    }
    tipoChips.forEach((chip) => {
      const ativo = chip.dataset.npcsTypeChip === tipagemSelecionada;
      chip.classList.toggle("ativo", ativo);
      chip.setAttribute("aria-pressed", ativo ? "true" : "false");
    });
  }

  function obterResultado() {
    const termo = normalizar(busca?.value ?? "");
    const tipo = filtroTipo?.value ?? "";
    const categoria = tipo === "vendedor" ? (filtroCategoria?.value ?? "") : "";
    const cargo = tipo === "combatente" ? (filtroCargo?.value ?? "") : "";
    const tipagem = tipo === "combatente" ? tipagemSelecionada : "";
    const sort = ordenacao?.value ?? "ordem";
    const direcao = direcaoAtual();

    const filtrados = (dados.npcs || []).filter((npc) => {
      if (termo && !npc.busca.includes(termo)) return false;
      if (tipo && npc.tipo !== tipo) return false;
      if (categoria && npc.categoriaBusca !== categoria) return false;
      if (cargo && npc.cargoBusca !== cargo) return false;
      if (tipagem && npc.estadioBusca !== tipagem) return false;
      return true;
    });

    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
      nivel: (a, b) => (a.nivel ?? 0) - (b.nivel ?? 0),
      tipo: (a, b) => a.tipoRotulo.localeCompare(b.tipoRotulo, "pt-BR", { numeric: true }),
      cargo: (a, b) => (a.cargo || "").localeCompare(b.cargo || "", "pt-BR", { numeric: true }),
      categoria: (a, b) => (a.categoria || "").localeCompare(b.categoria || "", "pt-BR", { numeric: true }),
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
    atualizarControlesCondicionais();
  }

  function renderLista() {
    if (!grid) return;
    resultadoAtual = obterResultado();
    visiveis = Math.min(PAGE_SIZE, resultadoAtual.length);
    grid.replaceChildren();
    resultadoAtual.slice(0, visiveis).forEach((npc) => {
      const card = criarCardNpc(npc, dados);
      card.classList.add("pokemon-card-entrando");
      grid.appendChild(card);
    });
    atualizarEstado();
  }

  function carregarMais() {
    if (!grid || visiveis >= resultadoAtual.length) return;
    const fim = Math.min(visiveis + PAGE_SIZE, resultadoAtual.length);
    resultadoAtual.slice(visiveis, fim).forEach((npc) => grid.appendChild(criarCardNpc(npc, dados)));
    visiveis = fim;
    atualizarEstado();
  }

  [busca, ordenacao, filtroTipo, filtroCategoria, filtroCargo].forEach((controle) => {
    controle?.addEventListener("input", renderLista);
    controle?.addEventListener("change", renderLista);
  });

  tipoChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const tipo = chip.dataset.npcsTypeChip || "";
      tipagemSelecionada = tipagemSelecionada === tipo ? "" : tipo;
      renderLista();
    });
  });

  direcaoBotao?.addEventListener("click", () => {
    direcaoBotao.dataset.sortDirection = direcaoAtual() === "asc" ? "desc" : "asc";
    renderLista();
  });

  botaoLimpar?.addEventListener("click", () => {
    if (busca) busca.value = "";
    if (ordenacao) ordenacao.value = "ordem";
    if (filtroTipo) filtroTipo.value = "";
    if (filtroCategoria) filtroCategoria.value = "";
    if (filtroCargo) filtroCargo.value = "";
    if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    tipagemSelecionada = "";
    renderLista();
  });

  grid?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-npc-id]");
    if (!card) return;
    detalheController.abrirDetalhe(card.dataset.npcId);
  });

  document.querySelector("[data-npc-detail]")?.addEventListener("click", (evento) => {
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
