import { formatarNumero, html, lerJson, normalizar } from "./WikiRuntimeBase.js";
import { rotaSite } from "./RotasSite.js";

const LIMITE_RESULTADOS = 80;
let faixaGlobalTocando = null;

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

function linkResultado(item, classe) {
  const card = document.createElement("a");
  card.className = `${classe} wiki-busca-card-existente`;
  card.href = rotaSite(item.href || "/wiki");
  card.setAttribute("aria-label", `Abrir ${item.secao}: ${item.titulo}`);
  return card;
}

function imagemOuFallback(card, arteClasse = "item-card-arte") {
  const fallbackClasse = card.fallbackClasse || "item-card-sem-arte";
  return `
    <span class="${html(arteClasse)}">
      ${card.imagem
        ? `<img src="${html(card.imagem)}" alt="${html(card.nome)}" loading="lazy" decoding="async" />`
        : `<span class="${html(fallbackClasse)}">${html(String(card.fallback || card.nome || "?").slice(0, 2))}</span>`}
    </span>
  `;
}

function tipoBolinhaHtml(tipo) {
  const chance = Number(tipo?.chance);
  const classeChance = Number.isFinite(chance) ? (chance > 50 ? "chance-ouro" : chance === 50 ? "chance-prata" : "chance-bronze") : "chance-neutra";
  return `<span class="tipo-bola pequena ${classeChance}" data-tipo="${html(tipo?.chave || normalizar(tipo?.nome))}" title="${html(tipo?.nome || "Tipo")}">
    ${tipo?.icone ? `<img src="${html(tipo.icone)}" alt="${html(tipo.nome)}" loading="lazy" decoding="async" />` : `<b>${html(String(tipo?.nome || "?").slice(0, 1))}</b>`}
  </span>`;
}

function tipoAfinidadeHtml(afinidade) {
  if (!afinidade?.nome) return "";
  return `${tipoBolinhaHtml(afinidade)}${html(afinidade.nome)}`;
}

function criarCardPokemon(item) {
  const card = item.card || {};
  const elemento = linkResultado(item, `pokemon-card ${card.radiante ? "pokemon-radiante" : ""}`.trim());
  elemento.innerHTML = `
    <span class="pokemon-card-codigo">${html(card.codigo || item.codigo || "")}</span>
    <span class="pokemon-card-arte">
      ${card.imagem
        ? `<img class="${card.radiante ? "sprite-radiante" : ""}" src="${html(card.imagem)}" alt="${html(card.nome || item.titulo)}" loading="lazy" decoding="async" />`
        : `<span class="pokemon-card-sem-arte">${html(String(card.fallback || item.titulo || "P").slice(0, 1))}</span>`}
    </span>
    <span class="pokemon-card-nome">${html(card.nome || item.titulo)}</span>
    ${card.meta ? `<span class="pokemon-card-meta">${html(card.meta)}</span>` : ""}
    <span class="pokemon-card-tipos">${(card.tipos || []).map(tipoBolinhaHtml).join("")}</span>
    <span class="pokemon-card-poder"><strong>${formatarNumero(card.poder)}</strong><small>Poder total</small></span>
  `;
  return elemento;
}

function valorLinha(valor) {
  if (valor === null || valor === undefined || valor === "") return "-";
  return Number.isNaN(Number(valor)) ? String(valor) : formatarNumero(valor);
}

function criarCardItem(item) {
  const card = item.card || {};
  const elemento = linkResultado(item, card.classe || "item-card");
  const linha = card.linhaRotulo || card.linhaValor !== undefined
    ? `<span class="item-card-linha"><strong>${html(valorLinha(card.linhaValor))}</strong><small>${html(card.linhaRotulo || "Info")}</small></span>`
    : "";
  const meta = card.afinidade
    ? `<span class="${html(card.metaClasse || "item-card-meta")}">${tipoAfinidadeHtml(card.afinidade)}</span>`
    : card.meta
      ? `<span class="${html(card.metaClasse || "item-card-meta")}">${html(card.meta)}</span>`
      : "";
  const pill = card.pillTexto ? `<span class="raridade-pill ${html(card.pillClasse || "")}">${html(card.pillTexto)}</span>` : "";
  elemento.innerHTML = `
    ${card.codigo ? `<span class="item-card-codigo">${html(card.codigo)}</span>` : ""}
    ${imagemOuFallback(card, card.arteClasse || "item-card-arte")}
    <span class="item-card-nome">${html(card.nome || item.titulo)}</span>
    ${meta}
    ${linha}
    ${pill}
  `;
  return elemento;
}

function criarCardBioma(item) {
  const card = item.card || {};
  const elemento = linkResultado(item, "mundo-bioma-card wiki-busca-bioma-card");
  elemento.innerHTML = `
    <h3>${html(card.nome || item.titulo)}</h3>
    <p>${html(card.descricao || item.descricao || "")}</p>
    ${card.tileBase ? `<div class="mundo-bioma-info"><span>Terreno principal</span><strong>${html(card.tileBase)}</strong></div>` : ""}
    <div class="mundo-bioma-estruturas">${(card.estruturas || []).map((estrutura) => `<span>${html(estrutura)}</span>`).join("")}</div>
  `;
  return elemento;
}

function formatarTempo(segundos) {
  if (!Number.isFinite(segundos) || segundos < 0) return "--:--";
  const total = Math.floor(segundos);
  const minutos = Math.floor(total / 60);
  const resto = String(total % 60).padStart(2, "0");
  return `${minutos}:${resto}`;
}

function atualizarFaixaTempo(card) {
  const audio = card.querySelector("audio");
  const barra = card.querySelector("[data-musica-progress]");
  const tempo = card.querySelector("[data-musica-tempo]");
  const duracao = Number.isFinite(audio?.duration) ? audio.duration : Number(card.dataset.duracao || NaN);
  const atual = Number.isFinite(audio?.currentTime) ? audio.currentTime : 0;
  if (barra && Number.isFinite(duracao) && duracao > 0 && !barra.matches(":active")) {
    barra.value = String(Math.round((atual / duracao) * 1000));
  }
  if (tempo) tempo.textContent = `${formatarTempo(atual)} / ${formatarTempo(duracao)}`;
}

function definirTocando(card, tocando) {
  const botao = card.querySelector("[data-musica-toggle]");
  const icone = card.querySelector("[data-musica-icone]");
  card.classList.toggle("tocando", tocando);
  if (icone) icone.textContent = tocando ? "⏸" : "▶";
  if (botao) {
    const nome = card.dataset.nome || "música";
    botao.setAttribute("aria-label", tocando ? `Pausar ${nome}` : `Tocar ${nome}`);
  }
}

function criarFaixaMusica(item) {
  const musica = item.card || {};
  const card = document.createElement("article");
  card.className = "faixa-musica wiki-busca-resultado-musica";
  card.dataset.musicaId = musica.id || item.id;
  card.dataset.nome = musica.nome || item.titulo;
  card.dataset.duracao = Number.isFinite(musica.duracao) ? String(musica.duracao) : "";
  card.innerHTML = `
    <button class="faixa-musica-botao" type="button" data-musica-toggle aria-label="Tocar ${html(musica.nome || item.titulo)}">
      <span data-musica-icone aria-hidden="true">▶</span>
    </button>
    <div class="faixa-musica-texto">
      <strong>${html(musica.nome || item.titulo)}</strong>
      <span>${html(musica.estiloRotulo || item.meta || "Música")}</span>
    </div>
    <label class="faixa-musica-barra" aria-label="Posição da música ${html(musica.nome || item.titulo)}">
      <input type="range" min="0" max="1000" value="0" step="1" data-musica-progress />
    </label>
    <time class="faixa-musica-tempo" data-musica-tempo>0:00 / ${formatarTempo(musica.duracao)}</time>
    <audio preload="none" src="${html(musica.url || "")}"></audio>
  `;
  const audio = card.querySelector("audio");
  const barra = card.querySelector("[data-musica-progress]");
  const botao = card.querySelector("[data-musica-toggle]");
  botao?.addEventListener("click", () => {
    if (!audio) return;
    if (faixaGlobalTocando && faixaGlobalTocando !== audio) faixaGlobalTocando.pause();
    if (audio.paused) {
      faixaGlobalTocando = audio;
      audio.play().catch(() => definirTocando(card, false));
    } else {
      audio.pause();
    }
  });
  audio?.addEventListener("loadedmetadata", () => {
    if (Number.isFinite(audio.duration)) {
      card.dataset.duracao = String(audio.duration);
      atualizarFaixaTempo(card);
    }
  });
  audio?.addEventListener("timeupdate", () => atualizarFaixaTempo(card));
  audio?.addEventListener("ended", () => {
    definirTocando(card, false);
    atualizarFaixaTempo(card);
  });
  audio?.addEventListener("pause", () => {
    if (faixaGlobalTocando === audio) faixaGlobalTocando = null;
    definirTocando(card, false);
  });
  audio?.addEventListener("play", () => definirTocando(card, true));
  barra?.addEventListener("input", () => {
    if (!audio || !Number.isFinite(audio.duration) || audio.duration <= 0) return;
    audio.currentTime = (Number(barra.value) / 1000) * audio.duration;
    atualizarFaixaTempo(card);
  });
  return card;
}

function criarResultadoCard(item) {
  if (item.modelo === "pokemon") return criarCardPokemon(item);
  if (item.modelo === "musica") return criarFaixaMusica(item);
  if (item.modelo === "bioma") return criarCardBioma(item);
  return criarCardItem(item);
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
        : `${itens.length} cartuchos e faixas indexados para busca rápida.`;
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
