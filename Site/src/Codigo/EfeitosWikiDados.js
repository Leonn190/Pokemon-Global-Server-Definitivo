import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizarChave } from "./PokemonWikiDados.js";

const NOME_CSV = "Pokemon Global Server - Efeitos.csv";

const ESTILOS_EFEITO = {
  pokemon: "Pokémon",
  clima: "Clima",
  terreno: "Terreno",
};

const SENTIDOS = {
  p: "Positivo",
  n: "Negativo",
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
  const bases = [
    path.resolve(diretorioAtual, "../../../Dados/Tabelas"),
    path.resolve(diretorioAtual, "../../../Dados"),
    path.resolve(process.cwd(), "../Dados/Tabelas"),
    path.resolve(process.cwd(), "../Dados"),
    path.resolve(process.cwd(), "Dados/Tabelas"),
    path.resolve(process.cwd(), "Dados"),
  ];
  return bases.map((base) => path.resolve(base, NOME_CSV));
}

function inferirEstilo(code) {
  if (code >= 35 && code <= 43) return "clima";
  if (code >= 44) return "terreno";
  return "pokemon";
}

function normalizarSentido(valor) {
  const chave = limparTexto(valor).toLowerCase();
  if (chave === "p" || chave === "positivo") return "p";
  if (chave === "n" || chave === "negativo") return "n";
  return "";
}

function normalizarEfeito(linha, indice) {
  const nome = limparTexto(linha.Efeito) || `Efeito ${indice + 1}`;
  const code = numero(linha.Code) ?? indice + 1;
  const estiloBusca = inferirEstilo(code);
  const sentidoBusca = normalizarSentido(linha.Sentido);
  const passosBase = numero(linha["Passos Base"]);

  return {
    id: String(code),
    ordem: indice + 1,
    code,
    nome,
    slug: normalizarChave(nome),
    busca: normalizarChave(`${nome} ${code} ${ESTILOS_EFEITO[estiloBusca]} ${SENTIDOS[sentidoBusca] ?? ""} ${linha.Descrição ?? ""}`),
    descricao: limparTexto(linha.Descrição) || "Descrição ainda não cadastrada.",
    estiloBusca,
    estiloRotulo: ESTILOS_EFEITO[estiloBusca],
    sentidoBusca,
    sentidoRotulo: SENTIDOS[sentidoBusca] ?? "Sem sentido fixo",
    passosBase,
    passosBaseTexto: passosBase === null ? "-" : String(passosBase),
  };
}

export function carregarEfeitos() {
  const caminho = caminhosPossiveisCsv().find((item) => existsSync(item));

  if (!caminho) {
    console.warn(`[Wiki Efeitos] CSV não encontrado. Procurei por: ${caminhosPossiveisCsv().join(" | ")}`);
    return [];
  }

  const conteudo = readFileSync(caminho, "utf8").replace(/^\uFEFF/, "");
  return parseCsv(conteudo).map((linha, indice) => normalizarEfeito(linha, indice));
}

function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}

export function indexarIconesEfeitos(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const chave = normalizarChave(arquivoSemExtensao(caminho));
    if (chave && !indice[chave]) indice[chave] = url;
  });
  return indice;
}

function candidatosEfeito(efeito) {
  const codigo = String(efeito.code ?? efeito.id ?? "");
  const prefixo = efeito.estiloBusca === "terreno" ? "Area" : efeito.estiloBusca === "clima" ? "Clima" : "Efeito";
  return [
    efeito.nome,
    efeito.slug,
    `${prefixo} ${efeito.nome}`,
    `${efeito.nome} ${prefixo}`,
    efeito.nome?.replace(/\s+/g, "_"),
    efeito.nome?.replace(/\s+/g, "-"),
    codigo,
    codigo.padStart(3, "0"),
    `efeito${codigo}`,
    `icone${codigo}`,
  ].filter(Boolean).map(normalizarChave);
}

export function resolverIconeEfeito(efeito, iconesPorNome) {
  for (const candidato of candidatosEfeito(efeito)) {
    if (iconesPorNome[candidato]) return iconesPorNome[candidato];
  }
  return null;
}

export function criarAssetsEfeitos(efeitos, iconesPorNome) {
  return Object.fromEntries(efeitos.map((efeito) => [efeito.id, { imagem: resolverIconeEfeito(efeito, iconesPorNome) }]));
}

export function resumoEfeitos(efeitos) {
  return {
    efeitos: efeitos.filter((efeito) => efeito.estiloBusca === "pokemon").length,
    climas: efeitos.filter((efeito) => efeito.estiloBusca === "clima").length,
    terrenos: efeitos.filter((efeito) => efeito.estiloBusca === "terreno").length,
  };
}

export const OPCOES_ESTILO_EFEITO = ESTILOS_EFEITO;
export const OPCOES_SENTIDO_EFEITO = SENTIDOS;
