import { abrirModalDetalhe, fecharModalDetalhe, formatarNumero, html, infoHtml, lerJson, normalizar } from "./WikiRuntimeBase.js";

const LIMITE_RESULTADOS = 80;
const CHAVE_VOLUME_GLOBAL = "pokemon-global-server-volume-musicas";
let faixaGlobalTocando = null;
let volumeGlobal = 1;

const FILTROS_WIKI = [
  "pokemons",
  "itens",
  "ataques",
  "npcs",
  "estruturas",
  "musicas",
  "habilidades",
  "comandos",
  "dungeons",
  "estadios",
];

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

function criarBotaoResultado(item, classe) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = `${classe} wiki-busca-card-existente`;
  card.dataset.resultadoId = item.id;
  card.setAttribute("aria-label", `Abrir detalhes de ${item.titulo}`);
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
  const elemento = criarBotaoResultado(item, `pokemon-card ${card.radiante ? "pokemon-radiante" : ""}`.trim());
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
  const elemento = criarBotaoResultado(item, card.classe || "item-card");
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
  const elemento = criarBotaoResultado(item, "mundo-bioma-card wiki-busca-bioma-card");
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

function limitarVolume(valor) {
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return 1;
  return Math.min(1, Math.max(0, numero));
}

function lerVolumeSalvo() {
  try {
    return limitarVolume(window.localStorage?.getItem(CHAVE_VOLUME_GLOBAL) ?? 1);
  } catch {
    return 1;
  }
}

function salvarVolume(valor) {
  try {
    window.localStorage?.setItem(CHAVE_VOLUME_GLOBAL, String(valor));
  } catch {
    // localStorage pode estar indisponível em alguns contextos.
  }
}

function aplicarVolumeGlobal(raiz = document) {
  raiz.querySelectorAll?.(".faixa-musica audio").forEach((audio) => {
    audio.volume = volumeGlobal;
  });
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
  card.dataset.resultadoId = item.id;
  card.dataset.musicaId = musica.id || item.id;
  card.dataset.nome = musica.nome || item.titulo;
  card.dataset.duracao = Number.isFinite(musica.duracao) ? String(musica.duracao) : "";
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.setAttribute("aria-label", `Abrir detalhes de ${musica.nome || item.titulo}`);
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
  if (audio) audio.volume = volumeGlobal;
  botao?.addEventListener("click", (evento) => {
    evento.stopPropagation();
    if (!audio) return;
    if (faixaGlobalTocando && faixaGlobalTocando !== audio) faixaGlobalTocando.pause();
    if (audio.paused) {
      faixaGlobalTocando = audio;
      audio.play().catch(() => definirTocando(card, false));
    } else {
      audio.pause();
    }
  });
  barra?.addEventListener("click", (evento) => evento.stopPropagation());
  barra?.addEventListener("pointerdown", (evento) => evento.stopPropagation());
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

function criarModalDetalheGlobal() {
  let detalhe = document.querySelector("[data-wiki-global-detail]");
  if (detalhe) return detalhe;
  detalhe = document.createElement("aside");
  detalhe.className = "pokemon-detalhe item-detalhe wiki-busca-detalhe";
  detalhe.dataset.wikiGlobalDetail = "true";
  detalhe.hidden = true;
  detalhe.setAttribute("aria-live", "polite");
  detalhe.innerHTML = `
    <div class="pokemon-detalhe-backdrop" data-wiki-global-detail-close></div>
    <article class="pokemon-detalhe-card item-detalhe-card wiki-busca-detalhe-card" role="dialog" aria-modal="true" aria-labelledby="wiki-busca-detalhe-nome">
      <button class="pokemon-fechar" type="button" aria-label="Fechar detalhes" data-wiki-global-detail-close>×</button>
      <section class="pokemon-detalhe-topo item-detalhe-topo wiki-busca-detalhe-topo">
        <div class="pokemon-palco-detalhe item-palco-detalhe wiki-busca-detalhe-palco">
          <span class="pokemon-brilho-detalhe"></span>
          <img data-wiki-global-detail-image hidden alt="" />
          <span class="item-card-sem-arte wiki-busca-detalhe-fallback" data-wiki-global-detail-fallback hidden></span>
        </div>
        <div class="pokemon-cabecalho-detalhe">
          <span class="codigo-pokemon" data-wiki-global-detail-code></span>
          <h2 id="wiki-busca-detalhe-nome" data-wiki-global-detail-name>Resultado</h2>
          <div class="pokemon-tags" data-wiki-global-detail-tags></div>
          <p data-wiki-global-detail-summary></p>
        </div>
      </section>
      <div class="pokemon-detalhe-grid wiki-busca-detalhe-grid">
        <section class="painel-detalhe item-info-painel">
          <h3>Informações avançadas</h3>
          <dl class="pokemon-info-lista" data-wiki-global-detail-info></dl>
        </section>
        <section class="painel-detalhe item-info-painel">
          <h3>Descrição</h3>
          <p class="item-descricao-melhor" data-wiki-global-detail-description></p>
        </section>
      </div>
    </article>
  `;
  document.body.appendChild(detalhe);
  return detalhe;
}

function abrirDetalheGlobal(item) {
  const detalhe = criarModalDetalheGlobal();
  const dados = item.detalhe || {};
  const imagem = detalhe.querySelector("[data-wiki-global-detail-image]");
  const fallback = detalhe.querySelector("[data-wiki-global-detail-fallback]");
  const codigo = detalhe.querySelector("[data-wiki-global-detail-code]");
  const nome = detalhe.querySelector("[data-wiki-global-detail-name]");
  const tags = detalhe.querySelector("[data-wiki-global-detail-tags]");
  const resumo = detalhe.querySelector("[data-wiki-global-detail-summary]");
  const info = detalhe.querySelector("[data-wiki-global-detail-info]");
  const descricao = detalhe.querySelector("[data-wiki-global-detail-description]");

  const titulo = dados.titulo || item.titulo;
  if (codigo) codigo.textContent = dados.codigo || item.codigo || item.secao || "Wiki";
  if (nome) nome.textContent = titulo;
  if (resumo) resumo.textContent = dados.subtitulo || item.meta || item.tipo || "";
  if (descricao) descricao.textContent = dados.descricao || item.descricao || "Informações detalhadas ainda não cadastradas.";
  if (tags) {
    const tagsLista = Array.isArray(dados.tags) && dados.tags.length ? dados.tags : [item.secao, item.tipo].filter(Boolean);
    tags.innerHTML = tagsLista.map((tag) => `<span class="tag-extra">${html(tag)}</span>`).join("");
  }
  if (info) {
    const linhas = Array.isArray(dados.infos) && dados.infos.length
      ? dados.infos
      : [["Wiki", item.secao], ["Categoria", item.tipo], ["Resumo", item.meta]];
    info.innerHTML = infoHtml(linhas);
  }
  if (imagem && fallback) {
    if (dados.imagem) {
      imagem.hidden = false;
      imagem.src = dados.imagem;
      imagem.alt = titulo;
      fallback.hidden = true;
      fallback.textContent = "";
    } else {
      imagem.hidden = true;
      imagem.removeAttribute("src");
      fallback.hidden = false;
      fallback.textContent = String(dados.fallback || titulo || "?").slice(0, 2);
    }
  }
  abrirModalDetalhe(detalhe);
}

function conectarModalGlobal() {
  const detalhe = criarModalDetalheGlobal();
  const fechar = () => fecharModalDetalhe(detalhe);
  detalhe.querySelectorAll("[data-wiki-global-detail-close]").forEach((botao) => botao.addEventListener("click", fechar));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fechar();
  });
}

function deveIgnorarCliqueDoCard(evento) {
  return !!evento.target.closest?.("button, input, audio, label, [data-musica-toggle], [data-musica-progress]");
}

function atualizarFiltrosVisuais(filtros, selecionados) {
  filtros.forEach((botao) => {
    const ativo = selecionados.has(botao.dataset.wikiGlobalFilter || "");
    botao.classList.toggle("ativo", ativo);
    botao.setAttribute("aria-pressed", ativo ? "true" : "false");
  });
}

function filtrarPorWiki(resultados, selecionados) {
  if (!selecionados.size) return resultados;
  return resultados.filter((item) => selecionados.has(item.categoria));
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
  const filtrosWrapper = document.querySelector("[data-wiki-global-filters]");
  const filtros = [...document.querySelectorAll("[data-wiki-global-filter]")];
  const volumeControle = document.querySelector("[data-wiki-global-volume]");
  const itens = Array.isArray(dados.itens) ? dados.itens : [];
  const selecionados = new Set();
  let renderId = 0;

  volumeGlobal = lerVolumeSalvo();
  if (volumeControle) volumeControle.value = String(volumeGlobal);
  conectarModalGlobal();

  function atualizar() {
    const termo = input?.value?.trim() ?? "";
    const ativo = termo.length > 0;
    const idAtual = ++renderId;
    const resultadosBrutos = ativo ? buscar(itens, termo) : [];
    const resultados = filtrarPorWiki(resultadosBrutos, selecionados);
    const totalLimitado = Math.min(resultados.length, LIMITE_RESULTADOS);
    if (secoes) secoes.hidden = ativo;
    if (resultadosSecao) resultadosSecao.hidden = !ativo;
    if (filtrosWrapper) filtrosWrapper.hidden = !ativo;
    if (vazio) vazio.hidden = !ativo || resultados.length > 0;
    if (status) {
      if (!ativo) {
        status.textContent = `${itens.length} cartuchos e faixas indexados para busca rápida.`;
      } else if (selecionados.size) {
        status.textContent = `${resultados.length} de ${resultadosBrutos.length} resultado${resultadosBrutos.length === 1 ? "" : "s"} encontrado${resultadosBrutos.length === 1 ? "" : "s"}.`;
      } else {
        status.textContent = `${resultados.length} resultado${resultados.length === 1 ? "" : "s"} encontrado${resultados.length === 1 ? "" : "s"}.`;
      }
    }
    if (!resultadosGrid) return;
    resultadosGrid.replaceChildren();
    if (!ativo || !resultados.length) return;
    window.requestAnimationFrame(() => {
      if (idAtual !== renderId) return;
      const fragmento = document.createDocumentFragment();
      resultados.slice(0, totalLimitado).forEach((item) => {
        const card = criarResultadoCard(item);
        const abrir = (evento) => {
          if (item.modelo === "musica" && deveIgnorarCliqueDoCard(evento)) return;
          abrirDetalheGlobal(item);
        };
        card.addEventListener("click", abrir);
        if (card.tagName !== "BUTTON") {
          card.addEventListener("keydown", (evento) => {
            if (evento.key === "Enter" || evento.key === " ") {
              evento.preventDefault();
              abrirDetalheGlobal(item);
            }
          });
        }
        fragmento.appendChild(card);
      });
      resultadosGrid.appendChild(fragmento);
      aplicarVolumeGlobal(resultadosGrid);
    });
  }

  filtros.forEach((botao) => {
    const chave = botao.dataset.wikiGlobalFilter || "";
    if (!FILTROS_WIKI.includes(chave)) return;
    botao.addEventListener("click", () => {
      if (selecionados.has(chave)) selecionados.delete(chave);
      else selecionados.add(chave);
      atualizarFiltrosVisuais(filtros, selecionados);
      atualizar();
    });
  });
  volumeControle?.addEventListener("input", () => {
    volumeGlobal = limitarVolume(volumeControle.value);
    salvarVolume(volumeGlobal);
    aplicarVolumeGlobal(resultadosGrid || document);
  });
  input?.addEventListener("input", atualizar);
  atualizarFiltrosVisuais(filtros, selecionados);
  atualizar();
}
