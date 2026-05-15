import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizarChave } from "./PokemonWikiDados.js";
const CSV_FR = "Pokemon Global Server - Sistema FR.csv";
const TOML_BATALHA = "Batalha.toml";
const TIPOS_CANONICOS = {
  agua: "Água",
  cosmico: "Cósmico",
  dragao: "Dragão",
  eletrico: "Elétrico",
  fada: "Fada",
  fantasma: "Fantasma",
  fogo: "Fogo",
  gelo: "Gelo",
  inseto: "Inseto",
  lutador: "Lutador",
  metal: "Metal",
  normal: "Normal",
  pedra: "Pedra",
  rocha: "Pedra",
  planta: "Planta",
  grama: "Planta",
  psiquico: "Psíquico",
  sombrio: "Sombrio",
  sonoro: "Sonoro",
  terrestre: "Terrestre",
  terra: "Terrestre",
  venenoso: "Venenoso",
  veneno: "Venenoso",
  voador: "Voador",
};
function limparTexto(valor) {
  return String(valor ?? "").trim();
}
function numero(valor, fallback = null) {
  if (typeof valor === "number" && Number.isFinite(valor)) return valor;
  const texto = limparTexto(valor).replace("%", "").replace(",", ".");
  if (!texto || texto === "-" || texto.toLowerCase() === "nan") return fallback;
  const convertido = Number(texto);
  return Number.isFinite(convertido) ? convertido : fallback;
}
function formatarNumero(valor, casas = 2) {
  const n = numero(valor);
  if (n === null) return "-";
  return n.toLocaleString("pt-BR", { maximumFractionDigits: casas });
}
function tipoCanonico(valor) {
  const chave = normalizarChave(valor);
  return TIPOS_CANONICOS[chave] ?? limparTexto(valor).replace(/^./, (letra) => letra.toUpperCase());
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
      if (linha.some((item) => limparTexto(item))) linhas.push(linha);
      campo = "";
      linha = [];
      continue;
    }
    campo += char;
  }
  if (campo || linha.length) {
    linha.push(campo);
    if (linha.some((item) => limparTexto(item))) linhas.push(linha);
  }
  return linhas;
}
function removerComentario(linha) {
  let aspas = false;
  let saida = "";
  for (let i = 0; i < linha.length; i += 1) {
    const char = linha[i];
    if (char === '"' && linha[i - 1] !== "\\") aspas = !aspas;
    if (char === "#" && !aspas) break;
    saida += char;
  }
  return saida.trim();
}
function separarSecao(secao) {
  const partes = [];
  let atual = "";
  let aspas = false;
  for (let i = 0; i < secao.length; i += 1) {
    const char = secao[i];
    if (char === '"' && secao[i - 1] !== "\\") {
      aspas = !aspas;
      continue;
    }
    if (char === "." && !aspas) {
      partes.push(atual.trim());
      atual = "";
      continue;
    }
    atual += char;
  }
  if (atual.trim()) partes.push(atual.trim());
  return partes;
}
function parseTomlValor(valor) {
  const texto = limparTexto(valor);
  if (texto.startsWith('"') && texto.endsWith('"')) return texto.slice(1, -1).replace(/\\"/g, '"');
  if (texto === "true") return true;
  if (texto === "false") return false;
  return numero(texto, texto);
}
function parseToml(texto) {
  const raiz = {};
  let alvo = raiz;
  texto.split(/\r?\n/).forEach((linhaBruta) => {
    const linha = removerComentario(linhaBruta);
    if (!linha) return;
    const secao = linha.match(/^\[([^\]]+)\]$/);
    if (secao) {
      alvo = raiz;
      separarSecao(secao[1]).forEach((parte) => {
        if (!alvo[parte]) alvo[parte] = {};
        alvo = alvo[parte];
      });
      return;
    }
    const igual = linha.indexOf("=");
    if (igual === -1) return;
    alvo[linha.slice(0, igual).trim()] = parseTomlValor(linha.slice(igual + 1));
  });
  return raiz;
}
function diretorioAtual() {
  return path.dirname(fileURLToPath(import.meta.url));
}
function caminhosCsv() {
  const atual = diretorioAtual();
  return [
    path.resolve(atual, "../../../Dados/Tabelas", CSV_FR),
    path.resolve(atual, "../../../Dados", CSV_FR),
    path.resolve(atual, "../../Dados/Tabelas", CSV_FR),
    path.resolve(atual, "../../Dados", CSV_FR),
    path.resolve(process.cwd(), "../Dados/Tabelas", CSV_FR),
    path.resolve(process.cwd(), "../Dados", CSV_FR),
    path.resolve(process.cwd(), "Dados/Tabelas", CSV_FR),
    path.resolve(process.cwd(), "Dados", CSV_FR),
  ];
}
function caminhosRegra(nomeArquivo) {
  const atual = diretorioAtual();
  return [
    path.resolve(atual, "../../../Dados/Regras", nomeArquivo),
    path.resolve(atual, "../../Dados/Regras", nomeArquivo),
    path.resolve(process.cwd(), "../Dados/Regras", nomeArquivo),
    path.resolve(process.cwd(), "Dados/Regras", nomeArquivo),
    path.resolve(process.cwd(), "../Pokemon-Global-Server-Definitivo/Dados/Regras", nomeArquivo),
  ];
}
function carregarCsvFr() {
  const caminhos = caminhosCsv();
  const caminho = caminhos.find((item) => existsSync(item));
  if (!caminho) {
    console.warn(`[Wiki Combate] CSV de fraquezas e resistências não encontrado. Procurei por: ${caminhos.join(" | ")}`);
    return [];
  }
  return parseCsv(readFileSync(caminho, "utf8").replace(/^\uFEFF/, ""));
}
function carregarRegraBatalha() {
  const caminhos = caminhosRegra(TOML_BATALHA);
  const caminho = caminhos.find((item) => existsSync(item));
  if (!caminho) return {};
  return parseToml(readFileSync(caminho, "utf8").replace(/^\uFEFF/, ""));
}
function montarMatriz(linhasCsv) {
  const cabecalho = (linhasCsv[0] ?? []).slice(1).map(tipoCanonico);
  return (linhasCsv.slice(1) ?? []).map((linha) => {
    const tipoAtaque = tipoCanonico(linha[0]);
    const valores = {};
    cabecalho.forEach((tipoDefesa, indice) => {
      valores[normalizarChave(tipoDefesa)] = numero(linha[indice + 1], 1);
    });
    return { tipo: tipoAtaque, chave: normalizarChave(tipoAtaque), valores };
  });
}
function tiposPorCondicao(tipos, fn) {
  return tipos.filter((tipo) => fn(tipo)).map((tipo) => ({ nome: tipo.nome, chave: tipo.chave }));
}
function montarLinhasTabela(matriz) {
  const tipos = matriz.map((linha) => ({ nome: linha.tipo, chave: linha.chave }));
  const porAtaque = Object.fromEntries(matriz.map((linha) => [linha.chave, linha.valores]));
  return tipos.map((tipo) => ({
    ...tipo,
    superEfetivo: tiposPorCondicao(tipos, (defensor) => (porAtaque[tipo.chave]?.[defensor.chave] ?? 1) > 1),
    poucoEfetivo: tiposPorCondicao(tipos, (defensor) => {
      const mult = porAtaque[tipo.chave]?.[defensor.chave] ?? 1;
      return mult > 0 && mult < 1;
    }),
    naoAfeta: tiposPorCondicao(tipos, (defensor) => (porAtaque[tipo.chave]?.[defensor.chave] ?? 1) === 0),
    fraquezas: tiposPorCondicao(tipos, (atacante) => (porAtaque[atacante.chave]?.[tipo.chave] ?? 1) > 1),
    resistencias: tiposPorCondicao(tipos, (atacante) => {
      const mult = porAtaque[atacante.chave]?.[tipo.chave] ?? 1;
      return mult > 0 && mult < 1;
    }),
    imunidades: tiposPorCondicao(tipos, (atacante) => (porAtaque[atacante.chave]?.[tipo.chave] ?? 1) === 0),
  }));
}
function resumoRegraBatalha() {
  // Valores refletidos pelo código atual em Servidor/Batalha:
  // ColetorAcoes valida limites/custos/ordem; RodadorTurno executa passos;
  // PokemonBatalha calcula dano, cura, energia, barreira e efeitos.
  return {
    maxAcoesPorLado: 5,
    maxAcoesPorPokemon: 2,
    custoMovimento: 15,
    custoTroca: 20,
    multiplicadorSegundaAcao: 1.10,
    segundaAcaoTexto: "1,10x",
    ordemTexto: "Inteligência decrescente; empate por Velocidade; captura depois das ações comuns",
    energiaFimRodada: "Ene do Pokémon",
    energiaEnergizado: "+25%",
    energiaDescarregado: "-25%",
    stabTexto: "1,20x",
    curaQueimadoTexto: "0,65x",
  };
}
export function carregarWikiCombate() {
  const matriz = montarMatriz(carregarCsvFr());
  const linhasTabela = montarLinhasTabela(matriz);
  const regra = resumoRegraBatalha();
  return {
    tipos: matriz.map((linha) => ({ nome: linha.tipo, chave: linha.chave })),
    tabela: linhasTabela,
    regra,
    resumo: {
      tipos: matriz.length,
      colunas: matriz.length ? 5 : 0,
      maxAcoesPorLado: regra.maxAcoesPorLado,
    },
  };
}
