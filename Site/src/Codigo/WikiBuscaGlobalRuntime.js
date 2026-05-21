import { criarCardAtaque } from "./AtaquesRuntime.js";
import { criarCardComando, criarControladorDetalheComandos } from "./ComandosRuntime.js";
import { criarCardDungeon, criarControladorDetalheDungeons } from "./DungeonsRuntime.js";
import { criarCardEfeito, criarControladorDetalheEfeitos } from "./EfeitosRuntime.js";
import { criarCardEquipavel, criarControladorDetalheEquipaveis } from "./EquipaveisRuntime.js";
import { criarCardEstadio, criarControladorEstadio } from "./EstadiosRuntime.js";
import { criarCardHabilidade, criarControladorDetalheHabilidades } from "./HabilidadesRuntime.js";
import { criarCardItem, criarControladorDetalheItens } from "./ItensRuntime.js";
import { criarCardEstrutura, criarControladorDetalheMundo } from "./MundoRuntime.js";
import { criarFaixa } from "./MusicasRuntime.js";
import { criarCardNpc, criarControladorDetalheNpc } from "./NpcsRuntime.js";
import { criarCardPokemon, criarControladorDetalhe as criarControladorDetalhePokemon } from "./PokedexRuntime.js";
import { lerJson, normalizar } from "./WikiRuntimeBase.js";

const LIMITE_RESULTADOS = 80;
const CHAVE_VOLUME_GLOBAL = "pokemon-global-server-volume-musicas";
let faixaGlobalTocando = null;
let volumeGlobal = 1;

const FILTROS_WIKI = [
  "pokemons",
  "itens",
  "ataques",
  "npcs",
  "estruturas",
  "musicas",
  "habilidades",
  "comandos",
  "dungeons",
  "estadios",
];

function tokensBusca(valor) {
  return String(valor ?? "")
    .split(/\s+/)
    .map(normalizar)
    .filter(Boolean);
}

function pontuar(item, consulta, tokens) {
  let score = 0;
  if (item.tituloBusca === consulta) score += 120;
  if (item.tituloBusca?.startsWith(consulta)) score += 72;
  if (item.tituloBusca?.includes(consulta)) score += 44;
  if (normalizar(item.secao) === consulta) score += 28;
  if (normalizar(item.tipo).includes(consulta)) score += 18;
  tokens.forEach((token) => {
    if (item.tituloBusca?.includes(token)) score += 12;
    if (normalizar(item.meta).includes(token)) score += 5;
    if (normalizar(item.tipo).includes(token)) score += 4;
  });
  return score;
}

function buscar(itens, valor) {
  const consulta = normalizar(valor);
  const tokens = tokensBusca(valor);
  if (!consulta || !tokens.length) return [];
  return (itens || [])
    .filter((item) => tokens.every((token) => item.busca?.includes(token)))
    .map((item) => ({ item, score: pontuar(item, consulta, tokens) }))
    .sort((a, b) => b.score - a.score || a.item.ordem - b.item.ordem)
    .map(({ item }) => item);
}

function limitarVolume(valor) {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 1;
  return Math.min(1, Math.max(0, numero));
}

function lerVolumeSalvo() {
  try {
    return limitarVolume(window.localStorage?.getItem(CHAVE_VOLUME_GLOBAL) ?? 1);
  } catch {
    return 1;
  }
}

function salvarVolume(valor) {
  try {
    window.localStorage?.setItem(CHAVE_VOLUME_GLOBAL, String(valor));
  } catch {
    // localStorage pode estar indisponível em alguns contextos.
  }
}

function aplicarVolumeGlobal(raiz = document) {
  raiz.querySelectorAll?.(".faixa-musica audio").forEach((audio) => {
    audio.volume = volumeGlobal;
  });
}

function encontrarPorId(lista, id, seletor = (item) => item.id) {
  return (lista || []).find((item) => String(seletor(item)) === String(id));
}

function encontrarAtaque(lista, id) {
  return (lista || []).find((ataque) => String(ataque.uid || ataque.id) === String(id));
}

function marcarCardBusca(card, item) {
  if (!card) return null;
  card.classList.add("wiki-busca-card-existente");
  card.dataset.resultadoId = item.id;
  return card;
}

function criarFaixaMusicaBusca(musica, item) {
  const card = criarFaixa(musica);
  marcarCardBusca(card, item);
  card.classList.add("wiki-busca-resultado-musica");
  const audio = card.querySelector("audio");
  const botao = card.querySelector("[data-musica-toggle]");
  if (audio) audio.volume = volumeGlobal;
  botao?.addEventListener("click", (evento) => {
    evento.stopPropagation();
    if (!audio) return;
    if (faixaGlobalTocando && faixaGlobalTocando !== audio) faixaGlobalTocando.pause();
    if (audio.paused) {
      faixaGlobalTocando = audio;
      audio.play().catch(() => {
        if (faixaGlobalTocando === audio) faixaGlobalTocando = null;
      });
    } else {
      audio.pause();
    }
  });
  audio?.addEventListener("pause", () => {
    if (faixaGlobalTocando === audio) faixaGlobalTocando = null;
  });
  return card;
}

function criarResultadoCard(item, detalhes) {
  const id = item.ref;
  if (item.href === "/wiki/pokemons") {
    const pokemon = encontrarPorId(detalhes.pokedex?.pokemons, id);
    return marcarCardBusca(pokemon && criarCardPokemon(pokemon, detalhes.pokedex, "busca-global"), item);
  }
  if (item.href === "/wiki/ataques") {
    const ataque = encontrarAtaque(detalhes.ataques?.ataques, id);
    return marcarCardBusca(ataque && criarCardAtaque(ataque, detalhes.ataques), item);
  }
  if (item.href === "/wiki/efeitos") {
    const efeito = encontrarPorId(detalhes.efeitos?.efeitos, id);
    return marcarCardBusca(efeito && criarCardEfeito(efeito, detalhes.efeitos), item);
  }
  if (item.href === "/wiki/itens") {
    const itemDados = encontrarPorId(detalhes.itens?.itens, id);
    return marcarCardBusca(itemDados && criarCardItem(itemDados, detalhes.itens), item);
  }
  if (item.href === "/wiki/equipaveis") {
    const equipavel = encontrarPorId(detalhes.equipaveis?.equipaveis, id);
    return marcarCardBusca(equipavel && criarCardEquipavel(equipavel, detalhes.equipaveis), item);
  }
  if (item.href === "/wiki/npcs") {
    const npc = encontrarPorId(detalhes.npcs?.npcs, id);
    return marcarCardBusca(npc && criarCardNpc(npc, detalhes.npcs, "busca-global"), item);
  }
  if (item.href === "/wiki/mundo") {
    const estrutura = encontrarPorId(detalhes.mundo?.estruturas, id);
    return marcarCardBusca(estrutura && criarCardEstrutura(estrutura, detalhes.mundo), item);
  }
  if (item.href === "/wiki/dungeons") {
    const dungeon = encontrarPorId(detalhes.dungeons?.dungeons, id);
    return marcarCardBusca(dungeon && criarCardDungeon(dungeon, detalhes.dungeons), item);
  }
  if (item.href === "/wiki/estadios") {
    const estadio = encontrarPorId(detalhes.estadios?.estadios, id);
    return marcarCardBusca(estadio && criarCardEstadio(estadio, detalhes.estadios), item);
  }
  if (item.href === "/wiki/musicas") {
    const musica = encontrarPorId(detalhes.musicas?.musicas, id);
    return musica ? criarFaixaMusicaBusca(musica, item) : null;
  }
  if (item.href === "/wiki/habilidades") {
    const habilidade = encontrarPorId(detalhes.habilidades?.habilidades, id);
    return marcarCardBusca(habilidade && criarCardHabilidade(habilidade), item);
  }
  if (item.href === "/wiki/comandos") {
    const comando = encontrarPorId(detalhes.comandos?.comandos, id);
    return marcarCardBusca(comando && criarCardComando(comando), item);
  }
  return null;
}

function criarControladoresDetalhe(detalhes) {
  const pokemonController = criarControladorDetalhePokemon(detalhes.pokedex, {
    obterListaAtual: () => detalhes.pokedex?.pokemons || [],
    seletorAtaqueDetalhe: "[data-ataque-detail]",
  });
  const controladores = {
    pokemons: pokemonController,
    ataques: { abrirDetalhe: pokemonController.abrirAtaqueDetalhe },
    efeitos: criarControladorDetalheEfeitos(detalhes.efeitos, () => detalhes.efeitos?.efeitos || []),
    itens: criarControladorDetalheItens(detalhes.itens, () => detalhes.itens?.itens || []),
    equipaveis: criarControladorDetalheEquipaveis(detalhes.equipaveis, () => detalhes.equipaveis?.equipaveis || []),
    mundo: criarControladorDetalheMundo(detalhes.mundo),
    dungeons: null,
    npcs: null,
    estadios: null,
    habilidades: criarControladorDetalheHabilidades(detalhes.habilidades, () => detalhes.habilidades?.habilidades || []),
    comandos: criarControladorDetalheComandos(detalhes.comandos, () => detalhes.comandos?.comandos || []),
  };

  const npcPokemonController = criarControladorDetalhePokemon(detalhes.pokedex, {
    seletorDetalhe: "[data-npc-pokemon-detail]",
    mostrarLinhagem: true,
    seletorAtaqueDetalhe: "[data-busca-global-ataque-npc-inexistente]",
  });
  controladores.npcs = criarControladorDetalheNpc(detalhes.npcs, detalhes.pokedex, {
    obterListaAtual: () => detalhes.npcs?.npcs || [],
  });
  document.querySelector("[data-npc-detail]")?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-pokemon-id]");
    if (card) npcPokemonController.abrirDetalhe(card.dataset.pokemonId);
  });

  const dungeonPokemonController = criarControladorDetalhePokemon(detalhes.pokedex, {
    seletorDetalhe: "[data-dungeon-pokemon-detail]",
    mostrarLinhagem: true,
    seletorAtaqueDetalhe: "[data-busca-global-ataque-dungeon-inexistente]",
  });
  controladores.dungeons = criarControladorDetalheDungeons(detalhes.dungeons, detalhes.pokedex, () => detalhes.dungeons?.dungeons || []);
  document.querySelector("[data-dungeon-detail]")?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-pokemon-id]");
    if (card) dungeonPokemonController.abrirDetalhe(card.dataset.pokemonId);
  });

  const estadioNpcController = criarControladorDetalheNpc(detalhes.estadios, detalhes.pokedex, {
    seletorDetalhe: "[data-estadio-npc-detail]",
    obterListaAtual: () => detalhes.estadios?.npcs || [],
  });
  const estadioPokemonController = criarControladorDetalhePokemon(detalhes.pokedex, {
    seletorDetalhe: "[data-estadio-pokemon-detail]",
    mostrarLinhagem: true,
    seletorAtaqueDetalhe: "[data-busca-global-ataque-estadio-inexistente]",
  });
  controladores.estadios = criarControladorEstadio(detalhes.estadios, () => detalhes.estadios?.estadios || [], estadioNpcController);
  document.querySelector("[data-estadio-npc-detail]")?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-pokemon-id]");
    if (card) estadioPokemonController.abrirDetalhe(card.dataset.pokemonId);
  });

  return controladores;
}

function abrirDetalheResultado(item, controladores) {
  const id = item.ref;
  if (item.href === "/wiki/pokemons") controladores.pokemons?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/ataques") controladores.ataques?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/efeitos") controladores.efeitos?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/itens") controladores.itens?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/equipaveis") controladores.equipaveis?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/npcs") controladores.npcs?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/mundo") controladores.mundo?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/dungeons") controladores.dungeons?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/estadios") controladores.estadios?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/habilidades") controladores.habilidades?.abrirDetalhe?.(id);
  else if (item.href === "/wiki/comandos") controladores.comandos?.abrirDetalhe?.(id);
}

function atualizarFiltrosVisuais(filtros, selecionados) {
  filtros.forEach((botao) => {
    const ativo = selecionados.has(botao.dataset.wikiGlobalFilter || "");
    botao.classList.toggle("ativo", ativo);
    botao.setAttribute("aria-pressed", ativo ? "true" : "false");
  });
}

function filtrarPorWiki(resultados, selecionados) {
  if (!selecionados.size) return resultados;
  return resultados.filter((item) => selecionados.has(item.categoria));
}

export function inicializarBuscaGlobalWiki(idDados = "wiki-global-search-data") {
  const dados = lerJson(idDados, "Busca global da wiki");
  const raiz = document.querySelector("[data-wiki-global-search-root]");
  if (!dados || !raiz) return;
  const input = raiz.querySelector("[data-wiki-global-search]");
  const secoes = document.querySelector("[data-wiki-menu-secoes]");
  const resultadosSecao = document.querySelector("[data-wiki-global-results-section]");
  const resultadosGrid = document.querySelector("[data-wiki-global-results]");
  const vazio = document.querySelector("[data-wiki-global-empty]");
  const status = raiz.querySelector("[data-wiki-global-status]");
  const filtrosWrapper = document.querySelector("[data-wiki-global-filters]");
  const filtros = [...document.querySelectorAll("[data-wiki-global-filter]")];
  const volumeControle = document.querySelector("[data-wiki-global-volume]");
  const itens = Array.isArray(dados.itens) ? dados.itens : [];
  const detalhes = dados.detalhes || {};
  const controladores = criarControladoresDetalhe(detalhes);
  const selecionados = new Set();
  let renderId = 0;

  volumeGlobal = lerVolumeSalvo();
  if (volumeControle) volumeControle.value = String(volumeGlobal);

  function atualizar() {
    const termo = input?.value?.trim() ?? "";
    const ativo = termo.length > 0;
    const idAtual = ++renderId;
    const resultadosBrutos = ativo ? buscar(itens, termo) : [];
    const resultados = filtrarPorWiki(resultadosBrutos, selecionados);
    const totalLimitado = Math.min(resultados.length, LIMITE_RESULTADOS);
    if (secoes) secoes.hidden = ativo;
    if (resultadosSecao) resultadosSecao.hidden = !ativo;
    if (filtrosWrapper) filtrosWrapper.hidden = !ativo;
    if (vazio) vazio.hidden = !ativo || resultados.length > 0;
    if (status) {
      if (!ativo) {
        status.textContent = `${itens.length} cartuchos e faixas indexados para busca rápida.`;
      } else if (selecionados.size) {
        status.textContent = `${resultados.length} de ${resultadosBrutos.length} resultado${resultadosBrutos.length === 1 ? "" : "s"} encontrado${resultadosBrutos.length === 1 ? "" : "s"}.`;
      } else {
        status.textContent = `${resultados.length} resultado${resultados.length === 1 ? "" : "s"} encontrado${resultados.length === 1 ? "" : "s"}.`;
      }
    }
    if (!resultadosGrid) return;
    resultadosGrid.replaceChildren();
    if (!ativo || !resultados.length) return;
    window.requestAnimationFrame(() => {
      if (idAtual !== renderId) return;
      const fragmento = document.createDocumentFragment();
      resultados.slice(0, totalLimitado).forEach((item) => {
        const card = criarResultadoCard(item, detalhes);
        if (!card) return;
        if (item.href !== "/wiki/musicas") {
          card.addEventListener("click", () => abrirDetalheResultado(item, controladores));
        }
        fragmento.appendChild(card);
      });
      resultadosGrid.appendChild(fragmento);
      aplicarVolumeGlobal(resultadosGrid);
    });
  }

  filtros.forEach((botao) => {
    const chave = botao.dataset.wikiGlobalFilter || "";
    if (!FILTROS_WIKI.includes(chave)) return;
    botao.addEventListener("click", () => {
      if (selecionados.has(chave)) selecionados.delete(chave);
      else selecionados.add(chave);
      atualizarFiltrosVisuais(filtros, selecionados);
      atualizar();
    });
  });
  volumeControle?.addEventListener("input", () => {
    volumeGlobal = limitarVolume(volumeControle.value);
    salvarVolume(volumeGlobal);
    aplicarVolumeGlobal(resultadosGrid || document);
  });
  input?.addEventListener("input", atualizar);
  atualizarFiltrosVisuais(filtros, selecionados);
  atualizar();
}
