export function lerJson(id, origem = "Wiki") {
  const node = document.getElementById(id);
  if (!node) return null;

  try {
    return JSON.parse(node.textContent || "{}");
  } catch (erro) {
    console.error(`[${origem}] Não consegui ler os dados de ${id}.`, erro);
    return null;
  }
}

export function html(valor) {
  return String(valor ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#039;",
    '"': "&quot;",
  })[char]);
}

export function normalizar(valor) {
  return String(valor ?? "")
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

export function formatarNumero(valor, sufixo = "") {
  if (valor === null || valor === undefined || valor === "" || Number.isNaN(Number(valor))) return "-";

  const numero = Number(valor);
  const texto = Number.isInteger(numero)
    ? String(numero)
    : numero.toLocaleString("pt-BR", { maximumFractionDigits: 2 });

  return `${texto}${sufixo}`;
}

export function infoHtml(linhas) {
  return linhas.map(([chave, valor]) => `<div><dt>${html(chave)}</dt><dd>${html(valor)}</dd></div>`).join("");
}

export function aplicarImagemDetalhe(imagem, src, alt) {
  if (!imagem) return;
  if (src) {
    imagem.hidden = false;
    imagem.src = src;
    imagem.alt = alt || "";
    return;
  }
  imagem.hidden = true;
  imagem.removeAttribute("src");
}

export function ordenarComDirecao(lista, ordenadores, sort, direcao, ordenadorPadrao = "ordem") {
  const ordenador = ordenadores[sort] ?? ordenadores[ordenadorPadrao];
  return [...lista].sort((a, b) => {
    const principal = ordenador(a, b);
    const final = principal === 0 ? (a.ordem ?? 0) - (b.ordem ?? 0) : principal;
    return direcao === "desc" ? -final : final;
  });
}

export function criarListagemPaginada(opcoes) {
  const {
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    controles = [],
    botaoLimpar,
    pageSize = 36,
    renderDelay = 18,
    rootMargin = "360px 0px",
    preservarScroll = true,
    usarFallbackScroll = false,
    classeEntrada = "pokemon-card-entrando",
    cardSelector,
    obterCardId,
    abrirDetalhe,
    criarCard,
    obterResultado,
    limparFiltros,
    aoAtualizarEstado,
  } = opcoes;

  const estado = {
    visiveis: 0,
    resultadoAtual: [],
    renderRequest: 0,
    renderizando: false,
  };

  if (direcaoBotao && !direcaoBotao.dataset.sortDirection) direcaoBotao.dataset.sortDirection = "asc";

  function direcaoAtual() {
    return direcaoBotao?.dataset.sortDirection === "desc" ? "desc" : "asc";
  }

  function atualizarDirecao() {
    if (!direcaoBotao) return;
    direcaoBotao.textContent = direcaoAtual() === "asc" ? "Crescente" : "Descrescente";
  }

  function atualizarEstado() {
    if (contador) contador.textContent = String(estado.resultadoAtual.length);
    if (vazio) vazio.hidden = estado.resultadoAtual.length !== 0;
    if (sentinela) sentinela.hidden = estado.resultadoAtual.length === 0 || estado.visiveis >= estado.resultadoAtual.length;
    atualizarDirecao();
    aoAtualizarEstado?.(estado);
  }

  function anexarCard(inicio, fim) {
    if (!grid) return;
    const fragmento = document.createDocumentFragment();
    estado.resultadoAtual.slice(inicio, fim).forEach((item) => {
      const card = criarCard(item);
      if (classeEntrada) card.classList.add(classeEntrada);
      fragmento.appendChild(card);
    });
    grid.appendChild(fragmento);
  }

  function manterScrollAposReset(alturaAnterior, scrollAnterior) {
    if (!grid || !preservarScroll) return;
    if (alturaAnterior > 0) grid.style.minHeight = `${Math.ceil(alturaAnterior)}px`;

    const comportamentoAnterior = document.documentElement.style.scrollBehavior;
    document.documentElement.style.scrollBehavior = "auto";
    window.requestAnimationFrame(() => {
      window.scrollTo(window.scrollX, scrollAnterior);
      document.documentElement.style.scrollBehavior = comportamentoAnterior;
    });
  }

  function liberarAlturaReservada(idRender) {
    if (!preservarScroll) return;
    window.setTimeout(() => {
      if (grid && idRender === estado.renderRequest) grid.style.minHeight = "";
    }, 120);
  }

  function renderizarAte(limite, idRender) {
    if (!grid || idRender !== estado.renderRequest) return;
    const jaRenderizados = grid.children.length;
    const alvo = Math.min(limite, estado.resultadoAtual.length);
    if (jaRenderizados >= alvo) {
      estado.renderizando = false;
      atualizarEstado();
      liberarAlturaReservada(idRender);
      return;
    }

    estado.renderizando = true;
    window.requestAnimationFrame(() => {
      if (idRender !== estado.renderRequest) return;
      anexarCard(jaRenderizados, jaRenderizados + 1);
      window.setTimeout(() => renderizarAte(alvo, idRender), renderDelay);
    });
  }

  function renderLista(reset = true) {
    if (!grid) return;

    if (reset) {
      const idRender = ++estado.renderRequest;
      const alturaAnterior = grid.getBoundingClientRect().height;
      const scrollAnterior = window.scrollY;
      estado.resultadoAtual = obterResultado(direcaoAtual());
      estado.visiveis = Math.min(pageSize, estado.resultadoAtual.length);
      manterScrollAposReset(alturaAnterior, scrollAnterior);
      grid.replaceChildren();
      estado.renderizando = false;
      atualizarEstado();
      renderizarAte(estado.visiveis, idRender);
      return;
    }

    if (estado.renderizando || estado.visiveis >= estado.resultadoAtual.length) {
      atualizarEstado();
      return;
    }

    const idRender = ++estado.renderRequest;
    estado.visiveis = Math.min(estado.visiveis + pageSize, estado.resultadoAtual.length);
    atualizarEstado();
    renderizarAte(estado.visiveis, idRender);
  }

  function carregarMaisAutomatico() {
    if (estado.renderizando || estado.visiveis >= estado.resultadoAtual.length) return;
    renderLista(false);
  }

  controles.forEach((controle) => {
    controle?.addEventListener("input", () => renderLista(true));
    controle?.addEventListener("change", () => renderLista(true));
  });

  direcaoBotao?.addEventListener("click", () => {
    direcaoBotao.dataset.sortDirection = direcaoAtual() === "asc" ? "desc" : "asc";
    renderLista(true);
  });

  botaoLimpar?.addEventListener("click", () => {
    limparFiltros?.();
    renderLista(true);
  });

  grid?.addEventListener("click", (evento) => {
    if (!cardSelector || typeof abrirDetalhe !== "function") return;
    const card = evento.target.closest(cardSelector);
    if (!card) return;
    abrirDetalhe(obterCardId ? obterCardId(card) : card.dataset.id);
  });

  if (sentinela && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entradas) => {
      if (entradas.some((entrada) => entrada.isIntersecting)) carregarMaisAutomatico();
    }, { rootMargin });
    observer.observe(sentinela);
  } else if (usarFallbackScroll) {
    window.addEventListener("scroll", () => {
      const restante = document.documentElement.scrollHeight - window.scrollY - window.innerHeight;
      if (restante < 360) carregarMaisAutomatico();
    }, { passive: true });
  }

  return {
    iniciar() {
      atualizarDirecao();
      renderLista(true);
    },
    renderLista,
    direcaoAtual,
    obterResultadoAtual() {
      return estado.resultadoAtual;
    },
  };
}
