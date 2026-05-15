import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizarChave } from "./PokemonWikiDados.js";

const ARQUIVO_COMANDOS = "Comandos.json";
const CONTEXTOS = {
  geral: "Geral",
  mundo: "Mundo",
  batalha: "Batalha",
};

function limparTexto(valor) {
  return String(valor ?? "").trim();
}

function numero(valor, fallback = 1) {
  const n = Number(String(valor ?? "").replace(",", "."));
  return Number.isFinite(n) ? n : fallback;
}

function diretorioAtual() {
  return path.dirname(fileURLToPath(import.meta.url));
}

function caminhosCatalogoComandos() {
  const atual = diretorioAtual();
  return [
    path.resolve(atual, "../../../Dados/Catalogos", ARQUIVO_COMANDOS),
    path.resolve(atual, "../../../Dados/Catalogo", ARQUIVO_COMANDOS),
    path.resolve(atual, "../../Dados/Catalogos", ARQUIVO_COMANDOS),
    path.resolve(atual, "../../Dados/Catalogo", ARQUIVO_COMANDOS),
    path.resolve(process.cwd(), "../Dados/Catalogos", ARQUIVO_COMANDOS),
    path.resolve(process.cwd(), "../Dados/Catalogo", ARQUIVO_COMANDOS),
    path.resolve(process.cwd(), "Dados/Catalogos", ARQUIVO_COMANDOS),
    path.resolve(process.cwd(), "Dados/Catalogo", ARQUIVO_COMANDOS),
    path.resolve(process.cwd(), "../Pokemon-Global-Server-Definitivo/Dados/Catalogos", ARQUIVO_COMANDOS),
  ];
}

function lerCatalogoComandos() {
  const caminhos = caminhosCatalogoComandos();
  const caminho = caminhos.find((item) => existsSync(item));
  if (!caminho) {
    console.warn(`[Wiki Comandos] Catalogo de comandos não encontrado. Procurei por: ${caminhos.join(" | ")}`);
    return { versao: 0, comandos: [] };
  }
  try {
    const dados = JSON.parse(readFileSync(caminho, "utf8").replace(/^\uFEFF/, ""));
    return dados && typeof dados === "object" ? dados : { versao: 0, comandos: [] };
  } catch (erro) {
    console.warn(`[Wiki Comandos] Falha ao ler ${caminho}: ${erro}`);
    return { versao: 0, comandos: [] };
  }
}

function listaTexto(valor) {
  if (Array.isArray(valor)) return valor.map(limparTexto).filter(Boolean);
  if (valor === null || valor === undefined || valor === "") return [];
  return [limparTexto(valor)].filter(Boolean);
}

function contextoCanonico(valor) {
  const chave = normalizarChave(valor || "geral");
  if (chave === "battle" || chave === "batalhas") return "batalha";
  if (chave === "world" || chave === "mundos") return "mundo";
  if (chave === "global" || chave === "gerais") return "geral";
  return CONTEXTOS[chave] ? chave : "geral";
}

function nivelTexto(nivel) {
  return Number(nivel) >= 2 ? "Avançado" : "Básico";
}

function normalizarComando(item, indice) {
  const nome = normalizarChave(limparTexto(item?.nome).replace(/^\//, "")) || `comando${indice + 1}`;
  const aliases = listaTexto(item?.aliases).map((alias) => limparTexto(alias).replace(/^\//, ""));
  const contexto = contextoCanonico(item?.contexto);
  const nivel = Math.max(1, Math.trunc(numero(item?.nivel, 1)));
  const uso = limparTexto(item?.uso) || `/${nome}`;
  const descricao = limparTexto(item?.descricao) || `Comando /${nome}.`;
  const argumentos = listaTexto(item?.argumentos);
  const exemplos = listaTexto(item?.exemplos);
  const localRotulo = CONTEXTOS[contexto] ?? "Geral";
  const nivelRotulo = nivelTexto(nivel);
  return {
    id: nome,
    ordem: indice + 1,
    nome,
    titulo: `/${nome}`,
    aliases,
    contexto,
    contextoRotulo: localRotulo,
    local: contexto,
    localRotulo,
    nivel,
    nivelRotulo,
    uso,
    descricao,
    argumentos,
    exemplos,
    busca: normalizarChave(`${nome} ${aliases.join(" ")} ${contexto} ${localRotulo} ${nivelRotulo} ${uso} ${descricao} ${argumentos.join(" ")} ${exemplos.join(" ")}`),
  };
}

export function carregarComandos() {
  const dados = lerCatalogoComandos();
  const lista = Array.isArray(dados?.comandos) ? dados.comandos : (Array.isArray(dados) ? dados : []);
  return lista.filter((item) => item && typeof item === "object").map(normalizarComando);
}

function unicosOrdenados(lista) {
  return [...new Set(lista.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), "pt-BR", { numeric: true }));
}

export function resumoComandos(comandos) {
  const locais = ["geral", "mundo", "batalha"]
    .filter((chave) => comandos.some((comando) => comando.local === chave))
    .map((chave) => ({ chave, rotulo: CONTEXTOS[chave] }));
  const niveis = unicosOrdenados(comandos.map((comando) => comando.nivel)).map((nivel) => ({
    chave: String(nivel),
    rotulo: nivelTexto(nivel),
  }));
  return {
    quantidade: comandos.length,
    locais,
    niveis,
    basicos: comandos.filter((comando) => comando.nivel <= 1).length,
    avancados: comandos.filter((comando) => comando.nivel >= 2).length,
  };
}
