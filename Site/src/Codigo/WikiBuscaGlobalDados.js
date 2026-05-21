import { carregarAtaques } from "./AtaquesWikiDados.js";
import { carregarComandos } from "./ComandosWikiDados.js";
import { carregarWikiCombate } from "./CombateWikiDados.js";
import { carregarDungeons } from "./DungeonsWikiDados.js";
import { carregarEfeitos } from "./EfeitosWikiDados.js";
import { carregarEquipaveis } from "./EquipaveisWikiDados.js";
import { carregarHabilidades } from "./HabilidadesWikiDados.js";
import { carregarItens } from "./ItemWikiDados.js";
import { carregarWikiMundo } from "./MundoWikiDados.js";
import { carregarMusicas } from "./MusicasWikiDados.js";
import { carregarEstadios, carregarNpcs } from "./NpcsWikiDados.js";
import { carregarPokemons, normalizarChave } from "./PokemonWikiDados.js";

export const SECOES_WIKI = [
  {
    href: "/wiki/pokemons",
    emoji: "🐾",
    titulo: "Pokémons",
    texto: "Pokédex com busca, filtros, atributos, tipagens, raridades e linhagens.",
  },
  {
    href: "/wiki/lore",
    emoji: "📖",
    titulo: "Lore",
    texto: "Espaço reservado para história, regiões, personagens e contexto do universo do jogo.",
  },
  {
    href: "/wiki/ataques",
    emoji: "⚡",
    titulo: "Ataques",
    texto: "Ataques com custo, tipo, estilo, motor, foco, descrição e aprimoramento.",
  },
  {
    href: "/wiki/efeitos",
    emoji: "✨",
    titulo: "Efeitos",
    texto: "Status de Pokémon, climas, terrenos, sentido, passos base e descrições.",
  },
  {
    href: "/wiki/itens",
    emoji: "🎒",
    titulo: "Itens",
    texto: "Consumíveis, doces, equipamentos, receitas e itens especiais do jogo.",
  },
  {
    href: "/wiki/equipaveis",
    emoji: "🛡️",
    titulo: "Equipáveis",
    texto: "Equipamentos, bônus, raridades, slots e efeitos aplicados aos Pokémons.",
  },
  {
    href: "/wiki/tipos",
    emoji: "🧬",
    titulo: "Tipos",
    texto: "Tabela de efetividade, fraquezas, resistências e imunidades dos tipos do jogo.",
  },
  {
    href: "/wiki/npcs",
    emoji: "🧍",
    titulo: "NPCs",
    texto: "Combatentes, vendedores, cargos, categorias, níveis, skins e equipes de Pokémon.",
  },
  {
    href: "/wiki/mundo",
    emoji: "🌍",
    titulo: "Mundo",
    texto: "Biomas, chunks, exploração, vilas, rotas, mapa e geração do mundo.",
  },
  {
    href: "/wiki/combate",
    emoji: "⚔️",
    titulo: "Combate",
    texto: "Regras de batalha, turnos, energia, dano, colisões, indicadores e animações.",
  },
  {
    href: "/wiki/dungeons",
    emoji: "🗺️",
    titulo: "Dungeons",
    texto: "Áreas fechadas, desafios especiais, progressão, recompensas e exploração por etapas.",
  },
  {
    href: "/wiki/estadios",
    emoji: "🏟️",
    titulo: "Estádios",
    texto: "Estádios de cada tipo, progressão de respeito, insígnias, líderes e associados.",
  },
  {
    href: "/wiki/musicas",
    emoji: "🎵",
    titulo: "Músicas",
    texto: "Faixas do jogo com player, busca, filtro por estilo, ordem oficial e duração.",
  },
  {
    href: "/wiki/habilidades",
    emoji: "🌟",
    titulo: "Habilidades",
    texto: "Árvore de skills do jogador com ramos, níveis, grupos, efeitos e dependências.",
  },
  {
    href: "/wiki/comandos",
    emoji: "⌨️",
    titulo: "Comandos",
    texto: "Comandos disponíveis, atalhos, permissões e ações rápidas para usar dentro do jogo.",
  },
];

const SECOES_POR_HREF = new Map(SECOES_WIKI.map((secao) => [secao.href, secao]));

function secoes(href) {
  return SECOES_POR_HREF.get(href) ?? { href, emoji: "✨", titulo: "Wiki", texto: "Resultado da wiki." };
}

function texto(...partes) {
  return partes
    .flat(Infinity)
    .filter((parte) => parte !== null && parte !== undefined && parte !== "")
    .join(" ");
}

function busca(...partes) {
  return normalizarChave(texto(...partes));
}

function limitarTexto(valor, limite = 150) {
  const limpo = String(valor ?? "").replace(/\s+/g, " ").trim();
  if (limpo.length <= limite) return limpo;
  return `${limpo.slice(0, limite - 1).trim()}…`;
}

function juntar(lista, vazio = "Não informado") {
  const valores = Array.isArray(lista) ? lista.filter(Boolean) : [lista].filter(Boolean);
  return valores.length ? valores.join(" • ") : vazio;
}

function resultado({ href, id, titulo, tipo, meta, descricao = "", codigo = "", buscaExtra = "" }) {
  const secao = secoes(href);
  const tituloLimpo = String(titulo ?? secao.titulo).trim() || secao.titulo;
  const metaLimpa = String(meta ?? secao.titulo).trim() || secao.titulo;
  const descricaoLimpa = limitarTexto(descricao || secao.texto || "");
  return {
    id: `${href}:${id ?? tituloLimpo}`,
    href,
    emoji: secao.emoji,
    secao: secao.titulo,
    tipo,
    titulo: tituloLimpo,
    tituloBusca: busca(tituloLimpo),
    codigo: String(codigo ?? ""),
    meta: metaLimpa,
    descricao: descricaoLimpa,
    busca: busca(secao.titulo, tipo, tituloLimpo, codigo, metaLimpa, descricaoLimpa, buscaExtra),
  };
}

function resultadosDeSecoes() {
  return SECOES_WIKI.map((secao) => resultado({
    href: secao.href,
    id: "pagina",
    titulo: secao.titulo,
    tipo: "Página da wiki",
    meta: "Entrada principal da seção",
    descricao: secao.texto,
    buscaExtra: secao.emoji,
  }));
}

function resultadosDePokemons() {
  return carregarPokemons().map((pokemon) => resultado({
    href: "/wiki/pokemons",
    id: pokemon.id,
    titulo: pokemon.nomeExibicao || pokemon.nome,
    tipo: "Cartucho de Pokémon",
    codigo: `#${pokemon.id}`,
    meta: juntar([pokemon.grupo, pokemon.tipos?.map((tipo) => tipo.nome).join(" / ")]),
    descricao: `Poder total ${pokemon.total ?? 0}. Foco principal: ${pokemon.focoAtributo || "-"}.`,
    buscaExtra: pokemon.busca,
  }));
}

function resultadosDeAtaques() {
  return carregarAtaques().map((ataque) => resultado({
    href: "/wiki/ataques",
    id: ataque.uid || ataque.id,
    titulo: ataque.nome,
    tipo: "Cartucho de ataque",
    codigo: `#${ataque.codigoExibicao || ataque.id}`,
    meta: juntar([ataque.tipo, ataque.estiloRotulo, ataque.custo !== null ? `Custo ${ataque.custo}` : "Custo -"]),
    descricao: ataque.descricao,
    buscaExtra: busca(ataque.busca, ataque.motorTexto, ataque.focoPrincipal),
  }));
}

function resultadosDeEfeitos() {
  return carregarEfeitos().map((efeito) => resultado({
    href: "/wiki/efeitos",
    id: efeito.id,
    titulo: efeito.nome,
    tipo: "Cartucho de efeito",
    codigo: `#${efeito.id}`,
    meta: juntar([efeito.estiloRotulo, efeito.sentidoRotulo]),
    descricao: efeito.descricao,
    buscaExtra: efeito.busca,
  }));
}

function resultadosDeItens() {
  return carregarItens().map((item) => resultado({
    href: "/wiki/itens",
    id: item.id,
    titulo: item.nome,
    tipo: "Cartucho de item",
    codigo: `#${item.id}`,
    meta: juntar([item.estiloRotulo, item.raridadeNome, item.valor ? `${item.valor} moedas` : "Sem valor"]),
    descricao: item.descricaoMelhor,
    buscaExtra: item.busca,
  }));
}

function resultadosDeEquipaveis() {
  return carregarEquipaveis().map((equipavel) => resultado({
    href: "/wiki/equipaveis",
    id: equipavel.id,
    titulo: equipavel.nome,
    tipo: "Cartucho de equipável",
    codigo: `#${equipavel.id}`,
    meta: juntar([equipavel.afinidade || "Sem afinidade", equipavel.focoPrincipal]),
    descricao: equipavel.descricao,
    buscaExtra: busca(equipavel.busca, equipavel.passiva, equipavel.formaFinal),
  }));
}

function resultadosDeTipos() {
  const { tabela = [] } = carregarWikiCombate();
  return tabela.map((tipo) => resultado({
    href: "/wiki/tipos",
    id: tipo.chave || tipo.nome,
    titulo: tipo.nome,
    tipo: "Tipo",
    meta: "Efetividades, fraquezas e resistências",
    descricao: `Super eficaz contra ${juntar(tipo.superEfetivo?.map((item) => item.nome), "-")}. Fraquezas: ${juntar(tipo.fraquezas?.map((item) => item.nome), "-")}.`,
    buscaExtra: busca(tipo.nome, tipo.superEfetivo?.map((item) => item.nome), tipo.fraquezas?.map((item) => item.nome), tipo.resistencias?.map((item) => item.nome), tipo.imunidades?.map((item) => item.nome)),
  }));
}

function resultadosDeNpcsEEstadios() {
  const npcs = carregarNpcs();
  const resultadosNpcs = npcs.map((npc) => resultado({
    href: "/wiki/npcs",
    id: npc.id,
    titulo: npc.nome,
    tipo: "Cartucho de NPC",
    codigo: `#${npc.codigo}`,
    meta: juntar([npc.tipoRotulo, npc.cargo || npc.categoria, npc.nivel ? `Nível ${npc.nivel}` : "Nível -"]),
    descricao: npc.tipo === "combatente" ? `Equipe: ${juntar(npc.pokemons, "Não informada")}` : `Vendedor de ${npc.categoria || "itens"}.`,
    buscaExtra: npc.busca,
  }));
  const resultadosEstadios = carregarEstadios(npcs).map((estadio) => resultado({
    href: "/wiki/estadios",
    id: estadio.id,
    titulo: estadio.nome,
    tipo: "Cartucho de estádio",
    codigo: `#${estadio.id}`,
    meta: juntar([estadio.nomeTipo, `${estadio.membrosQuantidade ?? 0} membros`]),
    descricao: `Estádio do tipo ${estadio.nomeTipo}, com líderes e associados próprios.`,
    buscaExtra: estadio.busca,
  }));
  return [...resultadosNpcs, ...resultadosEstadios];
}

function resultadosDeMundo() {
  const { estruturas = [], biomas = [] } = carregarWikiMundo();
  const resultadosEstruturas = estruturas.map((estrutura) => resultado({
    href: "/wiki/mundo",
    id: estrutura.id,
    titulo: estrutura.nome,
    tipo: "Estrutura natural",
    codigo: `#${estrutura.id}`,
    meta: juntar([estrutura.material, estrutura.ferramenta, estrutura.biomasTexto]),
    descricao: estrutura.descricao || `Estrutura natural encontrada em ${estrutura.biomasTexto}.`,
    buscaExtra: busca(estrutura.subtipo, estrutura.slug, estrutura.sprite, estrutura.origemEspecial, estrutura.biomas?.map((bioma) => bioma.nome)),
  }));
  const resultadosBiomas = biomas.map((bioma) => resultado({
    href: "/wiki/mundo",
    id: `bioma-${bioma.codigo}`,
    titulo: bioma.nome,
    tipo: "Bioma",
    meta: juntar([bioma.tileBase, bioma.tileCosta]),
    descricao: bioma.descricao,
    buscaExtra: busca(bioma.codigo, bioma.principaisEstruturas),
  }));
  return [...resultadosEstruturas, ...resultadosBiomas];
}

function resultadosDeDungeons() {
  return carregarDungeons().map((dungeon) => resultado({
    href: "/wiki/dungeons",
    id: dungeon.id,
    titulo: dungeon.nome,
    tipo: "Cartucho de dungeon",
    codigo: `#${dungeon.id}`,
    meta: juntar([dungeon.tamanhoRotulo, dungeon.dificuldadeRotulo, dungeon.entradas ? `${dungeon.entradas} entradas` : "Entradas -"]),
    descricao: `Biomas: ${juntar(dungeon.biomas, "Não informados")}. Pokémons: ${juntar(dungeon.pokemons, "Não informados")}.`,
    buscaExtra: dungeon.busca,
  }));
}

function resultadosDeMusicas() {
  return carregarMusicas().map((musica) => resultado({
    href: "/wiki/musicas",
    id: musica.id,
    titulo: musica.nome,
    tipo: "Faixa de música",
    meta: juntar([musica.estiloRotulo, musica.pasta, musica.extensao]),
    descricao: musica.caminho,
    buscaExtra: musica.busca,
  }));
}

function resultadosDeHabilidades() {
  return carregarHabilidades().map((habilidade) => resultado({
    href: "/wiki/habilidades",
    id: habilidade.id,
    titulo: habilidade.nome,
    tipo: "Cartucho de habilidade",
    codigo: habilidade.sigla,
    meta: juntar([habilidade.ramoRotulo, habilidade.grupoRotulo, `Nível ${habilidade.nivel}`]),
    descricao: habilidade.descricao,
    buscaExtra: habilidade.busca,
  }));
}

function resultadosDeComandos() {
  return carregarComandos().map((comando) => resultado({
    href: "/wiki/comandos",
    id: comando.id,
    titulo: comando.titulo || `/${comando.nome}`,
    tipo: "Cartucho de comando",
    codigo: comando.uso,
    meta: juntar([comando.localRotulo, comando.nivelRotulo]),
    descricao: comando.descricao,
    buscaExtra: comando.busca,
  }));
}

export function montarIndiceBuscaWiki() {
  return [
    ...resultadosDeSecoes(),
    ...resultadosDePokemons(),
    ...resultadosDeAtaques(),
    ...resultadosDeEfeitos(),
    ...resultadosDeItens(),
    ...resultadosDeEquipaveis(),
    ...resultadosDeTipos(),
    ...resultadosDeNpcsEEstadios(),
    ...resultadosDeMundo(),
    ...resultadosDeDungeons(),
    ...resultadosDeMusicas(),
    ...resultadosDeHabilidades(),
    ...resultadosDeComandos(),
  ].map((item, ordem) => ({ ...item, ordem }));
}
