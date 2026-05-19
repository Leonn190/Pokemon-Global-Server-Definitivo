import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { carregarCsvWiki, limparTexto, numero } from "./WikiCsv.js";
const NOME_CSV = "Pokemon Global Server - Pokemons.csv";
const ARQUIVO_MOVELIST = "MoveList.json";
const CAMPOS_NUMERICOS = [
  "Vida",
  "Atk",
  "Def",
  "SpA",
  "SpD",
  "Vel",
  "Mag",
  "Per",
  "Ene",
  "Int",
  "CrD",
  "CrC",
  "Sinergia",
  "Habilidades",
  "Equipaveis",
  "Total",
  "Poder R1",
  "Poder R2",
  "Poder R3",
  "%1",
  "%2",
  "%3",
  "Altura",
  "Peso",
  "Tamanho",
  "Raridade",
  "Code",
  "Linhagem",
];
export const ATRIBUTOS_BASE = [
  { chave: "Vida", rotulo: "Vida" },
  { chave: "Atk", rotulo: "Atk" },
  { chave: "Def", rotulo: "Def" },
  { chave: "SpA", rotulo: "SpA" },
  { chave: "SpD", rotulo: "SpD" },
  { chave: "Vel", rotulo: "Vel" },
  { chave: "Mag", rotulo: "Mag" },
  { chave: "Per", rotulo: "Per" },
  { chave: "Ene", rotulo: "Ene" },
  { chave: "Int", rotulo: "Int" },
  { chave: "CrD", rotulo: "CrD" },
  { chave: "CrC", rotulo: "CrC" },
];
export const ATRIBUTOS_REGULARES = ["Vida", "Atk", "Def", "SpA", "SpD", "Vel", "Mag", "Per", "Ene", "Int"];
const TIPOS_CANONICOS = {
  agua: "Água",
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
  metal: "Metal",
  normal: "Normal",
  pedra: "Pedra",
  psiquico: "Psíquico",
  sombrio: "Sombrio",
  sombro: "Sombrio",
  sonoro: "Sonoro",
  terrestre: "Terrestre",
  venenoso: "Venenoso",
  voador: "Voador",
};
function calcularFocoAtributo(atributos) {
  return ATRIBUTOS_REGULARES.reduce((melhor, atributo) => {
    const valor = (atributos[atributo] ?? 0) / (atributo === "Vida" ? 2 : 1);
    if (!melhor || valor > melhor.valor) return { atributo, valor };
    return melhor;
  }, null)?.atributo ?? "";
}
export function normalizarChave(valor) {
  return limparTexto(valor)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}
function tipoCanonico(valor) {
  const chave = normalizarChave(valor);
  return TIPOS_CANONICOS[chave] ?? limparTexto(valor).replace(/^./, (letra) => letra.toUpperCase());
}
function converterRaridadePokemon(valor) {
  const texto = limparTexto(valor);
  const chave = normalizarChave(texto);
  const conversoes = {
    ff: "Forma Final",
    f: "Forma",
    l: "Lendario",
    m: "Mitico",
  };
  return conversoes[chave] ?? texto ?? "-";
}
function nomeBaseRadiante(nome) {
  return String(nome ?? "")
    .replace(/\bradiante\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}
function nomeBaseForma(nome) {
  return String(nome ?? "")
    .replace(/\b(radiante|mega|ultra|gigantamax|gmax)\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}
function variantesTextoPokemon(nome) {
  const texto = String(nome ?? "").trim();
  if (!texto) return [];
  return [
    texto,
    texto.replace(/\s+/g, "_"),
    texto.replace(/\s+/g, "-"),
    texto.replace(/\s+/g, ""),
  ];
}
export function carregarPokemons() {
  return anexarMoveList(carregarCsvWiki([NOME_CSV], "Wiki Pokémons").map((linha, indice) => normalizarPokemon(linha, indice)));
}

function caminhosMoveList() {
  const atual = path.dirname(fileURLToPath(import.meta.url));
  return [
    path.resolve(atual, "../../../Dados/Catalogos", ARQUIVO_MOVELIST),
    path.resolve(atual, "../../../Dados/Catalogo", ARQUIVO_MOVELIST),
    path.resolve(process.cwd(), "../Dados/Catalogos", ARQUIVO_MOVELIST),
    path.resolve(process.cwd(), "../Dados/Catalogo", ARQUIVO_MOVELIST),
    path.resolve(process.cwd(), "Dados/Catalogos", ARQUIVO_MOVELIST),
    path.resolve(process.cwd(), "Dados/Catalogo", ARQUIVO_MOVELIST),
  ];
}

function lerMoveList() {
  const caminho = caminhosMoveList().find((item) => existsSync(item));
  if (!caminho) return {};
  try {
    const dados = JSON.parse(readFileSync(caminho, "utf8").replace(/^\uFEFF/, ""));
    return dados && typeof dados === "object" ? dados : {};
  } catch (erro) {
    console.warn(`[Wiki Pokémons] Falha ao ler ${caminho}: ${erro}`);
    return {};
  }
}

function entradasMoveList(entradas) {
  if (!entradas || typeof entradas !== "object" || Array.isArray(entradas)) return [];
  return Object.entries(entradas)
    .map(([nome, intensidade]) => ({ nome: limparTexto(nome), intensidade: numero(intensidade) ?? null }))
    .filter((entrada) => entrada.nome);
}

function normalizarMoveList(entrada) {
  if (!entrada || typeof entrada !== "object") return null;
  const regulares = entradasMoveList(entrada.regulares);
  const artificiais = entradasMoveList(entrada.artificiais);
  return regulares.length || artificiais.length ? { regulares, artificiais } : null;
}

function ehFormaPokemon(pokemon) {
  const nome = normalizarChave(pokemon?.nome);
  const raridade = normalizarChave(pokemon?.raridadeTexto);
  const estagio = normalizarChave(pokemon?.estagio);
  return (
    raridade === "forma" ||
    raridade === "formafinal" ||
    estagio === "f" ||
    estagio === "ff" ||
    nome.includes("radiante") ||
    nome.startsWith("mega") ||
    nome.startsWith("ultra") ||
    nome.startsWith("gigantamax") ||
    nome.startsWith("gmax")
  );
}

function anexarMoveList(pokemons) {
  const indice = new Map(Object.entries(lerMoveList()).map(([nome, entrada]) => [normalizarChave(nome), normalizarMoveList(entrada)]));
  const regularesPorLinhagem = new Map();
  pokemons.forEach((pokemon) => {
    if (!ehFormaPokemon(pokemon)) regularesPorLinhagem.set(String(pokemon.linhagem), pokemon);
  });
  return pokemons.map((pokemon) => {
    const movelist =
      indice.get(normalizarChave(pokemon.nome)) ||
      indice.get(normalizarChave(nomeBaseForma(pokemon.nome))) ||
      (ehFormaPokemon(pokemon) ? indice.get(normalizarChave(regularesPorLinhagem.get(String(pokemon.linhagem))?.nome)) : null);
    return movelist ? { ...pokemon, movelist } : pokemon;
  });
}
function normalizarPokemon(linha, indice) {
  const normalizado = { ...linha };
  CAMPOS_NUMERICOS.forEach((campo) => {
    normalizado[campo] = numero(linha[campo]);
  });
  const nome = limparTexto(linha.Nome) || `Pokémon ${indice + 1}`;
  const nomeExibicao = nomeBaseRadiante(nome) || nome;
  const code = normalizado.Code ?? indice + 1;
  const tiposUnicos = new Map();
  [
    { nome: limparTexto(linha.Tipo1), chance: normalizado["%1"] },
    { nome: limparTexto(linha.Tipo2), chance: normalizado["%2"] },
    { nome: limparTexto(linha.Tipo3), chance: normalizado["%3"] },
  ].forEach((tipo) => {
    if (!tipo.nome) return;
    const nomeTipo = tipoCanonico(tipo.nome);
    const chave = normalizarChave(nomeTipo);
    if (!tiposUnicos.has(chave)) tiposUnicos.set(chave, { nome: nomeTipo, chance: tipo.chance });
  });
  const tipos = [...tiposUnicos.values()];
  const atributos = Object.fromEntries(ATRIBUTOS_BASE.map((atributo) => [atributo.chave, normalizado[atributo.chave] ?? 0]));
  const focoAtributo = calcularFocoAtributo(atributos);
  return {
    id: String(code ?? indice + 1),
    ordem: indice + 1,
    nome,
    nomeExibicao,
    busca: normalizarChave(`${nome} ${nomeExibicao} ${linha.Grupo ?? ""} ${linha.Tipo1 ?? ""} ${linha.Tipo2 ?? ""} ${linha.Tipo3 ?? ""} ${code ?? ""}`),
    slug: normalizarChave(nome),
    slugBase: normalizarChave(nomeExibicao),
    atributos,
    focoAtributo,
    focoBusca: normalizarChave(focoAtributo),
    vida: atributos.Vida,
    atk: atributos.Atk,
    def: atributos.Def,
    spa: atributos.SpA,
    spd: atributos.SpD,
    vel: atributos.Vel,
    mag: atributos.Mag,
    per: atributos.Per,
    ene: atributos.Ene,
    int: atributos.Int,
    crd: atributos.CrD,
    crc: atributos.CrC,
    sinergia: normalizado.Sinergia,
    habilidades: normalizado.Habilidades,
    equipaveis: normalizado.Equipaveis,
    total: normalizado.Total ?? 0,
    poderR1: normalizado["Poder R1"] ?? 0,
    poderR2: normalizado["Poder R2"] ?? 0,
    poderR3: normalizado["Poder R3"] ?? 0,
    tipos,
    tipoPrincipal: tipos[0]?.nome ?? "sem tipo",
    altura: normalizado.Altura,
    peso: normalizado.Peso,
    tamanho: normalizado.Tamanho,
    grupo: limparTexto(linha.Grupo) || "sem grupo",
    raridade: normalizado.Raridade,
    raridadeTexto: converterRaridadePokemon(linha.Raridade) || "-",
    estagio: limparTexto(linha.Estagio) || "-",
    formaFinal: limparTexto(linha.FF),
    code,
    linhagem: normalizado.Linhagem ?? code ?? indice + 1,
  };
}
function candidatosPokemon(pokemon) {
  const codigo = String(pokemon.code ?? pokemon.id ?? "").trim();
  const codigo3 = codigo.padStart(3, "0");
  const codigo4 = codigo.padStart(4, "0");
  const nome = pokemon.nome ?? "";
  const nomeExibicao = pokemon.nomeExibicao ?? nome;
  const baseRadiante = nomeBaseRadiante(nome);
  const baseForma = nomeBaseForma(nomeExibicao);
  return [
    ...variantesTextoPokemon(nome),
    ...variantesTextoPokemon(nomeExibicao),
    pokemon.slug,
    pokemon.slugBase,
    codigo,
    codigo3,
    codigo4,
    `pokemon${codigo}`,
    `pokemon${codigo3}`,
    `pokemon_${codigo}`,
    `pokemon_${codigo3}`,
    `pokemon-${codigo}`,
    `pokemon-${codigo3}`,
    `poke${codigo}`,
    `poke${codigo3}`,
    `pokedex${codigo}`,
    `pokedex${codigo3}`,
    `dex${codigo}`,
    `dex${codigo3}`,
    ...variantesTextoPokemon(baseRadiante),
    ...variantesTextoPokemon(baseForma),
  ]
    .filter(Boolean)
    .map(normalizarChave);
}
export function resolverImagemPokemon(pokemon, imagensPorNome) {
  for (const candidato of candidatosPokemon(pokemon)) {
    if (imagensPorNome[candidato]) return imagensPorNome[candidato];
  }

  // Não usa fallback pela ordem dos arquivos: a pasta Imagens pode misturar imagens de várias origens.
  // Fallback por ordem foi o que fez Bulbasaur receber sprite errado quando a lista não batia com o CSV.
  return null;
}
export function criarAssetsPokemons(pokemons, imagensPorNome) {
  return Object.fromEntries(
    pokemons.map((pokemon) => [pokemon.id, { imagem: resolverImagemPokemon(pokemon, imagensPorNome) }]),
  );
}
export function resumoPokemons(pokemons) {
  const tiposPorChave = new Map();
  pokemons.flatMap((pokemon) => pokemon.tipos.map((tipo) => tipo.nome)).forEach((tipo) => {
    const chave = normalizarChave(tipo);
    if (chave && !tiposPorChave.has(chave)) tiposPorChave.set(chave, tipoCanonico(tipo));
  });
  const tipos = [...tiposPorChave.values()].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const grupos = [...new Set(pokemons.map((pokemon) => pokemon.grupo).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "pt-BR"),
  );
  const focos = [...new Set(pokemons.map((pokemon) => pokemon.focoAtributo).filter(Boolean))];
  const linhagens = new Set(pokemons.map((pokemon) => String(pokemon.linhagem)).filter(Boolean));
  const raridades = [...new Set(pokemons.map((pokemon) => pokemon.raridadeTexto).filter(Boolean))].sort((a, b) => {
    const na = Number(a);
    const nb = Number(b);
    if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
    return a.localeCompare(b, "pt-BR", { numeric: true });
  });
  const maximos = Object.fromEntries(
    ATRIBUTOS_BASE.map((atributo) => [atributo.chave, Math.max(1, ...pokemons.map((pokemon) => pokemon.atributos[atributo.chave] ?? 0))]),
  );
  return {
    quantidade: pokemons.length,
    tipos,
    grupos,
    focos,
    linhagens: linhagens.size,
    raridades,
    maximos,
    maiorTotal: Math.max(1, ...pokemons.map((pokemon) => pokemon.total ?? 0)),
    maiorPoderR3: Math.max(1, ...pokemons.map((pokemon) => pokemon.poderR3 ?? 0)),
  };
}
export function selecionarDestaquesHome(pokemons, limite = 36, imagensPorNome = null) {
  const validos = [...pokemons].filter((pokemon) => pokemon?.id && pokemon?.nome && (!imagensPorNome || resolverImagemPokemon(pokemon, imagensPorNome)));
  for (let i = validos.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [validos[i], validos[j]] = [validos[j], validos[i]];
  }
  return validos.slice(0, Math.min(limite, validos.length));
}
