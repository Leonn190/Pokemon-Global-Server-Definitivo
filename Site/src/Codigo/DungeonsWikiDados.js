import { campo, campoNumero, carregarCsvWiki, limparTexto } from "./WikiCsv.js";
import { normalizarChave } from "./PokemonWikiDados.js";
const NOMES_CSV = ["Pokemon Global Server - Dungeons.csv", "Pokemon Global Server - Dungeon.csv", "Pokemon Global Server - Dungeos.csv"];
export const TAMANHOS_DUNGEON = {
  1: "Mini",
  2: "Pequena",
  3: "Média",
  4: "Grande",
  5: "Gigante",
  6: "Colossal",
};
export const DIFICULDADES_DUNGEON = {
  1: "Muito fácil",
  2: "Fácil",
  3: "Média",
  4: "Alta",
  5: "Muito alta",
  6: "Descomunal",
};
const BIOMAS_CANONICOS = {
  agua: "Água",
  aguafunda: "Água funda",
  aguarasa: "Água rasa",
  campo: "Campo",
  deserto: "Deserto",
  floresta: "Floresta",
  magico: "Mágico",
  neve: "Neve",
  pantano: "Pântano",
  praia: "Praia",
  vulcanico: "Vulcânico",
  vulcao: "Vulcânico",
};
function biomaCanonico(valor) {
  const texto = limparTexto(valor);
  const chave = normalizarChave(texto);
  return BIOMAS_CANONICOS[chave] ?? (texto ? texto.replace(/^./, (letra) => letra.toUpperCase()) : "");
}
function separarLista(valor) {
  return limparTexto(valor)
    .split(/[/;,|]+/g)
    .map((item) => limparTexto(item))
    .filter(Boolean);
}
function unicos(lista) {
  const mapa = new Map();
  lista.forEach((item) => {
    const chave = normalizarChave(item);
    if (chave && !mapa.has(chave)) mapa.set(chave, item);
  });
  return [...mapa.values()];
}
function coletarCamposNumerados(linha, prefixos) {
  const encontrados = [];
  Object.entries(linha).forEach(([chave, valor]) => {
    const normalizada = normalizarChave(chave);
    const numerado = prefixos.some((prefixo) => new RegExp(`^${prefixo}\\d+$`).test(normalizada));
    if (numerado) encontrados.push(...separarLista(valor));
  });
  return encontrados;
}
function coletarPokemons(linha) {
  return unicos([
    ...coletarCamposNumerados(linha, ["pokemon"]),
    ...separarLista(campo(linha, ["Pokemons", "Pokémons", "Pokemon", "Pokémon"], "")),
  ]);
}
function coletarServos(linha) {
  return unicos([
    ...separarLista(campo(linha, ["Servos", "Pokemons Servos", "Pokémons Servos", "Servos Pokemon", "Servos Pokémon"], "")),
  ]);
}
function coletarBiomas(linha) {
  const brutos = [
    ...coletarCamposNumerados(linha, ["bioma"]),
    ...separarLista(campo(linha, ["Biomas", "Bioma"], "")),
  ];
  return unicos(brutos.map(biomaCanonico).filter(Boolean));
}
function rotuloNumerico(mapa, valor, fallback) {
  if (valor === null || valor === undefined || valor === "") return fallback;
  return mapa[Number(valor)] ?? String(valor);
}
function normalizarDungeon(linha, indice) {
  const nome = limparTexto(campo(linha, ["Nome", "Dungeon", "Dungeons"])) || `Dungeon ${indice + 1}`;
  const code = campoNumero(linha, ["Code", "Código", "ID", "Id"], indice + 1) ?? indice + 1;
  const tamanho = campoNumero(linha, ["Tamanho"], null);
  const dificuldade = campoNumero(linha, ["Dificuldade"], null);
  const entradas = campoNumero(linha, ["Entradas", "Entrada", "Portais"], null);
  const biomas = coletarBiomas(linha);
  const pokemons = coletarPokemons(linha);
  const servos = coletarServos(linha);
  const tamanhoRotulo = rotuloNumerico(TAMANHOS_DUNGEON, tamanho, "Não definido");
  const dificuldadeRotulo = rotuloNumerico(DIFICULDADES_DUNGEON, dificuldade, "Não definida");
  return {
    id: String(code),
    ordem: indice + 1,
    code,
    nome,
    slug: normalizarChave(nome),
    busca: normalizarChave(`${nome} ${code} ${tamanhoRotulo} ${dificuldadeRotulo} ${biomas.join(" ")} ${pokemons.join(" ")} ${servos.join(" ")}`),
    tamanho,
    tamanhoRotulo,
    dificuldade,
    dificuldadeRotulo,
    entradas,
    biomas,
    biomasBusca: biomas.map(normalizarChave),
    pokemons,
    servos,
  };
}
export function carregarDungeons() {
  return carregarCsvWiki(NOMES_CSV, "Wiki Dungeons").map((linha, indice) => normalizarDungeon(linha, indice));
}
function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}
export function indexarIconesDungeons(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const chave = normalizarChave(arquivoSemExtensao(caminho));
    if (chave && !indice[chave]) indice[chave] = url;
  });
  return indice;
}
function candidatosDungeon(dungeon) {
  const codigo = String(dungeon.code ?? dungeon.id ?? "");
  return [
    dungeon.nome,
    dungeon.slug,
    dungeon.nome?.replace(/\s+/g, "_"),
    dungeon.nome?.replace(/\s+/g, "-"),
    codigo,
    codigo.padStart(3, "0"),
    `dungeon${codigo}`,
    `medalhao${codigo}`,
    `medalhão${codigo}`,
    `icone${codigo}`,
  ].filter(Boolean).map(normalizarChave);
}
export function resolverIconeDungeon(dungeon, iconesPorNome) {
  for (const candidato of candidatosDungeon(dungeon)) {
    if (iconesPorNome[candidato]) return iconesPorNome[candidato];
  }
  return null;
}
export function criarAssetsDungeons(dungeons, iconesPorNome) {
  return Object.fromEntries(dungeons.map((dungeon) => [dungeon.id, { imagem: resolverIconeDungeon(dungeon, iconesPorNome) }]));
}
export function resumoDungeons(dungeons) {
  const biomas = [...new Set(dungeons.flatMap((dungeon) => dungeon.biomas))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  return {
    quantidade: dungeons.length,
    dificuldades: Object.keys(DIFICULDADES_DUNGEON).length,
    tamanhos: Object.keys(TAMANHOS_DUNGEON).length,
    biomas,
  };
}
