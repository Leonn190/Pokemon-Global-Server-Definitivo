import { existsSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { urlPublica } from "./AssetsPublicos.js";
import { normalizarChave } from "./PokemonWikiDados.js";

const PASTA_MUSICAS = "Musicas";
const EXTENSOES_AUDIO = new Set([".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac", ".webm"]);

const ESTILOS_PRIORIDADE = ["mundo", "confrontos", "lideres", "tipos", "gerais"];
const ESTILOS_ROTULOS = {
  mundo: "Mundo",
  confrontos: "Confrontos",
  lideres: "Líderes",
  tipos: "Tipos",
  gerais: "Gerais",
};

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
      // ignora candidato quebrado
    }
  }

  return path.resolve(process.cwd(), "public");
}

function compararTexto(a, b) {
  return String(a || "").localeCompare(String(b || ""), "pt-BR", {
    numeric: true,
    sensitivity: "base",
  });
}

function listarAudiosRecursivo(diretorio, destino) {
  let entradas = [];
  try {
    entradas = readdirSync(diretorio, { withFileTypes: true });
  } catch {
    return destino;
  }

  entradas.sort((a, b) => compararTexto(a.name, b.name));

  for (const entrada of entradas) {
    const absoluto = path.join(diretorio, entrada.name);
    if (entrada.isDirectory()) {
      listarAudiosRecursivo(absoluto, destino);
      continue;
    }
    if (!entrada.isFile()) continue;
    const extensao = path.extname(entrada.name).toLowerCase();
    if (!EXTENSOES_AUDIO.has(extensao)) continue;
    destino.push(absoluto);
  }
  return destino;
}

function tituloPtBr(texto) {
  return String(texto || "")
    .toLocaleLowerCase("pt-BR")
    .replace(/(^|\s)(\p{L})/gu, (_, espaco, letra) => `${espaco}${letra.toLocaleUpperCase("pt-BR")}`);
}

function nomeBonitoArquivo(arquivo) {
  return tituloPtBr(String(arquivo || "")
    .replace(/\.[^.]+$/, "")
    .replace(/([\p{Ll}\d])([\p{Lu}])/gu, "$1 $2")
    .replace(/([\p{L}])([0-9])/gu, "$1 $2")
    .replace(/([0-9])([\p{L}])/gu, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^\d+\s*/, ""));
}

function contemSegmento(segmentos, chaves) {
  const lista = Array.isArray(chaves) ? chaves : [chaves];
  return segmentos.some((segmento) => lista.includes(normalizarChave(segmento)));
}

function estiloPorCaminho(segmentos) {
  const chaves = segmentos.map((segmento) => normalizarChave(segmento));
  const contemParte = (partes) => chaves.some((chave) => partes.some((parte) => chave.includes(parte)));
  if (contemParte(["outros", "fechamento", "fechamentos"])) return null;
  if (contemParte(["mundo", "bioma", "exploracao"])) return "mundo";
  if (contemParte(["lider", "lideres", "lideranca", "estadio", "estadios"])) return "lideres";
  if (contemParte(["tipo", "tipos"])) return "tipos";
  if (contemParte(["confronto", "confrontos", "batalha", "batalhas", "combate", "combates", "boss", "bosses"])) return "confrontos";
  return "gerais";
}

function detalheEstilo(estilo) {
  const detalhes = {
    mundo: "Músicas que tocam durante exploração, biomas, rotas e ambientes do mundo.",
    confrontos: "Músicas usadas em confrontos, batalhas comuns, bosses e momentos de tensão.",
    lideres: "Músicas reservadas para líderes, estádios e batalhas especiais de progressão.",
    tipos: "Músicas temáticas ligadas aos tipos do jogo.",
    gerais: "Músicas gerais de menu, transição, créditos e outras áreas fora das categorias principais.",
  };
  return detalhes[estilo] ?? detalhes.gerais;
}

export function carregarMusicas() {
  const raizPublic = resolverRaizPublic();
  const raizMusicas = path.resolve(raizPublic, PASTA_MUSICAS);
  if (!existsSync(raizMusicas)) {
    console.warn(`[Wiki Músicas] Pasta public/${PASTA_MUSICAS} não encontrada em ${raizMusicas}.`);
    return [];
  }

  return listarAudiosRecursivo(raizMusicas, [])
    .map((absoluto) => {
      const relativoPublic = path.relative(raizPublic, absoluto).split(path.sep).join("/");
      const relativoMusicas = path.relative(raizMusicas, absoluto).split(path.sep).join("/");
      const segmentos = relativoMusicas.split("/").filter(Boolean);
      const arquivo = segmentos.at(-1) || relativoMusicas;
      const estilo = estiloPorCaminho(segmentos.slice(0, -1));
      if (!estilo) return null;
      const nome = nomeBonitoArquivo(arquivo) || `Música ${relativoMusicas}`;
      return {
        id: normalizarChave(relativoMusicas) || String(relativoMusicas),
        ordem: 0,
        nome,
        arquivo,
        caminho: relativoMusicas,
        pasta: segmentos.slice(0, -1).join(" / ") || "Raiz",
        estilo,
        estiloRotulo: ESTILOS_ROTULOS[estilo] ?? "Gerais",
        estiloDetalhe: detalheEstilo(estilo),
        url: urlPublica(relativoPublic),
        extensao: path.extname(arquivo).replace(/^\./, "").toUpperCase(),
        busca: normalizarChave(`${nome} ${relativoMusicas} ${ESTILOS_ROTULOS[estilo] ?? estilo} ${arquivo}`),
        duracao: null,
      };
    })
    .filter(Boolean)
    .map((musica, indice) => ({ ...musica, ordem: indice + 1 }));
}

export function resumoMusicas(musicas) {
  const porEstilo = new Map();
  musicas.forEach((musica) => {
    if (!porEstilo.has(musica.estilo)) {
      porEstilo.set(musica.estilo, {
        chave: musica.estilo,
        rotulo: musica.estiloRotulo,
        descricao: musica.estiloDetalhe,
        quantidade: 0,
      });
    }
    porEstilo.get(musica.estilo).quantidade += 1;
  });
  const estilos = [...porEstilo.values()].sort((a, b) => {
    const pa = ESTILOS_PRIORIDADE.indexOf(a.chave);
    const pb = ESTILOS_PRIORIDADE.indexOf(b.chave);
    if (pa !== pb) return (pa === -1 ? 999 : pa) - (pb === -1 ? 999 : pb);
    return compararTexto(a.rotulo, b.rotulo);
  });
  return {
    quantidade: musicas.length,
    estilos,
  };
}
