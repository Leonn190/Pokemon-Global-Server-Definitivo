import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
export function limparTexto(valor) {
  return String(valor ?? "").trim();
}
export function numero(valor) {
  const texto = limparTexto(valor).replace("%", "").replace(",", ".");
  if (!texto || texto === "-" || texto.toLowerCase() === "nan") return null;
  const convertido = Number(texto);
  return Number.isFinite(convertido) ? convertido : null;
}
export function parseCsv(texto) {
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
export function caminhosPossiveisCsv(nomes) {
  const diretorioAtual = path.dirname(fileURLToPath(import.meta.url));
  const bases = [
    path.resolve(diretorioAtual, "../../../Dados/Tabelas"),
    path.resolve(diretorioAtual, "../../../Dados"),
    path.resolve(process.cwd(), "../Dados/Tabelas"),
    path.resolve(process.cwd(), "../Dados"),
    path.resolve(process.cwd(), "Dados/Tabelas"),
    path.resolve(process.cwd(), "Dados"),
  ];
  return bases.flatMap((base) => nomes.map((nome) => path.resolve(base, nome)));
}
export function carregarCsvWiki(nomes, etiqueta) {
  const caminhos = caminhosPossiveisCsv(nomes);
  const caminho = caminhos.find((item) => existsSync(item));
  if (!caminho) {
    console.warn(`[${etiqueta}] CSV não encontrado. Procurei por: ${caminhos.join(" | ")}`);
    return [];
  }
  const conteudo = readFileSync(caminho, "utf8").replace(/^\uFEFF/, "");
  return parseCsv(conteudo);
}
export function campo(linha, nomes, fallback = "") {
  const lista = Array.isArray(nomes) ? nomes : [nomes];
  for (const nome of lista) {
    if (Object.prototype.hasOwnProperty.call(linha, nome) && limparTexto(linha[nome]) !== "") return linha[nome];
  }
  return fallback;
}
export function campoNumero(linha, nomes, fallback = null) {
  const valor = numero(campo(linha, nomes));
  return valor === null ? fallback : valor;
}
