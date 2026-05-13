import { criarWikiCatalogo, html, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";

const DURACAO_DESCONHECIDA = Number.POSITIVE_INFINITY;

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

function criarFaixa(musica) {
  const card = document.createElement("article");
  card.className = "faixa-musica";
  card.dataset.musicaId = musica.id;
  card.dataset.nome = musica.nome;
  card.dataset.duracao = Number.isFinite(musica.duracao) ? String(musica.duracao) : "";
  card.innerHTML = `
    <button class="faixa-musica-botao" type="button" data-musica-toggle aria-label="Tocar ${html(musica.nome)}">
      <span data-musica-icone aria-hidden="true">▶</span>
    </button>
    <div class="faixa-musica-texto">
      <strong>${html(musica.nome)}</strong>
      <span>${html(musica.estiloRotulo)}</span>
    </div>
    <label class="faixa-musica-volume" aria-label="Volume da música ${html(musica.nome)}">
      <input type="range" min="0" max="1" value="1" step="0.01" data-musica-volume />
    </label>
    <label class="faixa-musica-barra" aria-label="Posição da música ${html(musica.nome)}">
      <input type="range" min="0" max="1000" value="0" step="1" data-musica-progress />
    </label>
    <time class="faixa-musica-tempo" data-musica-tempo>0:00 / ${formatarTempo(musica.duracao)}</time>
    <audio preload="none" src="${html(musica.url)}"></audio>
  `;
  const audio = card.querySelector("audio");
  const barra = card.querySelector("[data-musica-progress]");
  const volume = card.querySelector("[data-musica-volume]");
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
  audio?.addEventListener("pause", () => definirTocando(card, false));
  audio?.addEventListener("play", () => definirTocando(card, true));
  barra?.addEventListener("input", () => {
    if (!audio || !Number.isFinite(audio.duration) || audio.duration <= 0) return;
    audio.currentTime = (Number(barra.value) / 1000) * audio.duration;
    atualizarFaixaTempo(card);
  });
  volume?.addEventListener("input", () => {
    if (!audio) return;
    audio.volume = Math.min(1, Math.max(0, Number(volume.value) || 0));
  });
  return card;
}

function buscarDuracao(musica) {
  return new Promise((resolve) => {
    if (Number.isFinite(musica.duracao)) {
      resolve(musica.duracao);
      return;
    }
    const audio = new Audio();
    audio.preload = "metadata";
    const finalizar = (valor = null) => {
      audio.removeAttribute("src");
      audio.load?.();
      resolve(valor);
    };
    audio.addEventListener("loadedmetadata", () => finalizar(Number.isFinite(audio.duration) ? audio.duration : null), { once: true });
    audio.addEventListener("error", () => finalizar(null), { once: true });
    audio.src = musica.url;
  });
}

function medirDuracoes(musicas, aoAtualizar, podeMedir = () => true) {
  let indice = 0;
  let ativa = false;
  let reagendar = 0;
  const agendar = (callback) => {
    const requestIdle = window.requestIdleCallback || ((fn) => window.setTimeout(fn, 160));
    requestIdle(callback);
  };
  const proxima = () => {
    window.clearTimeout(reagendar);
    if (ativa || indice >= musicas.length) return;
    if (!podeMedir()) {
      reagendar = window.setTimeout(proxima, 900);
      return;
    }
    const musica = musicas[indice];
    indice += 1;
    ativa = true;
    buscarDuracao(musica).then((duracao) => {
      ativa = false;
      if (Number.isFinite(duracao)) {
        musica.duracao = duracao;
        aoAtualizar?.(musica);
      }
      agendar(proxima);
    });
  };
  agendar(proxima);
}

export function inicializarWikiMusicas() {
  const payload = lerJson("musicas-data", "Wiki Músicas");
  if (!payload?.musicas) return;
  const musicas = payload.musicas;
  const app = document.querySelector("[data-musicas-app]");
  const grid = document.querySelector("[data-musicas-grid]");
  const busca = document.querySelector("[data-musicas-search]");
  const sort = document.querySelector("[data-musicas-sort]");
  const estilo = document.querySelector("[data-musicas-style]");
  const contador = document.querySelector("[data-musicas-count]");
  const direcaoBotao = document.querySelector("[data-musicas-direction]");
  const limparBotao = document.querySelector("[data-musicas-clear]");
  const vazio = document.querySelector("[data-musicas-empty]");
  const sentinela = document.querySelector("[data-musicas-sentinel]");
  if (!app || !grid) return;

  let tocandoAtual = null;
  const ordenadores = {
    ordem: (a, b) => (a.ordem ?? 0) - (b.ordem ?? 0),
    nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { sensitivity: "base", numeric: true }),
    duracao: (a, b) => (a.duracao ?? DURACAO_DESCONHECIDA) - (b.duracao ?? DURACAO_DESCONHECIDA),
  };

  const obterResultado = (direcao) => {
    const termo = normalizar(busca?.value ?? "");
    const estiloAtual = estilo?.value ?? "";
    const filtradas = musicas.filter((musica) => {
      if (estiloAtual && musica.estilo !== estiloAtual) return false;
      if (termo && !musica.busca.includes(termo)) return false;
      return true;
    });
    return ordenarComDirecao(filtradas, ordenadores, sort?.value || "ordem", direcao, "ordem");
  };

  const catalogo = criarWikiCatalogo({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    botaoLimpar: limparBotao,
    controles: [busca, sort, estilo].filter(Boolean),
    pageSize: 32,
    cardSelector: ".faixa-musica",
    classeEntrada: "",
    criarCard: criarFaixa,
    obterResultado,
    limparFiltros() {
      if (busca) busca.value = "";
      if (sort) sort.value = "ordem";
      if (estilo) estilo.value = "";
      if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    },
  });

  const pararAtual = () => {
    if (tocandoAtual) tocandoAtual.pause();
    tocandoAtual = null;
  };
  [busca, sort, estilo].filter(Boolean).forEach((controle) => {
    controle.addEventListener("input", pararAtual);
    controle.addEventListener("change", pararAtual);
  });
  direcaoBotao?.addEventListener("click", pararAtual);
  limparBotao?.addEventListener("click", pararAtual);
  window.addEventListener("pagehide", pararAtual, { once: true });

  grid.addEventListener("click", (evento) => {
    const botao = evento.target.closest?.("[data-musica-toggle]");
    if (!botao) return;
    const card = botao.closest(".faixa-musica");
    const audio = card?.querySelector?.("audio");
    if (!card || !audio) return;
    if (tocandoAtual && tocandoAtual !== audio) tocandoAtual.pause();
    if (audio.paused) {
      tocandoAtual = audio;
      audio.play().catch(() => definirTocando(card, false));
    } else {
      audio.pause();
    }
  });

  medirDuracoes(musicas, (musica) => {
    const card = grid.querySelector(`[data-musica-id="${CSS.escape(musica.id)}"]`);
    if (card) {
      card.dataset.duracao = String(musica.duracao);
      atualizarFaixaTempo(card);
    }
    if (sort?.value === "duracao") catalogo.renderLista(true);
  }, () => !tocandoAtual || tocandoAtual.paused);

  catalogo.iniciar();
}
