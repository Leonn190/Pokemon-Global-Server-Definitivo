function lerJson(id) {
  const script = document.getElementById(id);
  if (!script) return null;
  try {
    return JSON.parse(script.textContent || "{}");
  } catch (_erro) {
    return null;
  }
}

function html(valor) {
  return String(valor ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizar(valor) {
  return String(valor ?? "")
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function assetEfeito(efeito, dados) {
  return dados.assetsEfeitos?.[efeito.id] ?? { imagem: null };
}

function criarCardEfeito(efeito, dados) {
  const asset = assetEfeito(efeito, dados);
  const card = document.createElement("button");
  card.type = "button";
  card.className = "item-card efeito-card";
  card.dataset.efeitoId = efeito.id;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(efeito.id)}</span>
    <span class="item-card-arte efeito-card-arte">
      ${asset.imagem ? `<img src="${asset.imagem}" alt="${html(efeito.nome)}" loading="lazy" decoding="async" />` : `<span class="item-card-sem-arte">${html(efeito.nome.slice(0, 1))}</span>`}
    </span>
    <span class="item-card-nome">${html(efeito.nome)}</span>
  `;
  return card;
}

function criarControladorDetalhe(dados, obterListaAtual) {
  const detalhe = document.querySelector("[data-efeito-detail]");
  let efeitoAberto = null;

  function listaNavegacao() {
    const listaAtual = typeof obterListaAtual === "function" ? obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.efeitos || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }

  function abrirVizinho(direcao) {
    if (!efeitoAberto) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((efeito) => String(efeito.id) === String(efeitoAberto.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.id);
  }

  function abrirDetalhe(id) {
    const efeito = (dados.efeitos || []).find((atual) => atual.id === String(id));
    if (!efeito || !detalhe) return;
    efeitoAberto = efeito;
    const asset = assetEfeito(efeito, dados);
    const imagem = detalhe.querySelector("[data-efeito-image]");
    const codigo = detalhe.querySelector("[data-efeito-code]");
    const nome = detalhe.querySelector("[data-efeito-name]");
    const tags = detalhe.querySelector("[data-efeito-tags]");
    const descricao = detalhe.querySelector("[data-efeito-description]");
    const info = detalhe.querySelector("[data-efeito-info]");

    if (codigo) codigo.textContent = `#${efeito.id}`;
    if (nome) nome.textContent = efeito.nome;

    if (imagem) {
      if (asset.imagem) {
        imagem.hidden = false;
        imagem.src = asset.imagem;
        imagem.alt = efeito.nome;
      } else {
        imagem.hidden = true;
        imagem.removeAttribute("src");
      }
    }

    if (tags) {
      const sentido = efeito.sentidoBusca ? `<span class="tag-extra">${html(efeito.sentidoRotulo)}</span>` : "";
      tags.innerHTML = `<span class="tag-extra">${html(efeito.estiloRotulo)}</span>${sentido}<span class="tag-extra">Passos base: ${html(efeito.passosBaseTexto)}</span>`;
    }

    if (descricao) descricao.textContent = efeito.descricao || "Descrição ainda não cadastrada.";

    if (info) {
      const linhas = [
        ["Passos base", efeito.passosBaseTexto],
        ["Estilo", efeito.estiloRotulo],
      ];
      info.innerHTML = linhas.map(([chave, valor]) => `<div><dt>${html(chave)}</dt><dd>${html(valor)}</dd></div>`).join("");
    }

    detalhe.hidden = false;
    document.body.classList.add("detalhe-aberto");
  }

  function fecharDetalhe() {
    if (detalhe) detalhe.hidden = true;
    document.body.classList.remove("detalhe-aberto");
  }

  detalhe?.querySelectorAll("[data-efeito-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-efeito-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-efeito-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });

  return { abrirDetalhe };
}

export function inicializarWikiEfeitos(idDados = "efeitos-data") {
  const dados = lerJson(idDados);
  const app = document.querySelector("[data-efeitos-app]");
  if (!dados || !app) return;

  const grid = app.querySelector("[data-efeitos-grid]");
  const busca = app.querySelector("[data-efeitos-search]");
  const ordenacao = app.querySelector("[data-efeitos-sort]");
  const direcaoBotao = app.querySelector("[data-efeitos-direction]");
  const filtroEstilo = app.querySelector("[data-efeitos-style]");
  const filtroSentido = app.querySelector("[data-efeitos-sense]");
  const contador = app.querySelector("[data-efeitos-count]");
  const botaoLimpar = app.querySelector("[data-efeitos-clear]");
  const vazio = app.querySelector("[data-efeitos-empty]");
  const sentinela = app.querySelector("[data-efeitos-sentinel]");
  const PAGE_SIZE = 36;
  const RENDER_DELAY = 18;
  let visiveis = 0;
  let resultadoAtual = [];
  let renderRequest = 0;
  let renderizando = false;

  if (direcaoBotao && !direcaoBotao.dataset.sortDirection) direcaoBotao.dataset.sortDirection = "asc";
  const detalheController = criarControladorDetalhe(dados, () => resultadoAtual);

  function direcaoAtual() {
    return direcaoBotao?.dataset.sortDirection === "desc" ? "desc" : "asc";
  }

  function atualizarDirecao() {
    if (!direcaoBotao) return;
    direcaoBotao.textContent = direcaoAtual() === "asc" ? "Crescente" : "Descrescente";
  }

  function obterResultado() {
    const termo = normalizar(busca?.value ?? "");
    const estilo = filtroEstilo?.value ?? "";
    const sentido = filtroSentido?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
    const direcao = direcaoAtual();

    const filtrados = (dados.efeitos || []).filter((efeito) => {
      if (termo && !efeito.busca.includes(termo)) return false;
      if (estilo && efeito.estiloBusca !== estilo) return false;
      if (sentido && efeito.sentidoBusca !== sentido) return false;
      return true;
    });

    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
    };

    const ordenador = ordenadores[sort] ?? ordenadores.ordem;
    return [...filtrados].sort((a, b) => {
      const principal = ordenador(a, b);
      const final = principal === 0 ? a.ordem - b.ordem : principal;
      return direcao === "desc" ? -final : final;
    });
  }

  function atualizarEstado() {
    if (contador) contador.textContent = String(resultadoAtual.length);
    if (vazio) vazio.hidden = resultadoAtual.length !== 0;
    if (sentinela) sentinela.hidden = resultadoAtual.length === 0 || visiveis >= resultadoAtual.length;
    atualizarDirecao();
  }

  function anexarCard(inicio, fim) {
    if (!grid) return;
    const fragmento = document.createDocumentFragment();
    resultadoAtual.slice(inicio, fim).forEach((efeito) => {
      const card = criarCardEfeito(efeito, dados);
      card.classList.add("pokemon-card-entrando");
      fragmento.appendChild(card);
    });
    grid.appendChild(fragmento);
  }

  function manterScrollAposReset(alturaAnterior, scrollAnterior) {
    if (!grid) return;
    if (alturaAnterior > 0) grid.style.minHeight = `${Math.ceil(alturaAnterior)}px`;

    const comportamentoAnterior = document.documentElement.style.scrollBehavior;
    document.documentElement.style.scrollBehavior = "auto";
    window.requestAnimationFrame(() => {
      window.scrollTo(window.scrollX, scrollAnterior);
      document.documentElement.style.scrollBehavior = comportamentoAnterior;
    });
  }

  function liberarAlturaReservada(idRender) {
    window.setTimeout(() => {
      if (grid && idRender === renderRequest) grid.style.minHeight = "";
    }, 120);
  }

  function renderizarAte(limite, idRender) {
    if (!grid || idRender !== renderRequest) return;
    const jaRenderizados = grid.children.length;
    const alvo = Math.min(limite, resultadoAtual.length);
    if (jaRenderizados >= alvo) {
      renderizando = false;
      atualizarEstado();
      liberarAlturaReservada(idRender);
      return;
    }
    renderizando = true;
    window.requestAnimationFrame(() => {
      if (idRender !== renderRequest) return;
      anexarCard(jaRenderizados, jaRenderizados + 1);
      window.setTimeout(() => renderizarAte(alvo, idRender), RENDER_DELAY);
    });
  }

  function renderLista(reset = true) {
    if (!grid) return;
    if (reset) {
      const idRender = ++renderRequest;
      const alturaAnterior = grid.getBoundingClientRect().height;
      const scrollAnterior = window.scrollY;
      resultadoAtual = obterResultado();
      visiveis = Math.min(PAGE_SIZE, resultadoAtual.length);
      manterScrollAposReset(alturaAnterior, scrollAnterior);
      grid.replaceChildren();
      renderizando = false;
      atualizarEstado();
      renderizarAte(visiveis, idRender);
      return;
    }

    if (renderizando || visiveis >= resultadoAtual.length) return;
    const idRender = ++renderRequest;
    const proximoLimite = Math.min(visiveis + PAGE_SIZE, resultadoAtual.length);
    visiveis = proximoLimite;
    atualizarEstado();
    renderizarAte(proximoLimite, idRender);
  }

  function limparFiltros() {
    if (busca) busca.value = "";
    if (ordenacao) ordenacao.value = "ordem";
    if (filtroEstilo) filtroEstilo.value = "";
    if (filtroSentido) filtroSentido.value = "";
    if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    renderLista(true);
  }

  grid?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-efeito-id]");
    if (card) detalheController.abrirDetalhe(card.dataset.efeitoId);
  });

  [busca, ordenacao, filtroEstilo, filtroSentido].forEach((elemento) => {
    elemento?.addEventListener("input", () => renderLista(true));
    elemento?.addEventListener("change", () => renderLista(true));
  });

  direcaoBotao?.addEventListener("click", () => {
    direcaoBotao.dataset.sortDirection = direcaoAtual() === "asc" ? "desc" : "asc";
    renderLista(true);
  });

  botaoLimpar?.addEventListener("click", limparFiltros);

  if (sentinela && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entradas) => {
      if (entradas.some((entrada) => entrada.isIntersecting)) renderLista(false);
    }, { rootMargin: "220px" });
    observer.observe(sentinela);
  }

  renderLista(true);
}
