import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const EXTENSOES_IMAGEM = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"]);
const cacheListas = new Map();

function diretorioModulo() {
  try {
    return path.dirname(fileURLToPath(import.meta.url));
  } catch {
    return process.cwd();
  }
}

function subirAtePublic(inicio) {
  let atual = path.resolve(inicio || process.cwd());
  for (let i = 0; i < 8; i += 1) {
    const candidato = path.join(atual, "public");
    if (existsSync(candidato)) return candidato;
    const pai = path.dirname(atual);
    if (pai === atual) break;
    atual = pai;
  }
  return null;
}

function resolverRaizPublic() {
  const candidatos = [
    path.resolve(process.cwd(), "public"),
    path.resolve(process.cwd(), "Site/public"),
    subirAtePublic(diretorioModulo()),
    subirAtePublic(process.cwd()),
  ].filter(Boolean);

  for (const candidato of candidatos) {
    try {
      if (existsSync(candidato) && statSync(candidato).isDirectory()) return path.resolve(candidato);
    } catch {
      // ignora candidato inválido
    }
  }

  return path.resolve(process.cwd(), "public");
}

const RAIZ_PUBLIC = resolverRaizPublic();

function normalizarChave(valor) {
  return String(valor ?? "")
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function baseSite() {
  const base = import.meta.env?.BASE_URL || "/";
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
  const relativoSeguranca = path.relative(RAIZ_PUBLIC, absoluto);
  if (relativoSeguranca.startsWith("..") || path.isAbsolute(relativoSeguranca)) return null;
  return absoluto;
}

function codificarCaminho(caminho) {
  return caminhoRelativo(caminho)
    .split("/")
    .filter(Boolean)
    .map((parte) => encodeURIComponent(parte))
    .join("/");
}

function compararCaminhos(a, b) {
  return a.localeCompare(b, "pt-BR", {
    numeric: true,
    sensitivity: "base",
  });
}

function listarArquivosRecursivo(diretorio, destino) {
  let entradas = [];
  try {
    entradas = readdirSync(diretorio, { withFileTypes: true });
  } catch {
    return destino;
  }

  entradas.sort((a, b) => compararCaminhos(a.name, b.name));

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

function chavesNumericas(valor) {
  const texto = String(valor ?? "");
  const numeros = texto.match(/\d+/g) ?? [];
  const chaves = [];
  for (const numero of numeros) {
    const inteiro = Number(numero);
    if (!Number.isFinite(inteiro)) continue;
    chaves.push(String(inteiro));
    chaves.push(String(inteiro).padStart(2, "0"));
    chaves.push(String(inteiro).padStart(3, "0"));
    chaves.push(String(inteiro).padStart(4, "0"));
    chaves.push(`pokemon${inteiro}`);
    chaves.push(`pokemon${String(inteiro).padStart(3, "0")}`);
    chaves.push(`poke${inteiro}`);
    chaves.push(`poke${String(inteiro).padStart(3, "0")}`);
    chaves.push(`icone${inteiro}`);
    chaves.push(`icone${String(inteiro).padStart(3, "0")}`);
  }
  return chaves;
}

function adicionarChave(indice, chave, url) {
  const normalizada = normalizarChave(chave);
  if (normalizada && !indice[normalizada]) indice[normalizada] = url;
}

export function urlPublica(caminho) {
  const relativo = codificarCaminho(caminho);
  return relativo ? `${baseSite()}${relativo}` : baseSite();
}

export function listarImagensPublicas(pastas) {
  const listaPastas = (Array.isArray(pastas) ? pastas : [pastas]).map(caminhoRelativo).filter(Boolean);
  const chaveCache = `${RAIZ_PUBLIC}|${listaPastas.join("|")}`;
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

  const ordenado = Object.fromEntries(
    Object.entries(imagens).sort(([a], [b]) => compararCaminhos(a, b)),
  );

  cacheListas.set(chaveCache, ordenado);
  return ordenado;
}

export function indexarPublicoPorNome(pastas) {
  const indice = {};
  const listaOrdenada = [];

  Object.entries(listarImagensPublicas(pastas)).forEach(([caminho, url]) => {
    const partes = caminho.split("/").filter(Boolean);
    const arquivo = partes.at(-1) || caminho;
    const nomeArquivo = arquivo.replace(/\.[^.]+$/, "");
    const pastaPai = partes.at(-2) || "";
    const pastaRaiz = partes.at(0) || "";
    const caminhoSemExtensao = caminho.replace(/\.[^.]+$/, "");
    const partesSemPastaRaiz = partes.slice(1).join("/").replace(/\.[^.]+$/, "");

    listaOrdenada.push({ caminho, url, nome: nomeArquivo });

    [
      nomeArquivo,
      pastaPai,
      pastaRaiz,
      `${pastaPai} ${nomeArquivo}`,
      `${pastaRaiz} ${nomeArquivo}`,
      caminhoSemExtensao,
      partesSemPastaRaiz,
      nomeArquivo.replace(/^0+(\d+)$/, "$1"),
      ...chavesNumericas(nomeArquivo),
      ...chavesNumericas(pastaPai),
      ...chavesNumericas(caminhoSemExtensao),
    ].forEach((chave) => adicionarChave(indice, chave, url));
  });

  Object.defineProperty(indice, "__listaOrdenada", {
    value: listaOrdenada.sort((a, b) => compararCaminhos(a.caminho, b.caminho)),
    enumerable: false,
  });

  return indice;
}
