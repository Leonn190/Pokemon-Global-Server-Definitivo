import { html, lerJson, normalizar } from "./WikiRuntimeBase.js";
import { rotaSite } from "./RotasSite.js";

const LIMITE_RESULTADOS = 80;

function tokensBusca(valor) {
  return String(valor ?? "")
    .split(/\s+/)
    .map(normalizar)
    .filter(Boolean);
}

function pontuar(item, consulta, tokens) {
  let score = 0;
  if (item.tituloBusca === consulta) score += 120;
  if (item.tituloBusca?.startsWith(consulta)) score += 72;
  if (item.tituloBusca?.includes(consulta)) score += 44;
  if (normalizar(item.secao) === consulta) score += 28;
  if (normalizar(item.tipo).includes(consulta)) score += 18;
  tokens.forEach((token) => {
    if (item.tituloBusca?.includes(token)) score += 12;
    if (normalizar(item.meta).includes(token)) score += 5;
    if (normalizar(item.tipo).includes(token)) score += 4;
  });
  return score;
}

function buscar(itens, valor) {
  const consulta = normalizar(valor);
  const tokens = tokensBusca(valor);
  if (!consulta || !tokens.length) return [];
  return (itens || [])
    .filter((item) => tokens.every((token) => item.busca?.includes(token)))
    .map((item) => ({ item, score: pontuar(item, consulta, tokens) }))
    .sort((a, b) => b.score - a.score || a.item.ordem - b.item.ordem)
    .map(({ item }) => item);
}

function criarResultadoCard(item) {
  const card = document.createElement("a");
  card.className = "wiki-busca-card";
  card.href = rotaSite(item.href || "/wiki");
  card.innerHTML = `
    <span class="wiki-busca-card-emoji" aria-hidden="true">${html(item.emoji || "✨")}</span>
    <span class="wiki-busca-card-corpo">
      <span class="wiki-busca-card-topo">
        <strong>${html(item.titulo)}</strong>
        <em>${html(item.secao)}</em>
      </span>
      <span class="wiki-busca-card-meta">${html(item.tipo)}${item.codigo ? ` • ${html(item.codigo)}` : ""} • ${html(item.meta)}</span>
      ${item.descricao ? `<span class="wiki-busca-card-descricao">${html(item.descricao)}</span>` : ""}
    </span>
  `;
  return card;
}

export function inicializarBuscaGlobalWiki(idDados = "wiki-global-search-data") {
  const dados = lerJson(idDados, "Busca global da wiki");
  const raiz = document.querySelector("[data-wiki-global-search-root]");
  if (!dados || !raiz) return;
  const input = raiz.querySelector("[data-wiki-global-search]");
  const secoes = document.querySelector("[data-wiki-menu-secoes]");
  const resultadosSecao = document.querySelector("[data-wiki-global-results-section]");
  const resultadosGrid = document.querySelector("[data-wiki-global-results]");
  const vazio = document.querySelector("[data-wiki-global-empty]");
  const status = raiz.querySelector("[data-wiki-global-status]");
  const itens = Array.isArray(dados.itens) ? dados.itens : [];
  let renderId = 0;

  function atualizar() {
    const termo = input?.value?.trim() ?? "";
    const ativo = termo.length > 0;
    const idAtual = ++renderId;
    const resultados = ativo ? buscar(itens, termo) : [];
    if (secoes) secoes.hidden = ativo;
    if (resultadosSecao) resultadosSecao.hidden = !ativo;
    if (vazio) vazio.hidden = !ativo || resultados.length > 0;
    if (status) {
      status.textContent = ativo
        ? `${resultados.length} resultado${resultados.length === 1 ? "" : "s"} encontrado${resultados.length === 1 ? "" : "s"}.`
        : `${itens.length} entradas indexadas para busca rápida.`;
    }
    if (!resultadosGrid) return;
    resultadosGrid.replaceChildren();
    if (!ativo || !resultados.length) return;
    window.requestAnimationFrame(() => {
      if (idAtual !== renderId) return;
      const fragmento = document.createDocumentFragment();
      resultados.slice(0, LIMITE_RESULTADOS).forEach((item) => fragmento.appendChild(criarResultadoCard(item)));
      resultadosGrid.appendChild(fragmento);
    });
  }

  input?.addEventListener("input", atualizar);
  atualizar();
}
