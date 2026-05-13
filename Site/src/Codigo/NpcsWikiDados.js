import { campo, campoNumero, carregarCsvWiki, limparTexto } from "./WikiCsv.js";
import { normalizarChave } from "./PokemonWikiDados.js";
const CSV_COMBATENTES = [
  "Pokemon Global Server - NPC Combatente.csv",
  "Pokemon Global Server - NPC Combatente (1).csv",
  "Pokemon Global Server - NPC Combatentes.csv",
  "Pokemon Global Server - NPCs Combatentes.csv",
];
const CSV_VENDEDORES = [
  "Pokemon Global Server - NPC Vendedor.csv",
  "Pokemon Global Server - NPC Vendedor(12).csv",
  "Pokemon Global Server - NPC Vendedores.csv",
  "Pokemon Global Server - NPCs Vendedores.csv",
];
const CARGOS_CANONICOS = {
  lider: "Líder",
  capitao: "Capitão",
  desafiante: "Desafiante",
};
const TIPOS_CANONICOS = {
  agua: "Água",
  aco: "Aço",
  metal: "Metal",
  cosmico: "Cósmico",
  dragao: "Dragão",
  eletrico: "Elétrico",
  fada: "Fada",
  fantasma: "Fantasma",
  fogo: "Fogo",
  gelo: "Gelo",
  grama: "Planta",
  planta: "Planta",
  inseto: "Inseto",
  lutador: "Lutador",
  normal: "Normal",
  pedra: "Pedra",
  psiquico: "Psíquico",
  sombrio: "Sombrio",
  sonoro: "Sonoro",
  terrestre: "Terrestre",
  terra: "Terrestre",
  venenoso: "Venenoso",
  veneno: "Venenoso",
  voador: "Voador",
};
function titulo(valor) {
  const texto = limparTexto(valor);
  return texto ? texto.replace(/^./, (letra) => letra.toUpperCase()) : "";
}
function tipoCanonico(valor) {
  const texto = limparTexto(valor);
  const chave = normalizarChave(texto);
  return TIPOS_CANONICOS[chave] ?? titulo(texto);
}
function cargoCanonico(valor) {
  const texto = limparTexto(valor);
  const chave = normalizarChave(texto);
  return CARGOS_CANONICOS[chave] ?? titulo(texto || "Associado");
}
function separarLista(valor) {
  return limparTexto(valor)
    .split(/[/;,|]+/g)
    .map((item) => limparTexto(item))
    .filter(Boolean);
}
function coletarPokemons(linha) {
  const pokemons = [];
  Object.entries(linha).forEach(([chave, valor]) => {
    if (/^pokemon\s*\d+$/i.test(limparTexto(chave))) pokemons.push(...separarLista(valor));
  });
  pokemons.push(...separarLista(campo(linha, ["Pokemons", "Pokémons", "Pokemon", "Pokémon", "Equipe"], "")));
  const unicos = new Map();
  pokemons.forEach((pokemon) => {
    const chave = normalizarChave(pokemon);
    if (chave && !unicos.has(chave)) unicos.set(chave, pokemon);
  });
  return [...unicos.values()];
}
function normalizarCombatente(linha, indice) {
  const code = campoNumero(linha, ["Code", "Código", "ID", "Id"], indice + 1) ?? indice + 1;
  const nome = limparTexto(campo(linha, ["Nome", "NPC"], "")) || `Combatente ${code}`;
  const estadio = tipoCanonico(campo(linha, ["Estadio", "Estádio", "Tipo", "Tipagem"], ""));
  const cargo = cargoCanonico(campo(linha, ["Cargo", "Função", "Funcao"], ""));
  const nivel = campoNumero(linha, ["Nivel", "Nível", "Level"], null);
  const skin = limparTexto(campo(linha, ["Skin", "Icone", "Ícone", "Imagem"], ""));
  const pokemons = coletarPokemons(linha);
  const batalhas = campoNumero(linha, ["Batalhas"], null);
  return {
    id: `combatente-${code}`,
    ordem: indice + 1,
    codigo: code,
    nome,
    tipo: "combatente",
    tipoRotulo: "Combatente",
    nivel,
    skin,
    estadio,
    estadioBusca: normalizarChave(estadio),
    cargo,
    cargoBusca: normalizarChave(cargo),
    categoria: "",
    categoriaBusca: "",
    batalhas,
    pokemons,
    busca: normalizarChave(`${nome} ${code} combatente ${estadio} ${cargo} ${nivel ?? ""} ${pokemons.join(" ")}`),
  };
}
function normalizarVendedor(linha, indice, deslocamento) {
  const code = campoNumero(linha, ["Code", "Código", "ID", "Id"], deslocamento + indice + 1) ?? deslocamento + indice + 1;
  const nome = limparTexto(campo(linha, ["Nome", "NPC"], "")) || `Vendedor ${code}`;
  const categoria = titulo(campo(linha, ["Categoria", "Loja", "Tipo"], "")) || "Sem categoria";
  const nivel = campoNumero(linha, ["Nivel", "Nível", "Level"], null);
  const skin = limparTexto(campo(linha, ["Skin", "Icone", "Ícone", "Imagem"], ""));
  return {
    id: `vendedor-${code}`,
    ordem: deslocamento + indice + 1,
    codigo: code,
    nome,
    tipo: "vendedor",
    tipoRotulo: "Vendedor",
    nivel,
    skin,
    estadio: "",
    estadioBusca: "",
    cargo: "",
    cargoBusca: "",
    categoria,
    categoriaBusca: normalizarChave(categoria),
    batalhas: null,
    pokemons: [],
    busca: normalizarChave(`${nome} ${code} vendedor ${categoria} ${nivel ?? ""}`),
  };
}
export function carregarNpcs() {
  const combatentes = carregarCsvWiki(CSV_COMBATENTES, "Wiki NPCs Combatentes").map((linha, indice) => normalizarCombatente(linha, indice));
  const vendedores = carregarCsvWiki(CSV_VENDEDORES, "Wiki NPCs Vendedores").map((linha, indice) => normalizarVendedor(linha, indice, combatentes.length));
  return [...combatentes, ...vendedores];
}
function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}
export function indexarSkinsNpcs(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const chave = normalizarChave(arquivoSemExtensao(caminho));
    if (chave && !indice[chave]) indice[chave] = url;
  });
  return indice;
}
function candidatosSkin(npc) {
  const skin = String(npc.skin ?? "").trim();
  const codigo = String(npc.codigo ?? "");
  return [
    skin,
    skin.padStart(2, "0"),
    skin.padStart(3, "0"),
    `skin${skin}`,
    `npc${codigo}`,
    npc.nome,
  ].filter(Boolean).map(normalizarChave);
}
export function resolverSkinNpc(npc, skinsPorNome) {
  for (const candidato of candidatosSkin(npc)) {
    if (skinsPorNome[candidato]) return skinsPorNome[candidato];
  }
  return null;
}
export function criarAssetsNpcs(npcs, skinsPorNome) {
  return Object.fromEntries(npcs.map((npc) => [npc.id, { imagem: resolverSkinNpc(npc, skinsPorNome) }]));
}
export function resumoNpcs(npcs) {
  const combatentes = npcs.filter((npc) => npc.tipo === "combatente");
  const vendedores = npcs.filter((npc) => npc.tipo === "vendedor");
  const categorias = [...new Map(vendedores.map((npc) => [npc.categoriaBusca, npc.categoria]).filter(([chave]) => chave)).values()].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const cargos = [...new Map(combatentes.map((npc) => [npc.cargoBusca, npc.cargo]).filter(([chave]) => chave)).values()].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const tipagens = [...new Map(combatentes.map((npc) => [npc.estadioBusca, npc.estadio]).filter(([chave]) => chave && chave !== "geral")).values()].sort((a, b) => a.localeCompare(b, "pt-BR"));
  return {
    quantidade: npcs.length,
    combatentes: combatentes.length,
    vendedores: vendedores.length,
    categorias,
    cargos,
    tipagens,
  };
}
const ORDEM_CARGO = {
  lider: 0,
  capitao: 1,
  desafiante: 2,
};
export function carregarEstadios(npcs) {
  const grupos = new Map();
  npcs.filter((npc) => npc.tipo === "combatente" && npc.estadio).forEach((npc) => {
    const chave = npc.estadioBusca;
    if (!grupos.has(chave)) {
      grupos.set(chave, {
        id: String(grupos.size + 1),
        ordem: grupos.size + 1,
        nomeTipo: npc.estadio,
        nome: `Estádio ${npc.estadio}`,
        estadioBusca: chave,
        membrosIds: [],
      });
    }
    grupos.get(chave).membrosIds.push(npc.id);
  });
  const npcsPorId = Object.fromEntries(npcs.map((npc) => [npc.id, npc]));
  return [...grupos.values()].map((estadio) => {
    const membros = estadio.membrosIds
      .map((id) => npcsPorId[id])
      .filter(Boolean)
      .sort((a, b) => {
        const cargoA = ORDEM_CARGO[a.cargoBusca] ?? 99;
        const cargoB = ORDEM_CARGO[b.cargoBusca] ?? 99;
        if (cargoA !== cargoB) return cargoA - cargoB;
        if ((b.nivel ?? 0) !== (a.nivel ?? 0)) return (b.nivel ?? 0) - (a.nivel ?? 0);
        return a.nome.localeCompare(b.nome, "pt-BR", { numeric: true });
      });
    return {
      ...estadio,
      membrosIds: membros.map((npc) => npc.id),
      membrosQuantidade: membros.length,
      busca: normalizarChave(`${estadio.nome} ${estadio.nomeTipo} ${membros.map((npc) => `${npc.nome} ${npc.cargo}`).join(" ")}`),
    };
  });
}
export function indexarIconesEstadios(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const chave = normalizarChave(arquivoSemExtensao(caminho));
    if (chave && !indice[chave]) indice[chave] = url;
  });
  return indice;
}
function candidatosEstadio(estadio) {
  return [
    estadio.nomeTipo,
    estadio.nome,
    estadio.nomeTipo?.replace(/\s+/g, "_"),
    estadio.nomeTipo?.replace(/\s+/g, "-"),
    estadio.estadioBusca,
    String(estadio.id),
    String(estadio.id).padStart(3, "0"),
  ].filter(Boolean).map(normalizarChave);
}
export function resolverIconeEstadio(estadio, iconesPorNome) {
  for (const candidato of candidatosEstadio(estadio)) {
    if (iconesPorNome[candidato]) return iconesPorNome[candidato];
  }
  return null;
}
export function criarAssetsEstadios(estadios, iconesPorNome) {
  return Object.fromEntries(estadios.map((estadio) => [estadio.id, { imagem: resolverIconeEstadio(estadio, iconesPorNome) }]));
}
export function resumoEstadios(estadios, npcs) {
  return {
    quantidade: estadios.length,
    tipos: estadios.length,
    associados: npcs.filter((npc) => npc.tipo === "combatente" && npc.estadio).length,
  };
}
