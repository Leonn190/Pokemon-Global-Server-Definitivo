import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RAIZ_PUBLIC = path.resolve(__dirname, "../../public");
const EXTENSOES_IMAGEM = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"]);
const cacheListas = new Map();


function normalizarChave(valor) {
  return String(valor ?? "")
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function baseSite() {
  const base = import.meta.env.BASE_URL || "/";
  return base.endsWith("/") ? base : `${base}/`;
}

function caminhoRelativo(caminho) {
  return String(caminho || "")
    .replace(/^[\\/]+/g, "")
    .replace(/\\/g, "/");
}

function caminhoPublicSeguro(caminho) {
  const relativo = caminhoRelativo(caminho);
  const absoluto = path.resolve(RAIZ_PUBLIC, relativo);
  if (!absoluto.startsWith(RAIZ_PUBLIC)) return null;
  return absoluto;
}

function codificarCaminho(caminho) {
  return caminhoRelativo(caminho)
    .split("/")
    .filter(Boolean)
    .map((parte) => encodeURIComponent(parte))
    .join("/");
}

function listarArquivosRecursivo(diretorio, destino) {
  let entradas = [];
  try {
    entradas = readdirSync(diretorio, { withFileTypes: true });
  } catch {
    return destino;
  }

  for (const entrada of entradas) {
    const absoluto = path.join(diretorio, entrada.name);
    if (entrada.isDirectory()) {
      listarArquivosRecursivo(absoluto, destino);
      continue;
    }
    if (!entrada.isFile()) continue;
    const extensao = path.extname(entrada.name).toLowerCase();
    if (!EXTENSOES_IMAGEM.has(extensao)) continue;
    const relativo = path.relative(RAIZ_PUBLIC, absoluto).split(path.sep).join("/");
    destino.push(relativo);
  }
  return destino;
}

export function urlPublica(caminho) {
  const relativo = codificarCaminho(caminho);
  return relativo ? `${baseSite()}${relativo}` : baseSite();
}

export function listarImagensPublicas(pastas) {
  const listaPastas = (Array.isArray(pastas) ? pastas : [pastas]).map(caminhoRelativo).filter(Boolean);
  const chaveCache = listaPastas.join("|");
  if (cacheListas.has(chaveCache)) return cacheListas.get(chaveCache);

  const imagens = {};
  for (const pasta of listaPastas) {
    const absoluto = caminhoPublicSeguro(pasta);
    if (!absoluto || !existsSync(absoluto)) continue;
    let stats = null;
    try {
      stats = statSync(absoluto);
    } catch {
      continue;
    }
    if (!stats?.isDirectory()) continue;
    for (const relativo of listarArquivosRecursivo(absoluto, [])) {
      imagens[relativo] = urlPublica(relativo);
    }
  }

  cacheListas.set(chaveCache, imagens);
  return imagens;
}

export function indexarPublicoPorNome(pastas) {
  const indice = {};
  Object.entries(listarImagensPublicas(pastas)).forEach(([caminho, url]) => {
    const arquivo = caminho.split("/").pop() || caminho;
    const nome = arquivo.replace(/\.[^.]+$/, "");
    const chaveNome = normalizarChave(nome);
    if (chaveNome && !indice[chaveNome]) indice[chaveNome] = url;
  });
  return indice;
}
