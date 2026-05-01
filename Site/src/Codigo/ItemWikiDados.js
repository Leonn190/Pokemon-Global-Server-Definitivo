import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizarChave } from "./PokemonWikiDados.js";

const NOME_CSV = "Pokemon Global Server - Itens.csv";

const RARIDADES = {
  1: { nome: "Comum", classe: "raridade-comum" },
  2: { nome: "Incomum", classe: "raridade-incomum" },
  3: { nome: "Raro", classe: "raridade-raro" },
  4: { nome: "Épico", classe: "raridade-epico" },
  5: { nome: "Lendário", classe: "raridade-lendario" },
  6: { nome: "Mítico", classe: "raridade-mitico" },
};

const VENDA = {
  SS: "Loja Especial",
  S: "Loja",
  N: "Sem vendas",
};

function limparTexto(valor) {
  return String(valor ?? "").trim();
}

function numero(valor) {
  const texto = limparTexto(valor).replace(",", ".");
  if (!texto || texto === "-" || texto.toLowerCase() === "nan") return null;
  const convertido = Number(texto);
  return Number.isFinite(convertido) ? convertido : null;
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

function normalizarVenda(valor) {
  const texto = limparTexto(valor).toUpperCase();
  if (texto === "SS") return "SS";
  if (texto === "S") return "S";
  return "N";
}

function normalizarBau(valor) {
  return limparTexto(valor).toLowerCase() === "s";
}

function rotuloEstilo(valor) {
  const texto = limparTexto(valor).toLowerCase();
  const nomes = {
    "poção": "Poções",
    pocao: "Poções",
    bola: "Pokébolas",
    fruta: "Frutas",
    recurso: "Recursos",
    ferramenta: "Ferramentas",
    equipavel: "Equipáveis",
    "equipável": "Equipáveis",
  };
  return nomes[texto] ?? (texto ? texto.replace(/^./, (letra) => letra.toUpperCase()) : "Sem estilo");
}

function normalizarItem(linha, indice) {
  const nome = limparTexto(linha.Nome) || `Item ${indice + 1}`;
  const code = numero(linha.Code) ?? indice + 1;
  const raridadeNumero = numero(linha.Raridade) ?? 1;
  const raridade = RARIDADES[raridadeNumero] ?? { nome: `Raridade ${raridadeNumero}`, classe: "raridade-comum" };
  const estilo = limparTexto(linha.Estilo) || "sem estilo";
  const vendaCodigo = normalizarVenda(linha.Venda);
  const bau = normalizarBau(linha.Bau);

  return {
    id: String(code),
    ordem: indice + 1,
    code,
    nome,
    slug: normalizarChave(nome),
    busca: normalizarChave(`${nome} ${code} ${estilo} ${raridade.nome} ${linha["Descrição Melhor"] ?? ""}`),
    descricaoMelhor: limparTexto(linha["Descrição Melhor"]) || "Descrição detalhada ainda não cadastrada.",
    fator: limparTexto(linha.Fator),
    raridadeNumero,
    raridadeNome: raridade.nome,
    raridadeClasse: raridade.classe,
    bau,
    bauTexto: bau ? "Sim" : "Não",
    valor: numero(linha.Valor),
    vendaCodigo,
    vendaTexto: VENDA[vendaCodigo] ?? "Sem vendas",
    stacks: numero(linha.Stacks),
    estilo,
    estiloRotulo: rotuloEstilo(estilo),
    estiloBusca: normalizarChave(estilo),
  };
}

export function carregarItens() {
  const caminho = caminhosPossiveisCsv().find((item) => existsSync(item));

  if (!caminho) {
    console.warn(`[Wiki Itens] CSV não encontrado. Procurei por: ${caminhosPossiveisCsv().join(" | ")}`);
    return [];
  }

  const conteudo = readFileSync(caminho, "utf8").replace(/^\uFEFF/, "");
  return parseCsv(conteudo).map((linha, indice) => normalizarItem(linha, indice));
}

function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}

export function indexarImagensItens(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const nome = arquivoSemExtensao(caminho);
    const chave = normalizarChave(nome);
    if (chave && !indice[chave]) indice[chave] = url;
  });
  return indice;
}

function candidatosItem(item) {
  const codigo = String(item.code ?? item.id ?? "");
  return [
    item.nome,
    item.slug,
    item.nome?.replace(/\s+/g, "_"),
    item.nome?.replace(/\s+/g, "-"),
    codigo,
    codigo.padStart(3, "0"),
    `item${codigo}`,
    `icone${codigo}`,
  ].filter(Boolean).map(normalizarChave);
}

export function resolverImagemItem(item, imagensPorNome) {
  for (const candidato of candidatosItem(item)) {
    if (imagensPorNome[candidato]) return imagensPorNome[candidato];
  }
  return null;
}

export function criarAssetsItens(itens, imagensPorNome) {
  return Object.fromEntries(itens.map((item) => [item.id, { imagem: resolverImagemItem(item, imagensPorNome) }]));
}

export function resumoItens(itens) {
  const estilos = [...new Map(itens.map((item) => [item.estiloBusca, item.estiloRotulo])).values()].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const raridades = [...new Map(itens.map((item) => [item.raridadeNumero, item.raridadeNome])).entries()]
    .sort((a, b) => Number(a[0]) - Number(b[0]))
    .map(([, nome]) => nome);
  return {
    quantidade: itens.length,
    equipaveis: itens.filter((item) => item.estiloBusca === "equipavel").length,
    estilos,
    raridades,
  };
}

export const OPCOES_VENDA = VENDA;
export const MAPA_RARIDADES = RARIDADES;
