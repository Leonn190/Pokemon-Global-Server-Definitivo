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
function iniciarAcessibilidadeModaisWiki() {
  if (typeof window === "undefined" || typeof document === "undefined" || window.__PGS_MODAL_A11Y) return;
  window.__PGS_MODAL_A11Y = true;
  const seletorFoco = [
    "a[href]",
    "button:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
  ].join(",");
  const focoAnterior = new WeakMap();

  function containerDoDialog(dialog) {
    return dialog?.closest("aside, [data-pokemon-detail], [data-item-detail], [data-ataque-detail], [data-efeito-detail], [data-equipavel-detail], [data-dungeon-detail], [data-mundo-detail], [data-npc-detail], [data-estadio-detail]") ?? null;
  }
  function estaVisivel(elemento) {
    return !!elemento && !elemento.hidden && elemento.getClientRects().length > 0;
  }
  function dialogAbertoAtual() {
    const dialogs = [...document.querySelectorAll("[role='dialog']")];
    return dialogs.reverse().find((dialog) => estaVisivel(containerDoDialog(dialog) || dialog));
  }
  function elementosFocaveis(dialog) {
    return [...dialog.querySelectorAll(seletorFoco)].filter((item) => !item.hidden && item.getClientRects().length > 0);
  }
  function ativarModal(container) {
    const dialog = container?.querySelector?.("[role='dialog']") ?? (container?.matches?.("[role='dialog']") ? container : null);
    if (!dialog || container?.hidden) return;
    if (!focoAnterior.has(container)) focoAnterior.set(container, document.activeElement);
    container.dataset.pgsModalOpen = "true";
    if (!dialog.hasAttribute("tabindex")) dialog.setAttribute("tabindex", "-1");
    window.requestAnimationFrame(() => {
      const alvo = dialog.querySelector("[aria-label*='Fechar'], .pokemon-fechar, button") || dialog;
      alvo.focus?.({ preventScroll: true });
    });
  }
  function desativarModal(container) {
    if (!container) return;
    delete container.dataset.pgsModalOpen;
    const anterior = focoAnterior.get(container);
    focoAnterior.delete(container);
    if (anterior && document.contains(anterior) && typeof anterior.focus === "function") {
      window.requestAnimationFrame(() => anterior.focus({ preventScroll: true }));
    }
  }
  function avaliarContainer(container) {
    if (!container?.querySelector?.("[role='dialog']")) return;
    if (container.hidden) desativarModal(container);
    else ativarModal(container);
  }

  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Tab") return;
    const dialog = dialogAbertoAtual();
    if (!dialog) return;
    const focaveis = elementosFocaveis(dialog);
    if (!focaveis.length) {
      evento.preventDefault();
      dialog.focus?.({ preventScroll: true });
      return;
    }
    const primeiro = focaveis[0];
    const ultimo = focaveis[focaveis.length - 1];
    if (evento.shiftKey && document.activeElement === primeiro) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primeiro.focus();
    }
  });

  const observer = new MutationObserver((mutacoes) => {
    mutacoes.forEach((mutacao) => {
      if (mutacao.type === "attributes" && mutacao.attributeName === "hidden") avaliarContainer(mutacao.target);
      mutacao.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) avaliarContainer(node);
      });
    });
  });
  const iniciarObserver = () => {
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden"] });
    document.querySelectorAll("[role='dialog']").forEach((dialog) => avaliarContainer(containerDoDialog(dialog) || dialog));
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciarObserver, { once: true });
  else iniciarObserver();
}
iniciarAcessibilidadeModaisWiki();

export function criarListagemPaginada(opcoes) {
  const {
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    controles = [],
    botaoLimpar,
    pageSize = 24,
    renderDelay = 8,
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
    cancelado: false,
  };
  const cancelarRender = () => {
    estado.cancelado = true;
    estado.renderRequest += 1;
    estado.renderizando = false;
  };
  window.__PGS_CANCEL_GRID_RENDERS = window.__PGS_CANCEL_GRID_RENDERS || new Set();
  window.__PGS_CANCEL_GRID_RENDERS.add(cancelarRender);
  const cancelarTodosOsRenders = () => {
    window.__PGS_CANCEL_GRID_RENDERS?.forEach((cancelar) => cancelar());
  };
  window.addEventListener("pagehide", cancelarRender, { once: true });
  window.addEventListener("beforeunload", cancelarRender, { once: true });
  document.addEventListener("pointerdown", (evento) => {
    if (evento.target.closest?.(".wiki-menu-topo a, .wiki-menu-lateral a")) cancelarTodosOsRenders();
  }, { capture: true });
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
      if (classeEntrada) {
        card.classList.add(classeEntrada);
        card.addEventListener("animationend", () => card.classList.remove(classeEntrada), { once: true });
      }
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
  function sentinelaPertoDaTela() {
    if (!sentinela || sentinela.hidden || estado.visiveis >= estado.resultadoAtual.length) return false;
    const rect = sentinela.getBoundingClientRect();
    return rect.top < window.innerHeight + 900 && rect.bottom > -300;
  }
  function gridAindaNaoPreencheATela() {
    if (!grid || estado.visiveis >= estado.resultadoAtual.length) return false;
    const fimGrid = grid.getBoundingClientRect().bottom;
    return fimGrid < window.innerHeight + 520;
  }
  function deveCarregarMaisAgora() {
    return sentinelaPertoDaTela() || gridAindaNaoPreencheATela();
  }
  function agendarChecagemDeCarga(idRender = estado.renderRequest) {
    window.requestAnimationFrame(() => {
      if (estado.cancelado || idRender !== estado.renderRequest) return;
      if (!estado.renderizando && deveCarregarMaisAgora()) renderLista(false);
    });
  }
  function renderizarAte(limite, idRender) {
    if (!grid || estado.cancelado || idRender !== estado.renderRequest) return;
    const jaRenderizados = grid.children.length;
    const alvo = Math.min(limite, estado.resultadoAtual.length);
    if (jaRenderizados >= alvo) {
      estado.renderizando = false;
      atualizarEstado();
      liberarAlturaReservada(idRender);
      agendarChecagemDeCarga(idRender);
      return;
    }
    estado.renderizando = true;
    window.requestAnimationFrame(() => {
      if (estado.cancelado || idRender !== estado.renderRequest) return;
      anexarCard(jaRenderizados, jaRenderizados + 1);
      window.setTimeout(() => renderizarAte(alvo, idRender), renderDelay);
    });
  }
  function renderLista(reset = true) {
    if (!grid) return;
    if (reset) {
      estado.cancelado = false;
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
      agendarChecagemDeCarga(idRender);
      return;
    }
    if (estado.renderizando || estado.visiveis >= estado.resultadoAtual.length) {
      atualizarEstado();
      return;
    }
    estado.cancelado = false;
    const idRender = ++estado.renderRequest;
    estado.visiveis = Math.min(estado.visiveis + pageSize, estado.resultadoAtual.length);
    atualizarEstado();
    renderizarAte(estado.visiveis, idRender);
  }
  function carregarMaisAutomatico() {
    if (estado.renderizando || estado.visiveis >= estado.resultadoAtual.length) return;
    renderLista(false);
  }
  function checarCargaPelaTela() {
    if (estado.renderizando || estado.visiveis >= estado.resultadoAtual.length) return;
    if (deveCarregarMaisAgora()) carregarMaisAutomatico();
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
  }
  const aoScrollOuResize = () => checarCargaPelaTela();
  window.addEventListener("scroll", aoScrollOuResize, { passive: true });
  window.addEventListener("resize", aoScrollOuResize, { passive: true });
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
export function criarWikiCatalogo(opcoes) {
  return criarListagemPaginada(opcoes);
}

export function criarGridProgressiva({
  grid,
  itens = [],
  criarCard,
  cardSelector,
  obterCardId,
  abrirDetalhe,
  pageSize = 24,
  renderDelay = 8,
  classeEntrada = "pokemon-card-entrando",
}) {
  return criarListagemPaginada({
    grid,
    pageSize,
    renderDelay,
    classeEntrada,
    cardSelector,
    obterCardId,
    abrirDetalhe,
    criarCard,
    obterResultado: () => itens,
    preservarScroll: false,
    usarFallbackScroll: true,
  });
}
