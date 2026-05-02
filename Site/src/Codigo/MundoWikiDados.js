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
  pedra_dungeon: "DUNGEON_ROCK",
};

const OBJETO_PARA_SUBTIPO = Object.fromEntries(Object.entries(SUBTIPO_PARA_OBJETO).map(([subtipo, objeto]) => [objeto, subtipo]));

const DESCRICOES_BIOMAS = {
  FIELD: "Área aberta e equilibrada, boa para início de exploração. Costuma misturar vegetação, pedra e minérios básicos.",
  FOREST: "Ambiente mais fechado, com muita presença de árvores, arbustos, flores e plantas naturais.",
  DESERT: "Região seca e quente, marcada por areia, palmeiras, cactos e recursos próprios do deserto.",
  SNOW: "Área fria, com pinheiros e recursos raros ligados a regiões congeladas.",
  MAGIC: "Região mais incomum, com solo mágico, vegetação viva e recursos especiais do ambiente.",
  VOLCANIC: "Área quente e pesada, com rocha vulcânica, lava e minerais associados a calor intenso.",
  SWAMP: "Região úmida e densa, com solo pantanoso, vegetação resistente e recursos próprios do pântano.",
};

const DESCRICOES_ESTRUTURAS = {
  arvore: "Árvores aparecem em áreas naturais e ajudam a formar a base visual do mundo. Também servem como fonte simples de madeira para o jogador.",
  arvore_trombosa: "Árvore Trombosa é uma variação mais marcante de árvore, usada para deixar florestas mais reconhecíveis e menos repetitivas.",
  pedra: "Pedras aparecem em vários ambientes terrestres e são um dos recursos básicos da exploração.",
  arbusto: "Arbustos preenchem áreas naturais e ajudam a deixar o terreno mais vivo sem ocupar o papel principal das árvores.",
  palmeira: "Palmeiras reforçam a identidade de regiões quentes e secas, principalmente em áreas de deserto.",
  pinheiro: "Pinheiros combinam com regiões frias e ajudam o jogador a reconhecer áreas de neve durante a exploração.",
  cacto: "Cactos são estruturas típicas do deserto e dão mais identidade às áreas secas do mapa.",
  lava: "Lava aparece em regiões vulcânicas e funciona como uma estrutura ambiental especial, com presença visual mais forte que minérios comuns.",
  concha: "Conchas aparecem em áreas de costa e ajudam a marcar a transição entre terra e água.",
  aquamarine: "Aquamarine é um recurso associado à água profunda, valorizando a exploração fora dos biomas terrestres comuns.",
  casa: "Casas fazem parte da geração das vilas. Elas representam civilização e não devem ser tratadas como um recurso natural comum.",
  pedra_dungeon: "Pedra Dungeon compõe áreas de dungeon e ajuda a separar visualmente esses ambientes do restante do mundo.",
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
  return Number.isFinite(convertido) ? convertido : texto;
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
    secaoAtual[linha.slice(0, igual).trim()] = parseTomlValue(linha.slice(igual + 1).trim());
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
  return parseToml(readFileSync(caminho, "utf8").replace(/^\uFEFF/, ""));
}

function arquivoSemExtensao(caminho) {
  const arquivo = caminho.split(/[\\/]/).pop() ?? caminho;
  return arquivo.replace(/\.[^.]+$/, "");
}

function rotuloEstilo(valor) {
  const chave = normalizarChave(valor);
  const rotulos = { machado: "Machado", picareta: "Picareta", balde: "Balde", nenhum: "Nenhum" };
  return rotulos[chave] ?? (limparTexto(valor) || "Não informado");
}

function formatarNumero(valor, casas = 2) {
  const n = numero(valor);
  if (n === null) return "-";
  return n.toLocaleString("pt-BR", { maximumFractionDigits: casas });
}

function textoLista(lista, vazio = "Não informado") {
  return Array.isArray(lista) && lista.length ? lista.join(", ") : vazio;
}

function biomasDaEstrutura(subtipo, biomasToml) {
  const objeto = SUBTIPO_PARA_OBJETO[subtipo];
  if (!objeto) return [];

  return Object.entries(biomasToml.biomes ?? {})
    .map(([codigo, cfg]) => ({
      codigo,
      nome: ROTULOS_BIOMAS[codigo] ?? codigo,
      tile: ROTULOS_TILES[cfg.base_tile] ?? cfg.base_tile ?? "Terreno",
      chance: numero(cfg?.objects?.[objeto]) ?? 0,
    }))
    .filter((bioma) => bioma.chance > 0)
    .sort((a, b) => b.chance - a.chance || a.nome.localeCompare(b.nome, "pt-BR"))
    .map(({ chance, ...bioma }) => bioma);
}

function gerarDescricaoEstrutura(estrutura) {
  if (DESCRICOES_ESTRUTURAS[estrutura.subtipo]) return DESCRICOES_ESTRUTURAS[estrutura.subtipo];

  const locais = estrutura.biomasTexto;
  if (estrutura.material !== "Sem material") {
    return `${estrutura.nome} aparece em ${locais} e pode ser consultada nesta wiki como uma estrutura do mundo ligada ao material ${estrutura.material}.`;
  }
  return `${estrutura.nome} aparece em ${locais} e funciona como uma estrutura de ambiente dentro das regras atuais do mundo.`;
}

function montarEstrutura([codigo, cfg], biomasToml) {
  const subtipo = limparTexto(cfg.subtipo) || `estrutura_${codigo}`;
  const biomas = biomasDaEstrutura(subtipo, biomasToml);
  const origemEspecial = subtipo === "aquamarine" ? "Água profunda" : subtipo === "casa" ? "Vilas" : subtipo === "pedra_dungeon" ? "Dungeons" : "Geração especial";
  const dropAtivo = cfg.drop_ativo === undefined ? true : Boolean(cfg.drop_ativo);
  const material = limparTexto(cfg.material) || "Sem material";

  const estrutura = {
    id: String(codigo),
    ordem: numero(codigo) ?? 9999,
    nome: limparTexto(cfg.nome) || `Estrutura ${codigo}`,
    subtipo,
    slug: normalizarChave(cfg.nome || subtipo),
    sprite: limparTexto(cfg.sprite),
    spriteArquivo: arquivoSemExtensao(cfg.sprite || ""),
    material,
    ferramenta: rotuloEstilo(cfg.estilo),
    durezaTexto: formatarNumero(cfg.dureza, 0),
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
    origemEspecial,
  };

  estrutura.descricao = gerarDescricaoEstrutura(estrutura);
  return estrutura;
}

function montarMapaEstruturasPorObjeto(estruturasToml) {
  return Object.fromEntries(Object.entries(estruturasToml.tipos ?? {}).map(([, cfg]) => [SUBTIPO_PARA_OBJETO[cfg.subtipo] ?? cfg.subtipo, limparTexto(cfg.nome)]));
}

function montarBiomas(biomasToml, estruturasPorObjeto) {
  return Object.entries(biomasToml.biomes ?? {}).map(([codigo, cfg]) => {
    const objetos = Object.entries(cfg.objects ?? {})
      .filter(([, chance]) => (numero(chance) ?? 0) > 0)
      .sort((a, b) => (numero(b[1]) ?? 0) - (numero(a[1]) ?? 0))
      .map(([objeto]) => estruturasPorObjeto[objeto] || OBJETO_PARA_SUBTIPO[objeto] || objeto);

    return {
      codigo,
      nome: ROTULOS_BIOMAS[codigo] ?? codigo,
      descricao: DESCRICOES_BIOMAS[codigo] ?? "Bioma configurado nas regras de geração do mundo.",
      tileBase: ROTULOS_TILES[cfg.base_tile] ?? cfg.base_tile ?? "-",
      tileCosta: ROTULOS_TILES[cfg.coast_tile] ?? cfg.coast_tile ?? "-",
      principaisEstruturas: objetos.slice(0, 5),
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
  const estruturasPorObjeto = montarMapaEstruturasPorObjeto(regras.estruturas);
  const biomas = montarBiomas(regras.biomas, estruturasPorObjeto);
  const mundo = regras.terreno.world ?? {};

  return {
    estruturas,
    biomas,
    resumo: {
      estruturas: estruturas.length,
      biomas: biomas.length,
      largura: numero(mundo.width) ?? 10000,
      altura: numero(mundo.height) ?? 10000,
    },
  };
}

export function indexarImagensMundo(glob) {
  const indice = {};
  Object.entries(glob).forEach(([caminho, url]) => {
    const chaveArquivo = normalizarChave(arquivoSemExtensao(caminho));
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
