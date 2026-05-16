import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { normalizarChave } from "./PokemonWikiDados.js";

const NOMES_REGRAS_SKILLS = ["Skils.toml", "Skills.toml", "Habilidades.toml"];
const RAMOS_ROTULOS = {
  fisico: "Físico",
  tecnicas: "Técnicas",
  armazenamento: "Armazenamento",
};
const RAMOS_DADOS = {
  esquerda: "Rota esquerda",
  centro: "Rota central",
  direita: "Rota direita",
};
const GRUPOS_ARMAZENAMENTO = new Set(["mochila", "slots", "pokemons", "times", "conhecimento", "acumulador"]);
const EMOJIS_GRUPOS_FIXOS = {
  velocista: "🏃",
  corredor: "💨",
  acelerador: "⚡",
  pulmao: "🫁",
  respirador: "🌬️",
  nadador: "🏊",
  forca: "💪",
  combate: "🥊",
  tapa: "👊",
  maestria: "🎯",
  captura: "🧲",
  dungeon: "🗺️",
  coracoes: "❤️",
  mochila: "🎒",
  slots: "🧩",
  pokemons: "🐾",
  times: "👥",
  conhecimento: "📚",
  acumulador: "🧪",
};
const EMOJIS_GRUPOS_FALLBACK = ["✨", "🌟", "🔹", "🔸", "🔮", "🧬", "🛠️", "🪄", "🌀", "💎", "🧭", "🔥", "🌊", "🌿", "🪨", "⚙️", "🧠", "🛡️", "🚀", "🎲"];

function limparTexto(valor) {
  return String(valor ?? "").trim();
}

function diretorioAtual() {
  return path.dirname(fileURLToPath(import.meta.url));
}

function caminhosRegraSkills() {
  const atual = diretorioAtual();
  return NOMES_REGRAS_SKILLS.flatMap((nome) => [
    path.resolve(atual, "../../../Dados/Regras", nome),
    path.resolve(atual, "../../Dados/Regras", nome),
    path.resolve(process.cwd(), "../Dados/Regras", nome),
    path.resolve(process.cwd(), "Dados/Regras", nome),
    path.resolve(process.cwd(), "../Pokemon-Global-Server-Definitivo/Dados/Regras", nome),
  ]);
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

function dividirForaDeEstruturas(texto, separador = ",") {
  const partes = [];
  let atual = "";
  let aspas = false;
  let nivelColchete = 0;
  let nivelChave = 0;
  for (let i = 0; i < texto.length; i += 1) {
    const char = texto[i];
    if (char === '"' && texto[i - 1] !== "\\") aspas = !aspas;
    if (!aspas) {
      if (char === "[") nivelColchete += 1;
      if (char === "]") nivelColchete -= 1;
      if (char === "{") nivelChave += 1;
      if (char === "}") nivelChave -= 1;
      if (char === separador && nivelColchete === 0 && nivelChave === 0) {
        partes.push(atual.trim());
        atual = "";
        continue;
      }
    }
    atual += char;
  }
  if (atual.trim()) partes.push(atual.trim());
  return partes;
}

function separarSecao(secao) {
  return dividirForaDeEstruturas(secao, ".").map((parte) => parte.replace(/^"|"$/g, "").trim()).filter(Boolean);
}

function parseTomlValor(valor) {
  const texto = limparTexto(valor);
  if (!texto) return "";
  if (texto.startsWith('"') && texto.endsWith('"')) return texto.slice(1, -1).replace(/\\"/g, '"');
  if (texto === "true") return true;
  if (texto === "false") return false;
  if (texto.startsWith("[") && texto.endsWith("]")) {
    const miolo = texto.slice(1, -1).trim();
    if (!miolo) return [];
    return dividirForaDeEstruturas(miolo).map(parseTomlValor);
  }
  if (texto.startsWith("{") && texto.endsWith("}")) {
    const obj = {};
    const miolo = texto.slice(1, -1).trim();
    if (!miolo) return obj;
    dividirForaDeEstruturas(miolo).forEach((par) => {
      const igual = par.indexOf("=");
      if (igual === -1) return;
      const chave = par.slice(0, igual).trim().replace(/^"|"$/g, "");
      obj[chave] = parseTomlValor(par.slice(igual + 1));
    });
    return obj;
  }
  const numero = Number(texto.replace(",", "."));
  if (Number.isFinite(numero)) return numero;
  return texto;
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
        if (!alvo[parte] || typeof alvo[parte] !== "object") alvo[parte] = {};
        alvo = alvo[parte];
      });
      return;
    }
    const igual = linha.indexOf("=");
    if (igual === -1) return;
    const chave = linha.slice(0, igual).trim();
    alvo[chave] = parseTomlValor(linha.slice(igual + 1));
  });
  return raiz;
}

function lerRegrasSkills() {
  const caminhos = caminhosRegraSkills();
  const caminho = caminhos.find((item) => existsSync(item));
  if (!caminho) {
    console.warn(`[Wiki Habilidades] Regra de skills não encontrada. Procurei por: ${caminhos.join(" | ")}`);
    return {};
  }
  try {
    return parseToml(readFileSync(caminho, "utf8").replace(/^\uFEFF/, ""));
  } catch (erro) {
    console.warn(`[Wiki Habilidades] Falha ao ler ${caminho}: ${erro}`);
    return {};
  }
}

function listaTexto(valor) {
  if (Array.isArray(valor)) return valor.map(limparTexto).filter(Boolean);
  if (valor === null || valor === undefined || valor === "") return [];
  return [limparTexto(valor)].filter(Boolean);
}

function formatarValor(valor) {
  if (typeof valor === "boolean") return valor ? "Sim" : "Não";
  if (typeof valor === "number") return Number.isInteger(valor) ? String(valor) : valor.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
  return limparTexto(valor);
}

function formatarEfeitos(efeitos) {
  if (!efeitos || typeof efeitos !== "object") return [];
  return Object.entries(efeitos).map(([chave, valor]) => ({
    chave,
    valor,
    texto: `${chave}: ${formatarValor(valor)}`,
  }));
}

function nivelPorSkill(id, skill) {
  const candidatos = [skill?.nivel, limparTexto(skill?.sigla).match(/(\d+)$/)?.[1], limparTexto(id).match(/_(\d+)$/)?.[1]];
  for (const candidato of candidatos) {
    const numero = Number(candidato);
    if (Number.isFinite(numero) && numero > 0) return Math.trunc(numero);
  }
  return 1;
}

function categoriaRamo(skill) {
  const ramo = normalizarChave(skill?.ramo || "");
  const grupo = normalizarChave(skill?.grupo || "");
  if (ramo === "centro") return "tecnicas";
  if (GRUPOS_ARMAZENAMENTO.has(grupo)) return "armazenamento";
  return "fisico";
}

function idCatalogoSkill(skill, indice) {
  const bruto = skill?.id ?? skill?.ID ?? skill?.Id;
  const texto = limparTexto(bruto);
  return texto || String(indice + 1);
}

function emojiFallbackGrupo(grupo) {
  const chave = normalizarChave(grupo || "geral");
  const soma = [...chave].reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return EMOJIS_GRUPOS_FALLBACK[soma % EMOJIS_GRUPOS_FALLBACK.length];
}

function normalizarSkill([id, skill], indice) {
  const nome = limparTexto(skill?.nome) || id;
  const codigo = idCatalogoSkill(skill, indice);
  const grupo = limparTexto(skill?.grupo) || "geral";
  const grupoChave = normalizarChave(grupo || "geral");
  const grupoRotulo = grupo.replace(/_/g, " ").replace(/^./, (letra) => letra.toUpperCase());
  const ramoDado = normalizarChave(skill?.ramo || "");
  const categoria = categoriaRamo(skill);
  const pais = listaTexto(skill?.pais);
  const efeitos = formatarEfeitos(skill?.efeitos);
  const nivel = nivelPorSkill(id, skill);
  const sigla = limparTexto(skill?.sigla) || `${grupo.slice(0, 1).toUpperCase()}${nivel}`;
  const descricao = limparTexto(skill?.descricao) || "Habilidade cadastrada na regra de skills.";
  const grupoEmoji = EMOJIS_GRUPOS_FIXOS[grupoChave] ?? emojiFallbackGrupo(grupoChave);
  return {
    id: codigo,
    codigo,
    chave: id,
    ordem: indice + 1,
    nome,
    sigla,
    grupo,
    grupoChave,
    grupoRotulo,
    grupoEmoji,
    ramoDado,
    rotaRotulo: RAMOS_DADOS[ramoDado] ?? "Rota não definida",
    ramo: categoria,
    ramoRotulo: RAMOS_ROTULOS[categoria] ?? "Habilidade",
    nivel,
    pais,
    descricao,
    efeitos,
    busca: normalizarChave(`${codigo} ${id} ${nome} ${sigla} ${grupo} ${grupoRotulo} ${ramoDado} ${RAMOS_DADOS[ramoDado] ?? ""} ${categoria} ${RAMOS_ROTULOS[categoria] ?? ""} ${nivel} ${pais.join(" ")} ${descricao} ${efeitos.map((e) => e.texto).join(" ")}`),
  };
}

export function carregarHabilidades() {
  const dados = lerRegrasSkills();
  const skills = dados?.skills && typeof dados.skills === "object" ? dados.skills : {};
  return Object.entries(skills).map(normalizarSkill);
}

export function carregarMetaHabilidades() {
  const dados = lerRegrasSkills();
  return dados?.meta && typeof dados.meta === "object" ? dados.meta : {};
}

export function resumoHabilidades(habilidades) {
  const ramos = ["fisico", "tecnicas", "armazenamento"]
    .filter((chave) => habilidades.some((skill) => skill.ramo === chave))
    .map((chave) => ({ chave, rotulo: RAMOS_ROTULOS[chave] }));
  const niveis = [...new Set(habilidades.map((skill) => skill.nivel))]
    .sort((a, b) => a - b)
    .map((nivel) => ({ chave: String(nivel), rotulo: `Nível ${nivel}` }));
  const grupos = [...new Set(habilidades.map((skill) => skill.grupoRotulo))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  return {
    quantidade: habilidades.length,
    ramos,
    niveis,
    grupos,
    fisico: habilidades.filter((skill) => skill.ramo === "fisico").length,
    tecnicas: habilidades.filter((skill) => skill.ramo === "tecnicas").length,
    armazenamento: habilidades.filter((skill) => skill.ramo === "armazenamento").length,
  };
}
