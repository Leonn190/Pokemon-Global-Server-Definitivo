import { criarCardPokemon, criarControladorDetalhe as criarControladorPokemonDetalhe } from "./PokedexRuntime.js";
import { fecharModalDetalhe, abrirModalDetalhe, infoHtml, aplicarImagemDetalhe, criarWikiCatalogo, formatarNumero, html, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";
function assetDungeon(dungeon, dados) {
  return dados.assetsDungeons?.[dungeon.id] ?? { imagem: null };
}
export function criarCardDungeon(dungeon, dados) {
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
export function criarControladorDetalheDungeons(dados, pokedex, obterListaAtual) {
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
    const info = detalhe.querySelector("[data-dungeon-info]");
    const pokemons = detalhe.querySelector("[data-dungeon-pokemons]");
    const servos = detalhe.querySelector("[data-dungeon-servos]");
    if (codigo) codigo.textContent = `#${dungeon.id}`;
    if (nome) nome.textContent = dungeon.nome;
    aplicarImagemDetalhe(imagem, asset.imagem, dungeon.nome);
    if (info) {
      const linhas = [
        ["Tamanho", dungeon.tamanhoRotulo],
        ["Dificuldade", dungeon.dificuldadeRotulo],
        ["Entradas", formatarNumero(dungeon.entradas)],
        ["Biomas", dungeon.biomas?.join(" / ") || "-"],
      ];
      info.innerHTML = infoHtml(linhas);
    }
    preencherPokemonGrid(pokemons, dungeon.pokemons, pokedex, "dungeon");
    preencherPokemonGrid(servos, dungeon.servos, pokedex, "dungeon-servo");
    abrirModalDetalhe(detalhe);
  }
  function fecharDetalhe() {
    fecharModalDetalhe(detalhe);
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
  let listagem;
  const detalheController = criarControladorDetalheDungeons(dados, pokedex, () => listagem?.obterResultadoAtual() ?? []);
  const pokemonController = criarControladorPokemonDetalhe(pokedex, {
    seletorDetalhe: "[data-dungeon-pokemon-detail]",
    mostrarLinhagem: true,
  });
  function obterResultado(direcao) {
    const termo = normalizar(busca?.value ?? "");
    const dificuldade = filtroDificuldade?.value ?? "";
    const tamanho = filtroTamanho?.value ?? "";
    const bioma = filtroBioma?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
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
    return ordenarComDirecao(filtrados, ordenadores, sort, direcao);
  }
  listagem = criarWikiCatalogo({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    controles: [busca, ordenacao, filtroDificuldade, filtroTamanho, filtroBioma],
    botaoLimpar,
    cardSelector: "[data-dungeon-id]",
    obterCardId: (card) => card.dataset.dungeonId,
    abrirDetalhe: (id) => detalheController.abrirDetalhe(id),
    criarCard: (dungeon) => criarCardDungeon(dungeon, dados),
    obterResultado,
    limparFiltros: () => {
      if (busca) busca.value = "";
      if (ordenacao) ordenacao.value = "ordem";
      if (filtroDificuldade) filtroDificuldade.value = "";
      if (filtroTamanho) filtroTamanho.value = "";
      if (filtroBioma) filtroBioma.value = "";
      if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    },
  });
  document.querySelector("[data-dungeon-detail]")?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-pokemon-id]");
    if (!card) return;
    pokemonController.abrirDetalhe(card.dataset.pokemonId);
  });
  listagem.iniciar();
}
