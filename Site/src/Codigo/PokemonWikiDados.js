import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const NOME_CSV = "Pokemon Global Server - Pokemons.csv";
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

function limparTexto(valor) {
  return String(valor ?? "").trim();
}

function numero(valor) {
  const texto = limparTexto(valor).replace("%", "").replace(",", ".");
  if (!texto || texto === "-" || texto.toLowerCase() === "nan") return null;
  const convertido = Number(texto);
  return Number.isFinite(convertido) ? convertido : null;
}

export function normalizarChave(valor) {
  return limparTexto(valor)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function parseCsv(texto) {
  const linhas = [];
  let campo = "";
  let linha = [];
  let aspas = false;

  for (let i = 0; i < texto.length; i += 1) {
    const char = texto[i];
    const prox = texto[i + 1];

    if (char === '"') {
      if (aspas && prox === '"') {
        campo += '"';
        i += 1;
      } else {
        aspas = !aspas;
      }
      continue;
    }

    if (char === "," && !aspas) {
      linha.push(campo);
      campo = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !aspas) {
      if (char === "\r" && prox === "\n") i += 1;
      linha.push(campo);
      if (linha.some((item) => limparTexto(item) !== "")) linhas.push(linha);
      campo = "";
      linha = [];
      continue;
    }

    campo += char;
  }

  if (campo || linha.length) {
    linha.push(campo);
    if (linha.some((item) => limparTexto(item) !== "")) linhas.push(linha);
  }

  const cabecalho = linhas.shift()?.map(limparTexto) ?? [];
  return linhas.map((valores) => Object.fromEntries(cabecalho.map((campoAtual, i) => [campoAtual, valores[i] ?? ""])));
}

function caminhosPossiveisCsv() {
  const diretorioAtual = path.dirname(fileURLToPath(import.meta.url));
  return [
    path.resolve(diretorioAtual, "../../../Dados/Tabelas", NOME_CSV),
    path.resolve(diretorioAtual, "../../../Dados", NOME_CSV),
    path.resolve(process.cwd(), "../Dados/Tabelas", NOME_CSV),
    path.resolve(process.cwd(), "../Dados", NOME_CSV),
    path.resolve(process.cwd(), "Dados/Tabelas", NOME_CSV),
    path.resolve(process.cwd(), "Dados", NOME_CSV),
  ];
}

export function carregarPokemons() {
  const caminho = caminhosPossiveisCsv().find((item) => existsSync(item));

  if (!caminho) {
    console.warn(`[Wiki Pokémons] CSV não encontrado. Procurei por: ${caminhosPossiveisCsv().join(" | ")}`);
    return [];
  }

  const conteudo = readFileSync(caminho, "utf8").replace(/^\uFEFF/, "");
  return parseCsv(conteudo).map((linha, indice) => normalizarPokemon(linha, indice));
}

function normalizarPokemon(linha, indice) {
  const normalizado = { ...linha };
  CAMPOS_NUMERICOS.forEach((campo) => {
    normalizado[campo] = numero(linha[campo]);
  });

  const nome = limparTexto(linha.Nome) || `Pokémon ${indice + 1}`;
  const code = normalizado.Code ?? indice + 1;
  const tipos = [
    { nome: limparTexto(linha.Tipo1), chance: normalizado["%1"] },
    { nome: limparTexto(linha.Tipo2), chance: normalizado["%2"] },
    { nome: limparTexto(linha.Tipo3), chance: normalizado["%3"] },
  ].filter((tipo) => tipo.nome);

  const atributos = Object.fromEntries(ATRIBUTOS_BASE.map((atributo) => [atributo.chave, normalizado[atributo.chave] ?? 0]));

  return {
    id: String(code ?? indice + 1),
    ordem: indice + 1,
    nome,
    busca: normalizarChave(`${nome} ${linha.Grupo ?? ""} ${linha.Tipo1 ?? ""} ${linha.Tipo2 ?? ""} ${linha.Tipo3 ?? ""} ${code ?? ""}`),
    slug: normalizarChave(nome),
    atributos,
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
    raridadeTexto: limparTexto(linha.Raridade) || "-",
    estagio: limparTexto(linha.Estagio) || "-",
    formaFinal: limparTexto(linha.FF),
    code,
    linhagem: normalizado.Linhagem ?? code ?? indice + 1,
  };
}

function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}

export function indexarArquivosPorNome(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const chave = normalizarChave(arquivoSemExtensao(caminho));
    if (chave && !indice[chave]) indice[chave] = url;
  });
  return indice;
}

export function indexarFramesPorPasta(glob) {
  const grupos = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const partes = caminho.split(/[\\/]/).filter(Boolean);
    const pasta = partes.at(-2) ?? "";
    const chave = normalizarChave(pasta);
    if (!chave) return;
    if (!grupos[chave]) grupos[chave] = [];
    grupos[chave].push({ caminho, url });
  });

  Object.values(grupos).forEach((frames) => {
    frames.sort((a, b) => a.caminho.localeCompare(b.caminho, "pt-BR", { numeric: true, sensitivity: "base" }));
  });

  return Object.fromEntries(Object.entries(grupos).map(([chave, frames]) => [chave, frames.map((frame) => frame.url)]));
}

function candidatosPokemon(pokemon) {
  const codigo = String(pokemon.code ?? pokemon.id ?? "");
  return [
    codigo,
    codigo.padStart(3, "0"),
    `pokemon${codigo}`,
    `poke${codigo}`,
    pokemon.nome,
    pokemon.slug,
    pokemon.nome?.replace(/\s+/g, "_"),
    pokemon.nome?.replace(/\s+/g, "-"),
  ]
    .filter(Boolean)
    .map(normalizarChave);
}

export function resolverImagemPokemon(pokemon, imagensPorNome) {
  for (const candidato of candidatosPokemon(pokemon)) {
    if (imagensPorNome[candidato]) return imagensPorNome[candidato];
  }
  return null;
}

export function resolverFramesPokemon(pokemon, framesPorPasta) {
  for (const candidato of candidatosPokemon(pokemon)) {
    if (framesPorPasta[candidato]?.length) return framesPorPasta[candidato];
  }
  return [];
}

export function criarAssetsPokemons(pokemons, imagensPorNome, framesPorPasta = {}) {
  return Object.fromEntries(
    pokemons.map((pokemon) => [
      pokemon.id,
      {
        imagem: resolverImagemPokemon(pokemon, imagensPorNome),
        frames: resolverFramesPokemon(pokemon, framesPorPasta),
      },
    ]),
  );
}

export function resumoPokemons(pokemons) {
  const tipos = [...new Set(pokemons.flatMap((pokemon) => pokemon.tipos.map((tipo) => tipo.nome)))].sort((a, b) =>
    a.localeCompare(b, "pt-BR"),
  );
  const grupos = [...new Set(pokemons.map((pokemon) => pokemon.grupo).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "pt-BR"),
  );
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
    raridades,
    maximos,
    maiorTotal: Math.max(1, ...pokemons.map((pokemon) => pokemon.total ?? 0)),
    maiorPoderR3: Math.max(1, ...pokemons.map((pokemon) => pokemon.poderR3 ?? 0)),
  };
}

export function selecionarDestaquesHome(pokemons, limite = 8) {
  const nomesPreferidos = [
    "Bulbasaur",
    "Charizard",
    "Pikachu",
    "Mewtwo",
    "Lucario",
    "Greninja",
    "Gengar",
    "Dragonite",
    "Arceus",
    "Rayquaza",
  ];

  const porNome = new Map(pokemons.map((pokemon) => [normalizarChave(pokemon.nome), pokemon]));
  const escolhidos = nomesPreferidos.map((nome) => porNome.get(normalizarChave(nome))).filter(Boolean);

  if (escolhidos.length >= limite) return escolhidos.slice(0, limite);

  const usados = new Set(escolhidos.map((pokemon) => pokemon.id));
  const fortes = [...pokemons]
    .filter((pokemon) => !usados.has(pokemon.id))
    .sort((a, b) => (b.total ?? 0) - (a.total ?? 0))
    .slice(0, limite - escolhidos.length);

  return [...escolhidos, ...fortes];
}
