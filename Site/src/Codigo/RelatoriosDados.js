import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const NOMES_PASTAS_RELATORIOS = [
  "Documentação/Relatorios/Registros",
  "Documentação/Relatorios/Readmes",
  "Documentação/Relatorios",
  "Relatorios",
  "Relatórios",
];

function diretorioModulo() {
  try {
    return path.dirname(fileURLToPath(import.meta.url));
  } catch {
    return process.cwd();
  }
}

function subirAteRaizRepositorio(inicio) {
  let atual = path.resolve(inicio || process.cwd());
  for (let i = 0; i < 10; i += 1) {
    if (existsSync(path.join(atual, "Registro.md")) || existsSync(path.join(atual, "Site"))) return atual;
    const pai = path.dirname(atual);
    if (pai === atual) break;
    atual = pai;
  }
  return path.resolve(process.cwd(), "..");
}

function raizRepositorio() {
  const candidatos = [
    subirAteRaizRepositorio(process.cwd()),
    subirAteRaizRepositorio(diretorioModulo()),
    path.resolve(process.cwd(), ".."),
  ];
  for (const candidato of candidatos) {
    try {
      if (existsSync(candidato) && statSync(candidato).isDirectory()) return candidato;
    } catch {
      // ignora candidato inválido
    }
  }
  return candidatos[0];
}

function escaparHtml(valor) {
  return String(valor ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#039;",
    '"': "&quot;",
  })[char]);
}

function inlineMarkdown(valor) {
  return escaparHtml(valor)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}

function caminhoImagemRelatorio(valor) {
  const normalizado = String(valor || "").replace(/\\/g, "/");
  const prefixoPublic = "Site/public/";
  if (normalizado.startsWith(prefixoPublic)) return `/${normalizado.slice(prefixoPublic.length)}`;
  return normalizado;
}

function tabelaMarkdown(bloco) {
  const linhas = bloco.map((linha) => linha.trim()).filter(Boolean);
  if (linhas.length < 2) return null;
  const separador = /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(linhas[1]);
  if (!separador) return null;
  const celulas = (linha) => linha.replace(/^\|/, "").replace(/\|$/, "").split("|").map((item) => inlineMarkdown(item.trim()));
  const cabecalho = celulas(linhas[0]);
  const corpo = linhas.slice(2).map(celulas);
  return `<div class="relatorio-tabela-wrap"><table><thead><tr>${cabecalho.map((item) => `<th>${item}</th>`).join("")}</tr></thead><tbody>${corpo.map((linha) => `<tr>${linha.map((item) => `<td>${item}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

export function markdownParaHtml(markdown) {
  const linhas = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const saida = [];
  let paragrafo = [];
  let lista = [];
  let codigo = [];
  let emCodigo = false;

  const fecharParagrafo = () => {
    if (!paragrafo.length) return;
    saida.push(`<p>${inlineMarkdown(paragrafo.join(" "))}</p>`);
    paragrafo = [];
  };
  const fecharLista = () => {
    if (!lista.length) return;
    saida.push(`<ul>${lista.map((item) => `<li>${inlineMarkdown(item)}</li>`).join("")}</ul>`);
    lista = [];
  };

  for (let i = 0; i < linhas.length; i += 1) {
    const linhaOriginal = linhas[i];
    const linha = linhaOriginal.trimEnd();
    if (linha.trim().startsWith("```")) {
      if (emCodigo) {
        saida.push(`<pre><code>${escaparHtml(codigo.join("\n"))}</code></pre>`);
        codigo = [];
        emCodigo = false;
      } else {
        fecharParagrafo();
        fecharLista();
        emCodigo = true;
      }
      continue;
    }
    if (emCodigo) {
      codigo.push(linhaOriginal);
      continue;
    }

    if (!linha.trim()) {
      fecharParagrafo();
      fecharLista();
      continue;
    }

    const imagem = linha.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (imagem) {
      fecharParagrafo();
      fecharLista();
      const alt = escaparHtml(imagem[1] || "");
      const src = escaparHtml(caminhoImagemRelatorio(imagem[2]));
      saida.push(`<figure class="relatorio-figura"><img src="${src}" alt="${alt}" loading="lazy"></figure>`);
      continue;
    }

    if (linha.includes("|") && i + 1 < linhas.length && linhas[i + 1].includes("|")) {
      const bloco = [];
      let j = i;
      while (j < linhas.length && linhas[j].includes("|") && linhas[j].trim()) {
        bloco.push(linhas[j]);
        j += 1;
      }
      const tabela = tabelaMarkdown(bloco);
      if (tabela) {
        fecharParagrafo();
        fecharLista();
        saida.push(tabela);
        i = j - 1;
        continue;
      }
    }

    const heading = linha.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      fecharParagrafo();
      fecharLista();
      const nivel = Math.min(heading[1].length + 1, 5);
      saida.push(`<h${nivel}>${inlineMarkdown(heading[2])}</h${nivel}>`);
      continue;
    }
    const itemLista = linha.match(/^[-*]\s+(.+)$/);
    if (itemLista) {
      fecharParagrafo();
      lista.push(itemLista[1]);
      continue;
    }
    if (linha.startsWith(">")) {
      fecharParagrafo();
      fecharLista();
      saida.push(`<blockquote>${inlineMarkdown(linha.replace(/^>\s?/, ""))}</blockquote>`);
      continue;
    }
    paragrafo.push(linha.trim());
  }

  fecharParagrafo();
  fecharLista();
  if (codigo.length) saida.push(`<pre><code>${escaparHtml(codigo.join("\n"))}</code></pre>`);
  return saida.join("\n");
}

function lerRelatorio(caminho, tituloPadrao, atual = false) {
  const markdown = readFileSync(caminho, "utf8");
  const primeiroTitulo = markdown.match(/^#\s+(.+)$/m)?.[1]?.trim();
  const stat = statSync(caminho);
  return {
    id: path.basename(caminho).replace(/\.md$/i, "").toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    titulo: primeiroTitulo || tituloPadrao,
    arquivo: path.basename(caminho),
    atual,
    atualizadoEm: stat.mtime.toISOString(),
    markdown,
    html: markdownParaHtml(markdown),
  };
}

export function carregarRelatorios() {
  const raiz = raizRepositorio();
  const relatorios = [];
  const registroAtual = path.join(raiz, "Registro.md");
  if (existsSync(registroAtual)) relatorios.push(lerRelatorio(registroAtual, "Registro atual", true));

  for (const nomePasta of NOMES_PASTAS_RELATORIOS) {
    const pasta = path.join(raiz, nomePasta);
    if (!existsSync(pasta)) continue;
    let entradas = [];
    try {
      entradas = readdirSync(pasta, { withFileTypes: true });
    } catch {
      continue;
    }
    entradas
      .filter((entrada) => entrada.isFile() && entrada.name.toLowerCase().endsWith(".md"))
      .map((entrada) => path.join(pasta, entrada.name))
      .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs)
      .forEach((caminho) => relatorios.push(lerRelatorio(caminho, path.basename(caminho, ".md"), false)));
  }

  if (!relatorios.length) {
    const markdown = "# Registro não encontrado\n\nO arquivo `Registro.md` ainda não foi localizado na raiz do repositório durante o build do site.";
    return [{ id: "sem-registro", titulo: "Registro não encontrado", arquivo: "Registro.md", atual: true, atualizadoEm: "", markdown, html: markdownParaHtml(markdown) }];
  }

  const usados = new Map();
  relatorios.forEach((relatorio) => {
    const base = relatorio.id || "relatorio";
    const repeticao = usados.get(base) || 0;
    usados.set(base, repeticao + 1);
    relatorio.id = repeticao ? `${base}-${repeticao + 1}` : base;
  });

  return relatorios;
}
