import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { carregarCsvWiki, limparTexto } from "./WikiCsv.js";
import { normalizarChave } from "./PokemonWikiDados.js";
const NOME_CSV = "Pokemon Global Server - Itens.csv";
const ARQUIVO_RECEITAS = "Receitas.json";
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
function numero(valor) {
  const texto = limparTexto(valor).replace(",", ".");
  if (!texto || texto === "-" || texto.toLowerCase() === "nan") return null;
  const convertido = Number(texto);
  return Number.isFinite(convertido) ? convertido : null;
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
function diretorioAtual() {
  return path.dirname(fileURLToPath(import.meta.url));
}
function caminhosReceitas() {
  const atual = diretorioAtual();
  return [
    path.resolve(atual, "../../../Dados/Catalogos", ARQUIVO_RECEITAS),
    path.resolve(atual, "../../../Dados/Catalogo", ARQUIVO_RECEITAS),
    path.resolve(atual, "../../Dados/Catalogos", ARQUIVO_RECEITAS),
    path.resolve(atual, "../../Dados/Catalogo", ARQUIVO_RECEITAS),
    path.resolve(process.cwd(), "../Dados/Catalogos", ARQUIVO_RECEITAS),
    path.resolve(process.cwd(), "../Dados/Catalogo", ARQUIVO_RECEITAS),
    path.resolve(process.cwd(), "Dados/Catalogos", ARQUIVO_RECEITAS),
    path.resolve(process.cwd(), "Dados/Catalogo", ARQUIVO_RECEITAS),
    path.resolve(process.cwd(), "../Pokemon-Global-Server-Definitivo/Dados/Catalogos", ARQUIVO_RECEITAS),
  ];
}
function lerCatalogoReceitas() {
  const caminhos = caminhosReceitas();
  const caminho = caminhos.find((item) => existsSync(item));
  if (!caminho) {
    console.warn(`[Wiki Itens] Catalogo de receitas não encontrado. Procurei por: ${caminhos.join(" | ")}`);
    return {};
  }
  try {
    const dados = JSON.parse(readFileSync(caminho, "utf8").replace(/^﻿/, ""));
    return dados && typeof dados === "object" ? dados : {};
  } catch (erro) {
    console.warn(`[Wiki Itens] Falha ao ler ${caminho}: ${erro}`);
    return {};
  }
}
function normalizarCelulaReceita(celula) {
  if (celula === null || celula === undefined || celula === "") return null;
  if (Array.isArray(celula)) {
    const nome = limparTexto(celula[0]);
    if (!nome) return null;
    const quantidade = Math.max(1, Math.trunc(numero(celula[1]) ?? 1));
    return { nome, quantidade, slug: normalizarChave(nome) };
  }
  const nome = limparTexto(celula);
  return nome ? { nome, quantidade: 1, slug: normalizarChave(nome) } : null;
}
function linhasReceita(valor) {
  const receita = Array.isArray(valor) ? valor : [];
  const linhas = receita.filter(Array.isArray).slice(0, 3).map((linha) => {
    const celulas = linha.slice(0, 3).map(normalizarCelulaReceita);
    while (celulas.length < 3) celulas.push(null);
    return celulas;
  });
  while (linhas.length < 3) linhas.push([null, null, null]);
  return linhas;
}
function quantidadeResultadoReceita(valor) {
  const receita = Array.isArray(valor) ? valor : [];
  const extra = receita.find((item) => !Array.isArray(item) && Number.isFinite(Number(item)));
  const quantidade = Number(extra);
  return Number.isFinite(quantidade) && quantidade > 0 ? Math.trunc(quantidade) : 1;
}
function anexarReceitas(itens) {
  const receitas = lerCatalogoReceitas();
  const itensPorNome = new Map(itens.map((item) => [normalizarChave(item.nome), item]));
  Object.entries(receitas).forEach(([nomeResultado, dados]) => {
    const item = itensPorNome.get(normalizarChave(nomeResultado));
    const receitaBruta = Array.isArray(dados?.receita) ? dados.receita : null;
    if (!item || !receitaBruta) return;
    const matriz = linhasReceita(receitaBruta).map((linha) => linha.map((celula) => {
      if (!celula) return null;
      const itemCelula = itensPorNome.get(celula.slug);
      return {
        ...celula,
        nome: itemCelula?.nome || celula.nome,
        itemId: itemCelula?.id || null,
      };
    }));
    item.receita = {
      id: String(dados?.id ?? item.id),
      resultado: item.nome,
      quantidadeResultado: quantidadeResultadoReceita(receitaBruta),
      matriz,
    };
  });
  return itens;
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
  const itens = carregarCsvWiki([NOME_CSV], "Wiki Itens").map((linha, indice) => normalizarItem(linha, indice));
  return anexarReceitas(itens);
}
function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}
const CATEGORIAS_PASTAS_ITENS = {
  equipaveis: "equipavel",
  equipavel: "equipavel",
  equipamentos: "equipavel",
  equipamento: "equipavel",
  pokebolas: "bola",
  pokebola: "bola",
  bolas: "bola",
  bola: "bola",
  pocoes: "pocao",
  pocao: "pocao",
  potions: "pocao",
  frutas: "fruta",
  fruta: "fruta",
  berries: "fruta",
  recursos: "recurso",
  recurso: "recurso",
  ferramentas: "ferramenta",
  ferramenta: "ferramenta",
};

function categoriaPorCaminhoItem(caminho) {
  const partes = caminho.split(/[\\/]/).filter(Boolean).map(normalizarChave);
  for (const parte of partes.slice(0, -1).reverse()) {
    if (CATEGORIAS_PASTAS_ITENS[parte]) return CATEGORIAS_PASTAS_ITENS[parte];
  }
  return "geral";
}

function registrarImagem(indice, chave, url) {
  const normalizada = normalizarChave(chave);
  if (normalizada && !indice[normalizada]) indice[normalizada] = url;
}

export function indexarImagensItens(glob) {
  const geral = {};
  const porCategoria = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const nome = arquivoSemExtensao(caminho);
    const chave = normalizarChave(nome);
    if (!chave) return;
    const categoria = categoriaPorCaminhoItem(caminho);
    if (!porCategoria[categoria]) porCategoria[categoria] = {};
    registrarImagem(porCategoria[categoria], chave, url);
    if (categoria === "geral") registrarImagem(geral, chave, url);
  });
  return { ...geral, geral, porCategoria };
}
function candidatosNomeItem(item) {
  return [
    item.nome,
    item.slug,
    item.nome?.replace(/\s+/g, "_"),
    item.nome?.replace(/\s+/g, "-"),
  ].filter(Boolean).map(normalizarChave);
}
function candidatosNumericosItem(item) {
  const codigo = String(item.code ?? item.id ?? "").trim();
  return [
    codigo,
    codigo.padStart(3, "0"),
    `item${codigo}`,
    `icone${codigo}`,
    item.estiloBusca === "equipavel" ? `equipavel${codigo}` : null,
    item.estiloBusca === "equipavel" ? `equipável${codigo}` : null,
  ].filter(Boolean).map(normalizarChave);
}
function candidatosItem(item) {
  return [...candidatosNomeItem(item), ...candidatosNumericosItem(item)];
}
export function resolverImagemItem(item, imagensPorNome) {
  const categoria = normalizarChave(item.estiloBusca || "");
  const porCategoria = imagensPorNome?.porCategoria || {};
  const categoriasPreferidas = [categoria];
  if (categoria === "equipavel") categoriasPreferidas.unshift("equipavel");

  // Primeiro procura dentro da pasta correspondente ao estilo do item.
  // Isso permite que a wiki de Itens use as imagens da pasta Equipáveis sem roubar imagem de outros estilos por ID igual.
  for (const cat of [...new Set(categoriasPreferidas.filter(Boolean))]) {
    const indiceCategoria = porCategoria[cat] || {};
    for (const candidato of candidatosItem(item)) {
      if (indiceCategoria[candidato]) return indiceCategoria[candidato];
    }
  }

  // Em pastas gerais, só o nome é confiável. O fallback por número causava trocas de imagem entre categorias.
  for (const candidato of candidatosNomeItem(item)) {
    if (imagensPorNome?.geral?.[candidato]) return imagensPorNome.geral[candidato];
    if (imagensPorNome?.[candidato]) return imagensPorNome[candidato];
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
