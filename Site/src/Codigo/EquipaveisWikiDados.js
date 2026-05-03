import { campo, campoNumero, carregarCsvWiki, limparTexto } from "./WikiCsv.js";
import { normalizarChave } from "./PokemonWikiDados.js";
const NOMES_CSV = ["Pokemon Global Server - Equipaveis.csv", "Pokemon Global Server - Equipáveis.csv"];
export const ATRIBUTOS_EQUIPAVEIS = [
  { chave: "Vida", rotulo: "Vida", maximo: 200 },
  { chave: "Atk", rotulo: "Atk", maximo: 100 },
  { chave: "Def", rotulo: "Def", maximo: 100 },
  { chave: "SpA", rotulo: "SpA", maximo: 100 },
  { chave: "SpD", rotulo: "SpD", maximo: 100 },
  { chave: "Vel", rotulo: "Vel", maximo: 100 },
  { chave: "Mag", rotulo: "Mag", maximo: 100 },
  { chave: "Per", rotulo: "Per", maximo: 100 },
  { chave: "Ene", rotulo: "Ene", maximo: 100 },
  { chave: "Int", rotulo: "Int", maximo: 100 },
  { chave: "CrD", rotulo: "CrD", maximo: 75 },
  { chave: "CrC", rotulo: "CrC", maximo: 75 },
  { chave: "Vamp", rotulo: "Vamp", maximo: 100 },
  { chave: "Bar", rotulo: "Bar", maximo: 100 },
  { chave: "Dur", rotulo: "Dur", maximo: 100 },
  { chave: "Amp", rotulo: "Amp", maximo: 100 },
];
export const FOCOS_EQUIPAVEIS = [
  { chave: "ofensivo", campos: ["Ofensivo"], rotulo: "Ofensivo" },
  { chave: "defensivo", campos: ["Defensivo"], rotulo: "Defensivo" },
  { chave: "suporte", campos: ["Suporte"], rotulo: "Suporte" },
  { chave: "utilitario", campos: ["Utilitario", "Utilitário"], rotulo: "Utilitário" },
];
const ATRIBUTOS_POR_CHAVE = Object.fromEntries(
  ATRIBUTOS_EQUIPAVEIS.flatMap((atributo) => [
    [normalizarChave(atributo.chave), atributo],
    [normalizarChave(atributo.rotulo), atributo],
  ]),
);
const TIPOS_CANONICOS = {
  agua: "Água",
  aco: "Aço",
  metal: "Metal",
  cosmico: "Cósmico",
  dragao: "Dragão",
  eletrico: "Elétrico",
  fada: "Fada",
  fantasma: "Fantasma",
  fogo: "Fogo",
  gelo: "Gelo",
  grama: "Planta",
  planta: "Planta",
  inseto: "Inseto",
  lutador: "Lutador",
  normal: "Normal",
  pedra: "Pedra",
  psiquico: "Psíquico",
  sombrio: "Sombrio",
  sonoro: "Sonoro",
  terrestre: "Terrestre",
  terra: "Terrestre",
  venenoso: "Venenoso",
  veneno: "Venenoso",
  voador: "Voador",
};
function tipoCanonico(valor) {
  const texto = limparTexto(valor);
  const chave = normalizarChave(texto);
  return TIPOS_CANONICOS[chave] ?? (texto ? texto.replace(/^./, (letra) => letra.toUpperCase()) : "Sem afinidade");
}
function atributoCanonico(valor) {
  const chave = normalizarChave(valor);
  return ATRIBUTOS_POR_CHAVE[chave] ?? null;
}
function separarAfinidades(valor) {
  const lista = limparTexto(valor)
    .split(/[/;,|]+/g)
    .map((item) => tipoCanonico(item))
    .filter(Boolean);
  return lista.length ? [...new Map(lista.map((item) => [normalizarChave(item), item])).values()] : ["Sem afinidade"];
}
function numeroAumento(linha, indice) {
  return campoNumero(linha, [`Aumento ${indice}`, `Valor ${indice}`, `Bonus ${indice}`, `Bônus ${indice}`], 0) ?? 0;
}
function aumentosPorParesStatus(linha) {
  const mapa = new Map();
  for (let i = 1; i <= 8; i += 1) {
    const atributo = atributoCanonico(campo(linha, [`Status ${i}`, `Atributo ${i}`], ""));
    const valor = numeroAumento(linha, i);
    if (!atributo || valor === 0) continue;
    const atual = mapa.get(atributo.chave) ?? { ...atributo, valor: 0 };
    atual.valor += valor;
    mapa.set(atributo.chave, atual);
  }
  return mapa;
}
function valorAtributoDireto(linha, atributo) {
  return campoNumero(linha, [
    atributo.chave,
    atributo.rotulo,
    `+${atributo.chave}`,
    `+${atributo.rotulo}`,
    `Aumento ${atributo.chave}`,
    `Aumento ${atributo.rotulo}`,
  ], 0) ?? 0;
}
function coletarAumentos(linha) {
  const porPares = aumentosPorParesStatus(linha);
  ATRIBUTOS_EQUIPAVEIS.forEach((atributo) => {
    const direto = valorAtributoDireto(linha, atributo);
    if (!direto) return;
    const atual = porPares.get(atributo.chave) ?? { ...atributo, valor: 0 };
    atual.valor += direto;
    porPares.set(atributo.chave, atual);
  });
  return [...porPares.values()].filter((atributo) => atributo.valor !== 0);
}
function calcularFoco(linha) {
  const pontuacoes = Object.fromEntries(FOCOS_EQUIPAVEIS.map((foco) => [foco.chave, campoNumero(linha, foco.campos, 0) ?? 0]));
  const maior = FOCOS_EQUIPAVEIS.reduce((melhor, foco) => {
    const valor = pontuacoes[foco.chave] ?? 0;
    if (!melhor || valor > melhor.valor) return { ...foco, valor };
    return melhor;
  }, null);
  return { pontuacoes, principal: maior && maior.valor > 0 ? maior : null };
}
function normalizarEquipavel(linha, indice) {
  const nome = limparTexto(campo(linha, ["Nome", "Equipavel", "Equipável"])) || `Equipável ${indice + 1}`;
  const code = campoNumero(linha, ["Code", "Código", "ID", "Id"], indice + 1) ?? indice + 1;
  const afinidades = separarAfinidades(campo(linha, ["Afinidade", "Tipo", "Elemento"], ""));
  const afinidade = afinidades.join(" / ");
  const aumentos = coletarAumentos(linha);
  const atributos = Object.fromEntries(ATRIBUTOS_EQUIPAVEIS.map((atributo) => [atributo.chave, 0]));
  aumentos.forEach((atributo) => {
    atributos[atributo.chave] = atributo.valor;
  });
  const maiorAumento = aumentos.reduce((maior, atual) => (Math.abs(atual.valor) > Math.abs(maior?.valor ?? 0) ? atual : maior), null);
  const foco = calcularFoco(linha);
  const descricao = limparTexto(campo(linha, ["Descrição", "Descricao", "Descrição Melhor", "Descricao Melhor", "Desc"], ""));
  const passiva = limparTexto(campo(linha, ["Passiva", "Passivas", "Efeito", "Habilidade"], ""));
  const formaFinal = limparTexto(campo(linha, ["Forma Final", "Forma", "FF"], ""));
  return {
    id: String(code),
    ordem: indice + 1,
    code,
    nome,
    slug: normalizarChave(nome),
    busca: normalizarChave(`${nome} ${code} ${afinidade} ${descricao} ${passiva} ${formaFinal} ${aumentos.map((item) => item.rotulo).join(" ")}`),
    descricao: descricao && descricao !== "-" ? descricao : "Descrição ainda não cadastrada.",
    afinidade,
    afinidades,
    afinidadeBusca: normalizarChave(afinidades[0]),
    afinidadesBusca: afinidades.map(normalizarChave),
    atributos,
    aumentos,
    atributosBusca: aumentos.flatMap((atributo) => [atributo.chave, normalizarChave(atributo.chave), atributo.rotulo, normalizarChave(atributo.rotulo)]),
    maiorAumento: maiorAumento?.chave ?? "",
    maiorAumentoRotulo: maiorAumento?.rotulo ?? "",
    maiorAumentoValor: maiorAumento?.valor ?? 0,
    focoPrincipal: foco.principal?.rotulo ?? "Sem foco definido",
    focoPrincipalBusca: foco.principal?.chave ?? "",
    ...foco.pontuacoes,
    passiva,
    formaFinal,
  };
}
export function carregarEquipaveis() {
  return carregarCsvWiki(NOMES_CSV, "Wiki Equipáveis").map((linha, indice) => normalizarEquipavel(linha, indice));
}
function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}
export function indexarImagensEquipaveis(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const chave = normalizarChave(arquivoSemExtensao(caminho));
    if (chave && !indice[chave]) indice[chave] = url;
  });
  return indice;
}
function candidatosEquipavel(equipavel) {
  const codigo = String(equipavel.code ?? equipavel.id ?? "");
  return [
    equipavel.nome,
    equipavel.slug,
    equipavel.nome?.replace(/\s+/g, "_"),
    equipavel.nome?.replace(/\s+/g, "-"),
    codigo,
    codigo.padStart(3, "0"),
    `equipavel${codigo}`,
    `equipável${codigo}`,
    `item${codigo}`,
    `icone${codigo}`,
  ].filter(Boolean).map(normalizarChave);
}
export function resolverImagemEquipavel(equipavel, imagensPorNome) {
  for (const candidato of candidatosEquipavel(equipavel)) {
    if (imagensPorNome[candidato]) return imagensPorNome[candidato];
  }
  return null;
}
export function criarAssetsEquipaveis(equipaveis, imagensPorNome) {
  return Object.fromEntries(equipaveis.map((equipavel) => [equipavel.id, { imagem: resolverImagemEquipavel(equipavel, imagensPorNome) }]));
}
export function resumoEquipaveis(equipaveis) {
  const afinidades = [...new Map(equipaveis.flatMap((equipavel) => equipavel.afinidades || [equipavel.afinidade]).map((afinidade) => [normalizarChave(afinidade), afinidade])).values()]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, "pt-BR"));
  const formas = new Set(equipaveis.map((item) => item.formaFinal).filter(Boolean));
  const passivas = new Set(equipaveis.map((item) => item.passiva).filter(Boolean));
  return {
    quantidade: equipaveis.length,
    formasFinais: formas.size || 4,
    passivas: passivas.size || 40,
    afinidades,
  };
}
