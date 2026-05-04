import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const EXTENSOES_IMAGEM = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"]);
const cacheListas = new Map();
const cacheIndices = new Map();

const PASTAS_POKEMON = ["pokemon", "pokemons", "pokedex", "pokédex", "sprites", "imagens"];
const PASTAS_RUIDO = ["animacao", "animação", "animacoes", "animações", "frames", "frame", "gif", "gifs", "ataquesgifs"];

function diretorioModulo() {
  try {
    return path.dirname(fileURLToPath(import.meta.url));
  } catch {
    return process.cwd();
  }
}

function subirAtePublic(inicio) {
  let atual = path.resolve(inicio || process.cwd());
  for (let i = 0; i < 10; i += 1) {
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

export function normalizarChavePublica(valor) {
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

function numeroIdentificador(valor) {
  const chave = normalizarChavePublica(valor);
  const match = chave.match(/^(?:pokemon|poke|pokedex|dex|item|ataque|efeito|icone|icon|medalhao|insignia|skin|npc)?0*(\d{1,5})$/);
  if (!match) return null;
  return String(Number(match[1]));
}

function chavesNumericasIdentificadoras(valor) {
  const numero = numeroIdentificador(valor);
  if (!numero) return [];
  return [
    numero,
    numero.padStart(2, "0"),
    numero.padStart(3, "0"),
    numero.padStart(4, "0"),
    `pokemon${numero}`,
    `pokemon${numero.padStart(3, "0")}`,
    `poke${numero}`,
    `poke${numero.padStart(3, "0")}`,
    `pokedex${numero}`,
    `dex${numero}`,
    `item${numero}`,
    `ataque${numero}`,
    `efeito${numero}`,
    `icone${numero}`,
    `icon${numero}`,
    `medalhao${numero}`,
    `insignia${numero}`,
    `skin${numero}`,
    `npc${numero}`,
  ];
}

function variantesNomeArquivo(nomeArquivo) {
  const semExt = String(nomeArquivo || "").replace(/\.[^.]+$/, "");
  const variantes = new Set([semExt]);
  variantes.add(semExt.replace(/^\d+px[-_\s]*/i, ""));
  variantes.add(semExt.replace(/[_\s-]*hd$/i, ""));
  variantes.add(semExt.replace(/^\d+px[-_\s]*/i, "").replace(/[_\s-]*hd$/i, ""));
  variantes.add(semExt.replace(/^icone[-_\s]*/i, ""));
  variantes.add(semExt.replace(/^icon[-_\s]*/i, ""));
  variantes.add(semExt.replace(/^pokemon[-_\s]*/i, ""));
  variantes.add(semExt.replace(/^poke[-_\s]*/i, ""));
  variantes.add(semExt.replace(/^item[-_\s]*/i, ""));
  return [...variantes].filter(Boolean);
}

function pontuarCandidato({ caminho, arquivo, nomeArquivo, pastaPai, pastaRaiz, chaveOrigem, prioridade = 0 }) {
  const chave = normalizarChavePublica(chaveOrigem);
  const nome = normalizarChavePublica(nomeArquivo);
  const pai = normalizarChavePublica(pastaPai);
  const raiz = normalizarChavePublica(pastaRaiz);
  const caminhoNormalizado = normalizarChavePublica(caminho);
  const partes = caminho.split("/").map(normalizarChavePublica).filter(Boolean);
  const extensao = path.extname(arquivo).toLowerCase();
  const numeroChave = numeroIdentificador(chave);
  const numeroNome = numeroIdentificador(nome);

  let score = Number(prioridade) || 0;
  if (!chave) return -Infinity;

  if (nome === chave) score += 1200;
  if (numeroChave && numeroNome && numeroChave === numeroNome) score += 1050;
  if (nome.endsWith(chave) || nome.startsWith(chave)) score += 420;
  if (pai === chave) score += 360;
  if (raiz === chave) score += 120;
  if (caminhoNormalizado.includes(chave)) score += 70;

  if (partes.some((parte) => PASTAS_POKEMON.includes(parte))) score += 90;
  if (partes.some((parte) => PASTAS_RUIDO.includes(parte))) score -= 650;
  if (extensao === ".webp") score += 25;
  if (extensao === ".png") score += 18;
  if (extensao === ".jpg" || extensao === ".jpeg") score += 10;
  if (extensao === ".gif") score -= 60;
  score -= Math.max(0, partes.length - 2) * 8;

  return score;
}

function registrar(indiceInterno, chave, entrada, prioridade = 0) {
  const normalizada = normalizarChavePublica(chave);
  if (!normalizada) return;
  const score = pontuarCandidato({ ...entrada, chaveOrigem: normalizada, prioridade });
  const atual = indiceInterno.get(normalizada);
  if (!atual || score > atual.score || (score === atual.score && compararCaminhos(entrada.caminho, atual.caminho) < 0)) {
    indiceInterno.set(normalizada, { ...entrada, score });
  }
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
  const listaPastas = (Array.isArray(pastas) ? pastas : [pastas]).map(caminhoRelativo).filter(Boolean);
  const chaveCache = `${RAIZ_PUBLIC}|indice|${listaPastas.join("|")}`;
  if (cacheIndices.has(chaveCache)) return cacheIndices.get(chaveCache);

  const indiceInterno = new Map();
  const listaOrdenada = [];

  Object.entries(listarImagensPublicas(listaPastas)).forEach(([caminho, url]) => {
    const partes = caminho.split("/").filter(Boolean);
    const arquivo = partes.at(-1) || caminho;
    const nomeArquivo = arquivo.replace(/\.[^.]+$/, "");
    const pastaPai = partes.at(-2) || "";
    const pastaRaiz = partes.at(0) || "";
    const caminhoSemExtensao = caminho.replace(/\.[^.]+$/, "");
    const partesSemPastaRaiz = partes.slice(1).join("/").replace(/\.[^.]+$/, "");
    const entrada = { caminho, url, arquivo, nome: nomeArquivo, nomeArquivo, pastaPai, pastaRaiz };

    listaOrdenada.push(entrada);

    variantesNomeArquivo(nomeArquivo).forEach((chave) => registrar(indiceInterno, chave, entrada, 0));
    [
      pastaPai,
      pastaRaiz,
      `${pastaPai} ${nomeArquivo}`,
      `${pastaRaiz} ${nomeArquivo}`,
      caminhoSemExtensao,
      partesSemPastaRaiz,
    ].forEach((chave) => registrar(indiceInterno, chave, entrada, -80));

    chavesNumericasIdentificadoras(nomeArquivo).forEach((chave) => registrar(indiceInterno, chave, entrada, 40));
    chavesNumericasIdentificadoras(pastaPai).forEach((chave) => registrar(indiceInterno, chave, entrada, -30));
  });

  const indice = {};
  for (const [chave, entrada] of indiceInterno.entries()) {
    indice[chave] = entrada.url;
  }

  Object.defineProperty(indice, "__listaOrdenada", {
    value: listaOrdenada.sort((a, b) => compararCaminhos(a.caminho, b.caminho)),
    enumerable: false,
  });

  Object.defineProperty(indice, "__entradasPorChave", {
    value: indiceInterno,
    enumerable: false,
  });

  cacheIndices.set(chaveCache, indice);
  return indice;
}
