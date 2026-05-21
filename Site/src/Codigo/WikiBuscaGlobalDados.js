import { indexarPublicoPorNome, listarImagensPublicas } from "./AssetsPublicos.js";
import { carregarAtaques, criarAssetsAtaques, indexarIconesAtaques } from "./AtaquesWikiDados.js";
import { carregarComandos } from "./ComandosWikiDados.js";
import { carregarDungeons, criarAssetsDungeons, indexarIconesDungeons } from "./DungeonsWikiDados.js";
import { carregarEfeitos, criarAssetsEfeitos, indexarIconesEfeitos } from "./EfeitosWikiDados.js";
import { carregarEquipaveis, criarAssetsEquipaveis } from "./EquipaveisWikiDados.js";
import { carregarHabilidades } from "./HabilidadesWikiDados.js";
import { carregarItens, criarAssetsItens, indexarImagensItens } from "./ItemWikiDados.js";
import { carregarWikiMundo, criarAssetsEstruturas } from "./MundoWikiDados.js";
import { carregarMusicas } from "./MusicasWikiDados.js";
import {
  carregarEstadios,
  carregarNpcs,
  criarAssetsEstadios,
  criarAssetsNpcs,
  indexarIconesEstadios,
  indexarSkinsNpcs,
} from "./NpcsWikiDados.js";
import { ATRIBUTOS_BASE, carregarPokemons, criarAssetsPokemons, normalizarChave } from "./PokemonWikiDados.js";

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

function imagemAsset(assets, id) {
  return assets?.[id]?.imagem ?? null;
}

function tipoCompacto(tipo, iconesTipos) {
  const nome = String(tipo?.nome ?? tipo ?? "").trim();
  const chave = normalizarChave(nome);
  return {
    nome,
    chave,
    chance: tipo?.chance ?? "",
    icone: iconesTipos?.[chave] ?? "",
  };
}


function categoriaPadrao(href, tipo, modelo) {
  if (href === "/wiki/pokemons") return "pokemons";
  if (href === "/wiki/ataques") return "ataques";
  if (href === "/wiki/itens" || href === "/wiki/equipaveis") return "itens";
  if (href === "/wiki/npcs") return "npcs";
  if (href === "/wiki/mundo" && String(tipo || "").toLowerCase().includes("estrutura")) return "estruturas";
  if (href === "/wiki/mundo" && String(tipo || "").toLowerCase().includes("bioma")) return "estruturas";
  if (href === "/wiki/musicas") return "musicas";
  if (href === "/wiki/habilidades") return "habilidades";
  if (href === "/wiki/comandos") return "comandos";
  if (href === "/wiki/dungeons") return "dungeons";
  if (href === "/wiki/estadios") return "estadios";
  return "outros";
}

function resultado({ href, id, titulo, tipo, meta, descricao = "", codigo = "", buscaExtra = "", modelo = "item", card = {}, categoria = "" }) {
  const secao = secoes(href);
  const tituloLimpo = String(titulo ?? secao.titulo).trim() || secao.titulo;
  const metaLimpa = String(meta ?? secao.titulo).trim() || secao.titulo;
  const descricaoLimpa = limitarTexto(descricao || secao.texto || "");
  const categoriaFinal = categoria || categoriaPadrao(href, tipo, modelo);
  return {
    id: `${href}:${id ?? tituloLimpo}`,
    ref: String(id ?? tituloLimpo),
    href,
    emoji: secao.emoji,
    secao: secao.titulo,
    categoria: categoriaFinal,
    tipo,
    titulo: tituloLimpo,
    tituloBusca: busca(tituloLimpo),
    codigo: String(codigo ?? ""),
    meta: metaLimpa,
    descricao: descricaoLimpa,
    modelo,
    card,
    busca: busca(secao.titulo, tipo, tituloLimpo, codigo, metaLimpa, descricaoLimpa, buscaExtra),
  };
}

function criarAssetsBuscaGlobal() {
  const pokemons = carregarPokemons();
  const ataques = carregarAtaques();
  const efeitos = carregarEfeitos();
  const itens = carregarItens();
  const equipaveis = carregarEquipaveis();
  const npcs = carregarNpcs();
  const estadios = carregarEstadios(npcs);
  const mundo = carregarWikiMundo();
  const { estruturas = [], biomas = [], captura = {} } = mundo;
  const dungeons = carregarDungeons();
  const musicas = carregarMusicas();
  const habilidades = carregarHabilidades();
  const comandos = carregarComandos();

  const iconesTipos = indexarPublicoPorNome("Tipos");
  const iconesAtributos = indexarPublicoPorNome("Atributos");
  return {
    pokemons,
    ataques,
    efeitos,
    itens,
    equipaveis,
    npcs,
    estadios,
    estruturas,
    biomas,
    dungeons,
    musicas,
    habilidades,
    comandos,
    captura,
    iconesTipos,
    iconesAtributos,
    assetsPokemons: criarAssetsPokemons(pokemons, indexarPublicoPorNome("Imagens")),
    assetsAtaques: criarAssetsAtaques(ataques, indexarIconesAtaques(listarImagensPublicas("Ataques"))),
    assetsEfeitos: criarAssetsEfeitos(efeitos, indexarIconesEfeitos(listarImagensPublicas("Efeitos"))),
    assetsItens: criarAssetsItens(itens, indexarImagensItens(listarImagensPublicas([
      "Itens",
      "Objetos",
      "Recursos",
      "Recursos/Itens",
      "Recursos/Objetos",
      "Recursos/Visual/Itens",
      "Recursos/Visual/Objetos",
      "Visual/Itens",
      "Visual/Objetos",
    ]))),
    assetsEquipaveis: criarAssetsEquipaveis(equipaveis, indexarPublicoPorNome(["Equipaveis", "Equipáveis", "Objetos", "Itens", "Recursos"])),
    assetsNpcs: criarAssetsNpcs(npcs, indexarSkinsNpcs(listarImagensPublicas("Skins"))),
    assetsEstadios: criarAssetsEstadios(estadios, indexarIconesEstadios(listarImagensPublicas(["Insigneas", "Insignias", "Insígnias"]))),
    assetsEstruturas: criarAssetsEstruturas(estruturas, [
      indexarPublicoPorNome(["Objetos", "Recursos/Objetos", "Recursos/Visual/Objetos", "Visual/Objetos", "Mundo/Objetos"]),
      indexarPublicoPorNome(["Mundo", "Recursos/Mundo", "Recursos/Visual/Mundo"]),
      indexarPublicoPorNome(["Ferramentas", "Itens", "Recursos", "Recursos/Itens", "Recursos/Visual/Itens"]),
    ]),
    assetsDungeons: criarAssetsDungeons(dungeons, indexarIconesDungeons(listarImagensPublicas(["Medalhoes", "Medalhões", "Dungeons"]))),
  };
}

function resultadosDePokemons(ctx) {
  return ctx.pokemons.map((pokemon) => {
    const nome = pokemon.nomeExibicao || pokemon.nome;
    return resultado({
      href: "/wiki/pokemons",
      id: pokemon.id,
      titulo: nome,
      tipo: "Cartucho de Pokémon",
      codigo: `#${pokemon.id}`,
      meta: juntar([pokemon.grupo, pokemon.tipos?.map((tipo) => tipo.nome).join(" / ")]),
      descricao: `Poder total ${pokemon.total ?? 0}. Foco principal: ${pokemon.focoAtributo || "-"}.`,
      buscaExtra: pokemon.busca,
      modelo: "pokemon",
      card: {
        codigo: `#${pokemon.id}`,
        nome,
        meta: pokemon.grupo,
        imagem: imagemAsset(ctx.assetsPokemons, pokemon.id),
        fallback: String(nome || "P").slice(0, 1),
        tipos: (pokemon.tipos || []).map((tipo) => tipoCompacto(tipo, ctx.iconesTipos)),
        poder: pokemon.total,
        radiante: busca(pokemon.nome).includes("radiante"),
      },
    });
  });
}

function resultadosDeAtaques(ctx) {
  return ctx.ataques.map((ataque) => resultado({
    href: "/wiki/ataques",
    id: ataque.uid || ataque.id,
    titulo: ataque.nome,
    tipo: "Cartucho de ataque",
    codigo: `#${ataque.codigoExibicao || ataque.id}`,
    meta: juntar([ataque.tipo, ataque.estiloRotulo, ataque.custo !== null ? `Custo ${ataque.custo}` : "Custo -"]),
    descricao: ataque.descricao,
    buscaExtra: busca(ataque.busca, ataque.motorTexto, ataque.focoPrincipal),
    modelo: "item",
    card: {
      classe: "item-card ataque-card",
      arteClasse: "item-card-arte ataque-card-arte",
      codigo: `#${ataque.codigoExibicao || ataque.id}`,
      nome: ataque.nome,
      imagem: imagemAsset(ctx.assetsAtaques, ataque.uid || ataque.id),
      fallback: String(ataque.nome || "A").slice(0, 1),
      linhaValor: ataque.custo,
      linhaRotulo: "Custo",
    },
  }));
}

function resultadosDeEfeitos(ctx) {
  return ctx.efeitos.map((efeito) => resultado({
    href: "/wiki/efeitos",
    id: efeito.id,
    titulo: efeito.nome,
    tipo: "Cartucho de efeito",
    codigo: `#${efeito.id}`,
    meta: juntar([efeito.estiloRotulo, efeito.sentidoRotulo]),
    descricao: efeito.descricao,
    buscaExtra: efeito.busca,
    modelo: "item",
    card: {
      classe: "item-card efeito-card",
      arteClasse: "item-card-arte efeito-card-arte",
      codigo: `#${efeito.id}`,
      nome: efeito.nome,
      imagem: imagemAsset(ctx.assetsEfeitos, efeito.id),
      fallback: String(efeito.nome || "E").slice(0, 1),
    },
  }));
}

function resultadosDeItens(ctx) {
  return ctx.itens.map((item) => resultado({
    href: "/wiki/itens",
    id: item.id,
    titulo: item.nome,
    tipo: "Cartucho de item",
    codigo: `#${item.id}`,
    meta: juntar([item.estiloRotulo, item.raridadeNome, item.valor ? `${item.valor} moedas` : "Sem valor"]),
    descricao: item.descricaoMelhor,
    buscaExtra: item.busca,
    modelo: "item",
    card: {
      classe: `item-card ${item.raridadeClasse || "raridade-comum"}`,
      codigo: `#${item.id}`,
      nome: item.nome,
      meta: item.estiloRotulo,
      imagem: imagemAsset(ctx.assetsItens, item.id),
      fallback: String(item.nome || "I").slice(0, 1),
      linhaValor: item.valor,
      linhaRotulo: "Valor médio",
      pillTexto: item.raridadeNome,
      pillClasse: item.raridadeClasse,
    },
  }));
}

function resultadosDeEquipaveis(ctx) {
  return ctx.equipaveis.map((equipavel) => resultado({
    href: "/wiki/equipaveis",
    id: equipavel.id,
    titulo: equipavel.nome,
    tipo: "Cartucho de equipável",
    codigo: `#${equipavel.id}`,
    meta: juntar([equipavel.afinidade || "Sem afinidade", equipavel.focoPrincipal]),
    descricao: equipavel.descricao,
    buscaExtra: busca(equipavel.busca, equipavel.passiva, equipavel.formaFinal),
    modelo: "item",
    card: {
      classe: "item-card equipavel-card",
      arteClasse: "item-card-arte equipavel-card-arte",
      codigo: `#${equipavel.id}`,
      nome: equipavel.nome,
      metaClasse: "item-card-meta equipavel-afinidade-card",
      afinidade: tipoCompacto(equipavel.afinidades?.[0] || equipavel.afinidade, ctx.iconesTipos),
      meta: equipavel.afinidade,
      imagem: imagemAsset(ctx.assetsEquipaveis, equipavel.id),
      fallback: String(equipavel.nome || "E").slice(0, 1),
    },
  }));
}

function resultadosDeNpcsEEstadios(ctx) {
  const resultadosNpcs = ctx.npcs.map((npc) => resultado({
    href: "/wiki/npcs",
    id: npc.id,
    titulo: npc.nome,
    tipo: "Cartucho de NPC",
    codigo: `#${npc.codigo}`,
    meta: juntar([npc.tipoRotulo, npc.cargo || npc.categoria, npc.nivel ? `Nível ${npc.nivel}` : "Nível -"]),
    descricao: npc.tipo === "combatente" ? `Equipe: ${juntar(npc.pokemons, "Não informada")}` : `Vendedor de ${npc.categoria || "itens"}.`,
    buscaExtra: npc.busca,
    modelo: "item",
    card: {
      classe: `item-card npc-card npc-card-${npc.tipo}`,
      arteClasse: "item-card-arte npc-card-arte",
      codigo: `#${npc.codigo}`,
      nome: npc.nome,
      meta: npc.tipoRotulo,
      imagem: imagemAsset(ctx.assetsNpcs, npc.id),
      fallback: String(npc.nome || "N").slice(0, 1),
    },
  }));
  const resultadosEstadios = ctx.estadios.map((estadio) => resultado({
    href: "/wiki/estadios",
    id: estadio.id,
    titulo: estadio.nome,
    tipo: "Cartucho de estádio",
    codigo: `#${estadio.id}`,
    meta: juntar([estadio.nomeTipo, `${estadio.membrosQuantidade ?? 0} membros`]),
    descricao: `Estádio do tipo ${estadio.nomeTipo}, com líderes e associados próprios.`,
    buscaExtra: estadio.busca,
    modelo: "item",
    card: {
      classe: "item-card estadio-card",
      arteClasse: "item-card-arte estadio-card-arte",
      codigo: `#${estadio.id}`,
      nome: estadio.nome,
      imagem: imagemAsset(ctx.assetsEstadios, estadio.id),
      fallback: String(estadio.nomeTipo || estadio.nome || "E").slice(0, 1),
    },
  }));
  return [...resultadosNpcs, ...resultadosEstadios];
}

function resultadosDeMundo(ctx) {
  const resultadosEstruturas = ctx.estruturas.map((estrutura) => resultado({
    href: "/wiki/mundo",
    id: estrutura.id,
    titulo: estrutura.nome,
    tipo: "Estrutura natural",
    codigo: `#${estrutura.id}`,
    meta: juntar([estrutura.material, estrutura.ferramenta, estrutura.biomasTexto]),
    descricao: estrutura.descricao || `Estrutura natural encontrada em ${estrutura.biomasTexto}.`,
    buscaExtra: busca(estrutura.subtipo, estrutura.slug, estrutura.sprite, estrutura.origemEspecial, estrutura.biomas?.map((bioma) => bioma.nome)),
    modelo: "item",
    card: {
      classe: "item-card mundo-card",
      arteClasse: "item-card-arte mundo-card-arte",
      codigo: `#${estrutura.id}`,
      nome: estrutura.nome,
      meta: estrutura.material || "Sem material",
      imagem: imagemAsset(ctx.assetsEstruturas, estrutura.id),
      fallback: String(estrutura.nome || "M").slice(0, 1),
    },
  }));
  return resultadosEstruturas;
}

function resultadosDeDungeons(ctx) {
  return ctx.dungeons.map((dungeon) => resultado({
    href: "/wiki/dungeons",
    id: dungeon.id,
    titulo: dungeon.nome,
    tipo: "Cartucho de dungeon",
    codigo: `#${dungeon.id}`,
    meta: juntar([dungeon.tamanhoRotulo, dungeon.dificuldadeRotulo, dungeon.entradas ? `${dungeon.entradas} entradas` : "Entradas -"]),
    descricao: `Biomas: ${juntar(dungeon.biomas, "Não informados")}. Pokémons: ${juntar(dungeon.pokemons, "Não informados")}.`,
    buscaExtra: dungeon.busca,
    modelo: "item",
    card: {
      classe: "item-card dungeon-card",
      arteClasse: "item-card-arte dungeon-card-arte",
      codigo: `#${dungeon.id}`,
      nome: dungeon.nome,
      imagem: imagemAsset(ctx.assetsDungeons, dungeon.id),
      fallback: String(dungeon.nome || "D").slice(0, 1),
      linhaValor: dungeon.dificuldadeRotulo,
      linhaRotulo: "Dificuldade",
    },
  }));
}

function resultadosDeMusicas(ctx) {
  return ctx.musicas.map((musica) => resultado({
    href: "/wiki/musicas",
    id: musica.id,
    titulo: musica.nome,
    tipo: "Faixa de música",
    meta: juntar([musica.estiloRotulo, musica.pasta, musica.extensao]),
    descricao: musica.caminho,
    buscaExtra: musica.busca,
    modelo: "musica",
    card: {
      id: musica.id,
      nome: musica.nome,
      estiloRotulo: musica.estiloRotulo,
      url: musica.url,
      duracao: musica.duracao,
    },
  }));
}

function resultadosDeHabilidades(ctx) {
  return ctx.habilidades.map((habilidade) => resultado({
    href: "/wiki/habilidades",
    id: habilidade.id,
    titulo: habilidade.nome,
    tipo: "Cartucho de habilidade",
    codigo: habilidade.sigla,
    meta: juntar([habilidade.ramoRotulo, habilidade.grupoRotulo, `Nível ${habilidade.nivel}`]),
    descricao: habilidade.descricao,
    buscaExtra: habilidade.busca,
    modelo: "item",
    card: {
      classe: `item-card habilidade-card habilidade-${habilidade.ramo}`,
      arteClasse: "item-card-arte habilidade-card-arte",
      codigo: `#${habilidade.codigo || habilidade.id}`,
      nome: habilidade.nome,
      meta: habilidade.sigla || `N${habilidade.nivel}`,
      fallback: habilidade.grupoEmoji || "✦",
      fallbackClasse: "item-card-sem-arte habilidade-card-emoji",
      linhaValor: habilidade.grupoRotulo,
      linhaRotulo: "Grupo",
    },
  }));
}

function resultadosDeComandos(ctx) {
  return ctx.comandos.map((comando) => resultado({
    href: "/wiki/comandos",
    id: comando.id,
    titulo: comando.titulo || `/${comando.nome}`,
    tipo: "Cartucho de comando",
    codigo: comando.uso,
    meta: juntar([comando.localRotulo, comando.nivelRotulo]),
    descricao: comando.descricao,
    buscaExtra: comando.busca,
    modelo: "item",
    card: {
      classe: `item-card comando-card comando-${comando.local} nivel-${comando.nivel >= 2 ? "avancado" : "basico"}`,
      arteClasse: "item-card-arte comando-card-arte",
      codigo: `#${comando.codigo || comando.id}`,
      nome: `/${comando.nome}`,
      meta: comando.localRotulo,
      fallback: "💻",
      fallbackClasse: "item-card-sem-arte comando-card-emoji",
      linhaValor: comando.nivelRotulo,
      linhaRotulo: "Permissão",
    },
  }));
}

function montarIndiceComContexto(ctx) {
  return [
    ...resultadosDePokemons(ctx),
    ...resultadosDeAtaques(ctx),
    ...resultadosDeEfeitos(ctx),
    ...resultadosDeItens(ctx),
    ...resultadosDeEquipaveis(ctx),
    ...resultadosDeNpcsEEstadios(ctx),
    ...resultadosDeMundo(ctx),
    ...resultadosDeDungeons(ctx),
    ...resultadosDeMusicas(ctx),
    ...resultadosDeHabilidades(ctx),
    ...resultadosDeComandos(ctx),
  ].map((item, ordem) => ({ ...item, ordem }));
}

function montarDetalhesBuscaGlobal(ctx) {
  const pokedex = {
    pokemons: ctx.pokemons,
    ataques: ctx.ataques,
    assetsPokemons: ctx.assetsPokemons,
    assetsAtaques: ctx.assetsAtaques,
    iconesTipos: ctx.iconesTipos,
    iconesAtributos: ctx.iconesAtributos,
    atributosBase: ATRIBUTOS_BASE,
  };
  return {
    pokedex,
    ataques: { ataques: ctx.ataques, assetsAtaques: ctx.assetsAtaques, iconesTipos: ctx.iconesTipos },
    efeitos: { efeitos: ctx.efeitos, assetsEfeitos: ctx.assetsEfeitos },
    itens: { itens: ctx.itens, assetsItens: ctx.assetsItens },
    equipaveis: {
      equipaveis: ctx.equipaveis,
      assetsEquipaveis: ctx.assetsEquipaveis,
      iconesTipos: ctx.iconesTipos,
      iconesAtributos: ctx.iconesAtributos,
    },
    npcs: { npcs: ctx.npcs, assetsNpcs: ctx.assetsNpcs },
    estadios: {
      estadios: ctx.estadios,
      npcs: ctx.npcs,
      assetsEstadios: ctx.assetsEstadios,
      assetsNpcs: ctx.assetsNpcs,
    },
    mundo: {
      estruturas: ctx.estruturas,
      biomas: ctx.biomas,
      captura: ctx.captura,
      assetsEstruturas: ctx.assetsEstruturas,
    },
    dungeons: { dungeons: ctx.dungeons, assetsDungeons: ctx.assetsDungeons },
    musicas: { musicas: ctx.musicas },
    habilidades: { habilidades: ctx.habilidades },
    comandos: { comandos: ctx.comandos },
  };
}

export function montarDadosBuscaGlobalWiki() {
  const ctx = criarAssetsBuscaGlobal();
  return {
    itens: montarIndiceComContexto(ctx),
    detalhes: montarDetalhesBuscaGlobal(ctx),
  };
}

export function montarIndiceBuscaWiki() {
  return montarDadosBuscaGlobalWiki().itens;
}
