import { carregarCsvWiki, limparTexto, numero } from "./WikiCsv.js";
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
  const codigoExibicao = String(code);
  const tipo = tipoCanonico(linha.Tipo);
  const estiloRotulo = rotuloEstilo(linha.Estilo);
  const estiloBusca = normalizarChave(linha.Estilo || estiloRotulo);
  const motores = separarMotores(linha.Motor || "Nenhum");
  const foco = calcularFoco(linha) ?? FOCOS_ATAQUE[0];
  const pontuacoes = Object.fromEntries(FOCOS_ATAQUE.map((item) => [item.chave, numero(linha[item.campo]) ?? 0]));
  const custo = numero(linha.Custo);
  const custoAprimorado = numero(linha["Custo AP"]);
  const uid = `${codigoExibicao}-${indice + 1}-${normalizarChave(nome)}`;
  return {
    id: codigoExibicao,
    uid,
    ordem: indice + 1,
    code,
    codigoExibicao,
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
  return carregarCsvWiki([NOME_CSV], "Wiki Ataques").map((linha, indice) => normalizarAtaque(linha, indice));
}
function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}
const CHAVES_TIPOS_VALIDOS = new Set(Object.keys(TIPOS_CANONICOS));

function chaveTipoPorCaminho(partes) {
  for (const parte of partes.slice(0, -1).reverse()) {
    const chave = normalizarChave(parte);
    if (CHAVES_TIPOS_VALIDOS.has(chave)) return normalizarChave(tipoCanonico(parte));
  }
  return "";
}

function registrarImagem(indice, chave, url) {
  const normalizada = normalizarChave(chave);
  if (normalizada && !indice[normalizada]) indice[normalizada] = url;
}

export function indexarIconesAtaques(glob) {
  const geral = {};
  const porTipo = {};
  let temPastasDeTipo = false;

  Object.entries(glob).forEach(([caminho, url]) => {
    const partes = caminho.split(/[\\/]/).filter(Boolean);
    const nomeArquivo = arquivoSemExtensao(caminho);
    const chaveArquivo = normalizarChave(nomeArquivo);
    const tipoChave = chaveTipoPorCaminho(partes);
    if (!chaveArquivo) return;

    if (tipoChave) {
      temPastasDeTipo = true;
      if (!porTipo[tipoChave]) porTipo[tipoChave] = {};
      registrarImagem(porTipo[tipoChave], chaveArquivo, url);
      return;
    }

    registrarImagem(geral, chaveArquivo, url);
  });

  return { geral, porTipo, temPastasDeTipo };
}
function candidatosNomeAtaque(ataque) {
  return [
    ataque.nome,
    ataque.slug,
    ataque.nome?.replace(/\s+/g, "_"),
    ataque.nome?.replace(/\s+/g, "-"),
  ].filter(Boolean).map(normalizarChave);
}
function candidatosNumericosAtaque(ataque) {
  const codigo = String(ataque.code ?? ataque.id ?? "").trim();
  return [
    codigo,
    codigo.padStart(3, "0"),
    `ataque${codigo}`,
    `icone${codigo}`,
  ].filter(Boolean).map(normalizarChave);
}
function candidatosAtaque(ataque) {
  return [...candidatosNomeAtaque(ataque), ...candidatosNumericosAtaque(ataque)];
}
export function resolverIconeAtaque(ataque, indiceIcones) {
  const tipo = ataque.tipoBusca;
  const porTipo = indiceIcones?.porTipo?.[tipo] ?? {};

  // Código/ID só é seguro quando está dentro da pasta do tipo correto.
  // Isso evita o bug de ataques normais puxarem ícones de água/fogo por terem o mesmo número.
  for (const candidato of candidatosAtaque(ataque)) {
    if (porTipo[candidato]) return porTipo[candidato];
  }

  // Fora de uma pasta de tipo, só o nome é confiável quando há pastas tipadas no projeto.
  for (const candidato of candidatosNomeAtaque(ataque)) {
    if (indiceIcones?.geral?.[candidato]) return indiceIcones.geral[candidato];
  }

  // Projetos antigos podem ter apenas ícones numéricos soltos em /public/Ataques.
  // Nesse caso, permite o fallback numérico porque não há risco de cruzar tipos.
  if (!indiceIcones?.temPastasDeTipo) {
    for (const candidato of candidatosNumericosAtaque(ataque)) {
      if (indiceIcones?.geral?.[candidato]) return indiceIcones.geral[candidato];
    }
  }
  return null;
}
export function criarAssetsAtaques(ataques, indiceIcones) {
  const assets = {};
  ataques.forEach((ataque) => {
    const entrada = { imagem: resolverIconeAtaque(ataque, indiceIcones) };
    const chaveUnica = ataque.uid || ataque.id;
    assets[chaveUnica] = entrada;

    // Fallback de compatibilidade para tabelas antigas com Code único.
    // Se o Code se repetir em outra linha, não sobrescreve e evita o bug de vários ataques puxarem o mesmo ícone.
    if (ataque.id && !assets[ataque.id]) assets[ataque.id] = entrada;
  });
  return assets;
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
