import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizarChave } from "./PokemonWikiDados.js";

const NOMES_REGRAS = {
  estruturas: "EstruturasNaturais.toml",
  biomas: "Biomas.toml",
  terreno: "Terreno.toml",
};

const ROTULOS_BIOMAS = {
  FIELD: "Campo",
  FOREST: "Floresta",
  DESERT: "Deserto",
  SNOW: "Neve",
  MAGIC: "Mágico",
  VOLCANIC: "Vulcânico",
  SWAMP: "Pântano",
};

const ROTULOS_TILES = {
  FIELD_GRASS: "Grama de campo",
  FOREST_GRASS: "Grama de floresta",
  BEACH_SAND: "Areia de praia",
  DESERT_SAND: "Areia de deserto",
  SNOW: "Neve",
  MAGIC_SOIL: "Solo mágico",
  VOLCANIC_ROCK: "Rocha vulcânica",
  DEAD_SOIL: "Solo pantanoso",
  WATER_DEEP: "Água profunda",
  WATER_SHALLOW: "Água rasa",
};

const SUBTIPO_PARA_OBJETO = {
  arvore: "TREE",
  pedra: "ROCK",
  arbusto: "BUSH",
  ouro: "GOLD",
  ametista: "AMETHYST",
  diamante: "DIAMOND",
  rubi: "RUBY",
  esmeralda: "EMERALD",
  palmeira: "PALM",
  pinheiro: "PINE",
  cobre: "COPPER",
  lava: "LAVA_POOL",
  cacto: "CACTUS",
  concha: "SHELL",
  aquamarine: "AQUAMARINE",
  carvao: "COAL",
  ferro: "IRON",
  flor: "FLOWER",
  jade: "JADE",
  planta: "PLANT",
  safira: "SAPPHIRE",
  topazio: "TOPAZ",
  arvore_trombosa: "TREE_TROMBOSA",
  casa: "HOUSE",
};

const CATEGORIAS_ESTRUTURA = {
  arvore: "Flora",
  arvore_trombosa: "Flora",
  arbusto: "Flora",
  palmeira: "Flora",
  pinheiro: "Flora",
  cacto: "Flora",
  flor: "Flora",
  planta: "Flora",
  pedra: "Mineral comum",
  cobre: "Mineral comum",
  ferro: "Mineral comum",
  carvao: "Mineral comum",
  ouro: "Mineral raro",
  ametista: "Gema",
  diamante: "Gema",
  rubi: "Gema",
  esmeralda: "Gema",
  aquamarine: "Gema",
  jade: "Gema",
  safira: "Gema",
  topazio: "Gema",
  lava: "Especial",
  concha: "Especial",
  casa: "Localidade",
  pedra_dungeon: "Dungeon",
};

const DESCRICOES_BIOMAS = {
  FIELD: "Bioma aberto e equilibrado. Costuma receber árvores, arbustos, pedras, minérios básicos e pequenas plantas, funcionando como uma região segura para início de exploração.",
  FOREST: "Bioma denso e úmido, com maior presença de vegetação. É o principal ambiente para árvores trombosas, arbustos, flores e plantas naturais.",
  DESERT: "Bioma seco, quente e aberto. Troca vegetação comum por palmeiras, cactos e gemas de areia, como esmeralda e topázio.",
  SNOW: "Bioma frio, marcado por pinheiros e gemas associadas à neve. É o espaço natural para diamante e jade.",
  MAGIC: "Bioma raro e instável. Mantém vegetação viva, mas adiciona presença de ametista e flores em maior destaque.",
  VOLCANIC: "Bioma quente e mineral. Possui ferro, carvão, lava e rubi com mais força que outros ambientes.",
  SWAMP: "Bioma úmido e pesado. Mistura árvores, plantas, pedra e safira, com uma sensação mais fechada e pantanosa.",
};

function limparTexto(valor) {
  return String(valor ?? "").trim();
}

function numero(valor) {
  if (typeof valor === "number" && Number.isFinite(valor)) return valor;
  const texto = limparTexto(valor).replace(",", ".");
  if (!texto || texto === "-" || texto.toLowerCase() === "nan") return null;
  const convertido = Number(texto);
  return Number.isFinite(convertido) ? convertido : null;
}

function removerComentario(linha) {
  let aspas = false;
  let resultado = "";
  for (let i = 0; i < linha.length; i += 1) {
    const char = linha[i];
    if (char === '"' && linha[i - 1] !== "\\") aspas = !aspas;
    if (char === "#" && !aspas) break;
    resultado += char;
  }
  return resultado.trim();
}

function separarCaminhoSecao(secao) {
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
  return partes.map((parte) => parte.replace(/^"|"$/g, ""));
}

function parseArray(valor) {
  const miolo = valor.slice(1, -1).trim();
  if (!miolo) return [];
  const itens = [];
  let atual = "";
  let aspas = false;

  for (let i = 0; i < miolo.length; i += 1) {
    const char = miolo[i];
    if (char === '"' && miolo[i - 1] !== "\\") aspas = !aspas;
    if (char === "," && !aspas) {
      itens.push(parseTomlValue(atual.trim()));
      atual = "";
      continue;
    }
    atual += char;
  }

  if (atual.trim()) itens.push(parseTomlValue(atual.trim()));
  return itens;
}

function parseTomlValue(valor) {
  const texto = limparTexto(valor);
  if (texto.startsWith("[") && texto.endsWith("]")) return parseArray(texto);
  if (texto.startsWith('"') && texto.endsWith('"')) return texto.slice(1, -1).replace(/\\"/g, '"');
  if (texto === "true") return true;
  if (texto === "false") return false;
  const convertido = Number(texto);
  if (Number.isFinite(convertido)) return convertido;
  return texto;
}

function garantirSecao(objeto, caminho) {
  let alvo = objeto;
  caminho.forEach((parte) => {
    if (!alvo[parte] || typeof alvo[parte] !== "object" || Array.isArray(alvo[parte])) alvo[parte] = {};
    alvo = alvo[parte];
  });
  return alvo;
}

function parseToml(texto) {
  const raiz = {};
  let secaoAtual = raiz;

  texto.split(/\r?\n/).forEach((linhaBruta) => {
    const linha = removerComentario(linhaBruta);
    if (!linha) return;

    const secao = linha.match(/^\[([^\]]+)\]$/);
    if (secao) {
      secaoAtual = garantirSecao(raiz, separarCaminhoSecao(secao[1]));
      return;
    }

    const igual = linha.indexOf("=");
    if (igual === -1) return;
    const chave = linha.slice(0, igual).trim();
    const valor = linha.slice(igual + 1).trim();
    secaoAtual[chave] = parseTomlValue(valor);
  });

  return raiz;
}

function candidatosRegras(nomeArquivo) {
  const diretorioAtual = path.dirname(fileURLToPath(import.meta.url));
  return [
    path.resolve(diretorioAtual, "../../../SimuladorServerJogo/Logica/Regras", nomeArquivo),
    path.resolve(diretorioAtual, "../../SimuladorServerJogo/Logica/Regras", nomeArquivo),
    path.resolve(diretorioAtual, "../SimuladorServerJogo/Logica/Regras", nomeArquivo),
    path.resolve(process.cwd(), "../SimuladorServerJogo/Logica/Regras", nomeArquivo),
    path.resolve(process.cwd(), "SimuladorServerJogo/Logica/Regras", nomeArquivo),
    path.resolve(process.cwd(), "../Pokemon-Global-Server-Definitivo/SimuladorServerJogo/Logica/Regras", nomeArquivo),
  ];
}

function carregarToml(nomeArquivo, rotulo) {
  const caminhos = candidatosRegras(nomeArquivo);
  const caminho = caminhos.find((item) => existsSync(item));
  if (!caminho) {
    console.warn(`[Wiki Mundo] ${rotulo} não encontrado. Procurei por: ${caminhos.join(" | ")}`);
    return {};
  }

  const conteudo = readFileSync(caminho, "utf8").replace(/^\uFEFF/, "");
  return parseToml(conteudo);
}

function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}

function rotuloEstilo(valor) {
  const chave = normalizarChave(valor);
  const rotulos = {
    machado: "Machado",
    picareta: "Picareta",
    balde: "Balde",
    nenhum: "Nenhum",
  };
  return rotulos[chave] ?? (limparTexto(valor) || "Não informado");
}

function percentual(valor) {
  const n = numero(valor);
  if (n === null) return "-";
  return `${(n * 100).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}%`;
}

function formatarNumero(valor, casas = 2) {
  const n = numero(valor);
  if (n === null) return "-";
  return n.toLocaleString("pt-BR", { maximumFractionDigits: casas });
}

function textoLista(lista, vazio = "Não informado") {
  if (!Array.isArray(lista) || !lista.length) return vazio;
  return lista.join(", ");
}

function gerarDescricaoEstrutura(estrutura, biomas) {
  const nome = estrutura.nome;
  const categoria = estrutura.categoria;
  const ferramenta = estrutura.ferramenta;
  const biomasTexto = biomas.length ? biomas.map((bioma) => bioma.nome).join(", ") : estrutura.origemEspecial || "localidades específicas";
  const drop = estrutura.dropAtivo ? "é coletável e entrega recurso ao jogador" : "está marcada como sem drop ativo nas regras atuais";

  if (estrutura.subtipo === "casa") {
    return "Casas fazem parte da geração das vilas. Na wiki elas aparecem como estruturas de localidade, não como recurso natural comum, porque são inquebráveis e ajudam a representar civilização no mapa.";
  }

  if (estrutura.subtipo === "pedra_dungeon") {
    return "Pedra Dungeon é uma estrutura especial usada para compor áreas de dungeon. Ela mantém comportamento mineral, mas sua função principal é dar identidade visual e física aos ambientes fechados.";
  }

  if (estrutura.subtipo === "aquamarine") {
    return "Aquamarine é uma gema ligada à água profunda. A regra usa uma taxa própria para águas fundas, então ela não depende dos mesmos sorteios terrestres dos outros biomas.";
  }

  if (estrutura.subtipo === "concha") {
    return "Conchas aparecem em faixas de praia e costa. Elas ajudam a marcar a transição entre terra e água e funcionam mais como estrutura ambiental especial do que como recurso bruto comum.";
  }

  if (estrutura.subtipo === "lava") {
    return "Lava nasce em regiões vulcânicas e funciona como estrutura natural especial. O tamanho de campo e interação é maior que o de minérios comuns, reforçando que ela ocupa espaço de ambiente.";
  }

  if (categoria === "Flora") {
    return `${nome} aparece em ${biomasTexto}. É uma estrutura vegetal de dureza ${estrutura.durezaTexto}, usa ${ferramenta} como ferramenta indicada e ${drop}.`;
  }

  if (categoria.includes("Mineral")) {
    return `${nome} aparece em ${biomasTexto}. É uma estrutura mineral de dureza ${estrutura.durezaTexto}, normalmente associada à coleta com ${ferramenta} e a progressão de recursos do mundo.`;
  }

  if (categoria === "Gema") {
    return `${nome} aparece em ${biomasTexto}. É uma gema mais específica do mapa, útil para recompensar exploração em biomas próprios e diferenciar regiões visualmente.`;
  }

  return `${nome} aparece em ${biomasTexto}. A regra define quantidade, dureza, campo e interação, então a wiki acompanha automaticamente qualquer ajuste feito no TOML.`;
}

function classificarFrequencia(chanceMaxima) {
  if (!chanceMaxima || chanceMaxima <= 0) return "Especial";
  if (chanceMaxima >= 0.008) return "Comum";
  if (chanceMaxima >= 0.003) return "Frequente";
  if (chanceMaxima >= 0.001) return "Raro";
  return "Muito raro";
}

function biomasDaEstrutura(subtipo, biomasToml) {
  const objeto = SUBTIPO_PARA_OBJETO[subtipo];
  const biomas = [];
  if (!objeto) return biomas;

  Object.entries(biomasToml.biomes ?? {}).forEach(([codigo, cfg]) => {
    const chance = numero(cfg?.objects?.[objeto]) ?? 0;
    if (chance <= 0) return;
    biomas.push({
      codigo,
      nome: ROTULOS_BIOMAS[codigo] ?? codigo,
      tile: ROTULOS_TILES[cfg.base_tile] ?? cfg.base_tile ?? "Terreno",
      chance,
      chanceTexto: percentual(chance),
    });
  });

  return biomas.sort((a, b) => b.chance - a.chance || a.nome.localeCompare(b.nome, "pt-BR"));
}

function montarEstrutura([codigo, cfg], biomasToml) {
  const subtipo = limparTexto(cfg.subtipo) || `estrutura_${codigo}`;
  const biomas = biomasDaEstrutura(subtipo, biomasToml);
  const chanceMaxima = Math.max(0, ...biomas.map((bioma) => bioma.chance));
  const origemEspecial = subtipo === "aquamarine" ? "Água profunda" : subtipo === "casa" ? "Vilas" : subtipo === "pedra_dungeon" ? "Dungeons" : "Geração especial";
  const dropAtivo = cfg.drop_ativo === undefined ? true : Boolean(cfg.drop_ativo);

  const estrutura = {
    id: String(codigo),
    ordem: numero(codigo) ?? 9999,
    nome: limparTexto(cfg.nome) || `Estrutura ${codigo}`,
    subtipo,
    subtipoChave: normalizarChave(subtipo),
    slug: normalizarChave(cfg.nome || subtipo),
    sprite: limparTexto(cfg.sprite),
    spriteArquivo: arquivoSemExtensao(cfg.sprite || ""),
    categoria: CATEGORIAS_ESTRUTURA[subtipo] ?? "Estrutura",
    material: limparTexto(cfg.material) || (dropAtivo ? "Material não informado" : "Sem material/drop"),
    ferramenta: rotuloEstilo(cfg.estilo),
    dureza: numero(cfg.dureza),
    durezaTexto: formatarNumero(cfg.dureza, 0),
    quantidade: numero(cfg.quantidade),
    quantidadeTexto: formatarNumero(cfg.quantidade, 0),
    raioColisaoTexto: formatarNumero(cfg.raio_colisao),
    raioInteracaoTexto: formatarNumero(cfg.raio_interacao),
    campoTexto: formatarNumero(cfg.campo),
    intensidadeTexto: formatarNumero(cfg.intensidade),
    rotacao: limparTexto(cfg.rotacao) || "nenhuma",
    inquebravel: Boolean(cfg.inquebravel),
    dropAtivo,
    particulasTexto: textoLista(cfg.particulasXP),
    tamanhosTexto: textoLista(cfg.tamanhosXP),
    biomas,
    biomasTexto: biomas.length ? biomas.map((bioma) => bioma.nome).join(", ") : origemEspecial,
    chanceMaxima,
    chanceMaximaTexto: chanceMaxima > 0 ? percentual(chanceMaxima) : "Regra especial",
    frequencia: classificarFrequencia(chanceMaxima),
    origemEspecial,
  };

  estrutura.descricao = gerarDescricaoEstrutura(estrutura, biomas);
  return estrutura;
}

function montarBiomas(biomasToml) {
  return Object.entries(biomasToml.biomes ?? {}).map(([codigo, cfg]) => {
    const objetos = Object.entries(cfg.objects ?? {})
      .filter(([, chance]) => (numero(chance) ?? 0) > 0)
      .sort((a, b) => (numero(b[1]) ?? 0) - (numero(a[1]) ?? 0));

    return {
      codigo,
      nome: ROTULOS_BIOMAS[codigo] ?? codigo,
      descricao: DESCRICOES_BIOMAS[codigo] ?? "Bioma configurado nas regras de geração do mundo.",
      pesoTexto: formatarNumero(cfg.weight),
      tileBase: ROTULOS_TILES[cfg.base_tile] ?? cfg.base_tile ?? "-",
      tileCosta: ROTULOS_TILES[cfg.coast_tile] ?? cfg.coast_tile ?? "-",
      objetosAtivos: objetos.length,
      principaisObjetos: objetos.slice(0, 4).map(([objeto]) => objeto),
    };
  });
}

function carregarRegrasMundo() {
  return {
    estruturas: carregarToml(NOMES_REGRAS.estruturas, "regras de estruturas naturais"),
    biomas: carregarToml(NOMES_REGRAS.biomas, "regras de biomas"),
    terreno: carregarToml(NOMES_REGRAS.terreno, "regras de terreno"),
  };
}

export function carregarWikiMundo() {
  const regras = carregarRegrasMundo();
  const estruturas = Object.entries(regras.estruturas.tipos ?? {})
    .map((entrada) => montarEstrutura(entrada, regras.biomas))
    .sort((a, b) => a.ordem - b.ordem);
  const biomas = montarBiomas(regras.biomas);
  const mundo = regras.terreno.world ?? {};
  const pois = regras.terreno.pois ?? {};
  const variacao = regras.estruturas.variacao ?? {};

  return {
    estruturas,
    biomas,
    resumo: {
      estruturas: estruturas.length,
      categorias: new Set(estruturas.map((estrutura) => estrutura.categoria)).size,
      biomas: biomas.length,
      largura: numero(mundo.width) ?? 10000,
      altura: numero(mundo.height) ?? 10000,
      chunk: numero(mundo.chunk_size) ?? 10,
      estadios: numero(pois.gym?.count) ?? 0,
      dungeons: numero(pois.dungeon?.count) ?? 0,
      vilas: numero(pois.village?.count) ?? 0,
      escalaMin: numero(variacao.escala_min),
      escalaMax: numero(variacao.escala_max),
      totalVariantes: numero(variacao.total_variantes) ?? 0,
    },
  };
}

export function indexarImagensMundo(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const nomeArquivo = arquivoSemExtensao(caminho);
    const chaveArquivo = normalizarChave(nomeArquivo);
    if (chaveArquivo && !indice[chaveArquivo]) indice[chaveArquivo] = url;
  });
  return indice;
}

function candidatosImagemEstrutura(estrutura) {
  return [
    estrutura.spriteArquivo,
    estrutura.nome,
    estrutura.subtipo,
    estrutura.slug,
    estrutura.nome?.replace(/\s+/g, "_"),
    estrutura.nome?.replace(/\s+/g, "-"),
    estrutura.id,
  ].filter(Boolean).map(normalizarChave);
}

export function resolverImagemEstrutura(estrutura, imagensPorNome) {
  for (const candidato of candidatosImagemEstrutura(estrutura)) {
    if (imagensPorNome[candidato]) return imagensPorNome[candidato];
  }
  return null;
}

export function criarAssetsEstruturas(estruturas, imagensPorNome) {
  return Object.fromEntries(estruturas.map((estrutura) => [estrutura.id, { imagem: resolverImagemEstrutura(estrutura, imagensPorNome) }]));
}
