import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizarChave } from "./PokemonWikiDados.js";

const NOME_CSV = "Pokemon Global Server - Ataques.csv";

export const FOCOS_ATAQUE = [
  { chave: "ofensivo", campo: "Ofensivo", rotulo: "Ofensivo" },
  { chave: "defensivo", campo: "Defensivo", rotulo: "Defensivo" },
  { chave: "suporte", campo: "Suporte", rotulo: "Suporte" },
  { chave: "utilitario", campo: "Utilitario", rotulo: "Utilitário" },
];

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
  terra: "Terrestre",
  terrestre: "Terrestre",
  venenoso: "Venenoso",
  voador: "Voador",
};

const ESTILOS_ATAQUE = {
  alvo: "Alvo",
  ativa: "Ativa",
  ativo: "Ativa",
  passivo: "Passiva",
  passiva: "Passiva",
};

function limparTexto(valor) {
  return String(valor ?? "").trim();
}

function numero(valor) {
  const texto = limparTexto(valor).replace("%", "").replace(",", ".");
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

function tipoCanonico(valor) {
  const chave = normalizarChave(valor);
  return TIPOS_CANONICOS[chave] ?? (limparTexto(valor) || "Sem tipo").replace(/^./, (letra) => letra.toUpperCase());
}

function rotuloEstilo(valor) {
  const chave = normalizarChave(valor);
  return ESTILOS_ATAQUE[chave] ?? (limparTexto(valor) || "Sem estilo").replace(/^./, (letra) => letra.toUpperCase());
}

function separarMotores(valor) {
  const partes = limparTexto(valor)
    .split("/")
    .map((parte) => limparTexto(parte))
    .filter(Boolean);
  const unicos = new Map();
  partes.forEach((motor) => {
    const chave = normalizarChave(motor);
    if (chave && !unicos.has(chave)) unicos.set(chave, motor);
  });
  return [...unicos.entries()].map(([chave, rotulo]) => ({ chave, rotulo }));
}

function calcularFoco(linha) {
  return FOCOS_ATAQUE.reduce((melhor, foco) => {
    const valor = numero(linha[foco.campo]) ?? 0;
    if (!melhor || valor > melhor.valor) return { ...foco, valor };
    return melhor;
  }, null);
}

function normalizarAtaque(linha, indice) {
  const nome = limparTexto(linha.Ataque) || `Ataque ${indice + 1}`;
  const code = numero(linha.Code) ?? indice + 1;
  const tipo = tipoCanonico(linha.Tipo);
  const estiloRotulo = rotuloEstilo(linha.Estilo);
  const estiloBusca = normalizarChave(linha.Estilo || estiloRotulo);
  const motores = separarMotores(linha.Motor || "Nenhum");
  const foco = calcularFoco(linha) ?? FOCOS_ATAQUE[0];
  const pontuacoes = Object.fromEntries(FOCOS_ATAQUE.map((item) => [item.chave, numero(linha[item.campo]) ?? 0]));
  const custo = numero(linha.Custo);
  const custoAprimorado = numero(linha["Custo AP"]);

  return {
    id: String(code),
    ordem: indice + 1,
    code,
    nome,
    slug: normalizarChave(nome),
    busca: normalizarChave(`${nome} ${code} ${tipo} ${linha.Tipo ?? ""} ${linha.Estilo ?? ""} ${linha.Motor ?? ""} ${linha.Descrição ?? ""} ${linha.Aprimoramento ?? ""}`),
    custo,
    custoAprimorado,
    tipo,
    tipoOriginal: limparTexto(linha.Tipo) || tipo,
    tipoBusca: normalizarChave(tipo),
    estiloOriginal: limparTexto(linha.Estilo) || estiloRotulo,
    estiloRotulo,
    estiloBusca,
    descricao: limparTexto(linha.Descrição) || "Descrição ainda não cadastrada.",
    aprimoramento: limparTexto(linha.Aprimoramento) || "Aprimoramento ainda não cadastrado.",
    motores,
    motoresBusca: motores.map((motor) => motor.chave),
    motorTexto: motores.map((motor) => motor.rotulo).join(" / ") || "Nenhum",
    focoPrincipal: foco.rotulo,
    focoPrincipalBusca: foco.chave,
    ...pontuacoes,
  };
}

export function carregarAtaques() {
  const caminho = caminhosPossiveisCsv().find((item) => existsSync(item));

  if (!caminho) {
    console.warn(`[Wiki Ataques] CSV não encontrado. Procurei por: ${caminhosPossiveisCsv().join(" | ")}`);
    return [];
  }

  const conteudo = readFileSync(caminho, "utf8").replace(/^\uFEFF/, "");
  return parseCsv(conteudo).map((linha, indice) => normalizarAtaque(linha, indice));
}

function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}

export function indexarIconesAtaques(glob) {
  const geral = {};
  const porTipo = {};

  Object.entries(glob).forEach(([caminho, url]) => {
    const partes = caminho.split(/[\\/]/).filter(Boolean);
    const nomeArquivo = arquivoSemExtensao(caminho);
    const chaveArquivo = normalizarChave(nomeArquivo);
    const pastaTipo = partes.at(-2) ?? "";
    const tipo = tipoCanonico(pastaTipo);
    const tipoChave = normalizarChave(tipo);

    if (chaveArquivo && !geral[chaveArquivo]) geral[chaveArquivo] = url;
    if (tipoChave) {
      if (!porTipo[tipoChave]) porTipo[tipoChave] = {};
      if (chaveArquivo && !porTipo[tipoChave][chaveArquivo]) porTipo[tipoChave][chaveArquivo] = url;
    }
  });

  return { geral, porTipo };
}

function candidatosAtaque(ataque) {
  const codigo = String(ataque.code ?? ataque.id ?? "");
  return [
    ataque.nome,
    ataque.slug,
    ataque.nome?.replace(/\s+/g, "_"),
    ataque.nome?.replace(/\s+/g, "-"),
    codigo,
    codigo.padStart(3, "0"),
    `ataque${codigo}`,
    `icone${codigo}`,
  ].filter(Boolean).map(normalizarChave);
}

export function resolverIconeAtaque(ataque, indiceIcones) {
  const tipo = ataque.tipoBusca;
  const porTipo = indiceIcones?.porTipo?.[tipo] ?? {};
  for (const candidato of candidatosAtaque(ataque)) {
    if (porTipo[candidato]) return porTipo[candidato];
  }
  for (const candidato of candidatosAtaque(ataque)) {
    if (indiceIcones?.geral?.[candidato]) return indiceIcones.geral[candidato];
  }
  return null;
}

export function criarAssetsAtaques(ataques, indiceIcones) {
  return Object.fromEntries(ataques.map((ataque) => [ataque.id, { imagem: resolverIconeAtaque(ataque, indiceIcones) }]));
}

export function resumoAtaques(ataques) {
  const estilos = [...new Map(ataques.map((ataque) => [ataque.estiloBusca, ataque.estiloRotulo])).values()].sort((a, b) =>
    a.localeCompare(b, "pt-BR"),
  );
  const tipos = [...new Map(ataques.map((ataque) => [ataque.tipoBusca, ataque.tipo])).values()].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const motores = new Map();
  ataques.forEach((ataque) => ataque.motores.forEach((motor) => motores.set(motor.chave, motor.rotulo)));

  return {
    quantidade: ataques.length,
    estilos,
    tipos,
    motores: [...motores.entries()].map(([chave, rotulo]) => ({ chave, rotulo })).sort((a, b) => a.rotulo.localeCompare(b.rotulo, "pt-BR")),
  };
}
