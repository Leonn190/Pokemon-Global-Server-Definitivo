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

function formatarNumero(valor, sufixo = "") {
  if (valor === null || valor === undefined || valor === "" || Number.isNaN(Number(valor))) return "-";
  const numero = Number(valor);
  const texto = Number.isInteger(numero) ? String(numero) : numero.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  return `${texto}${sufixo}`;
}

function assetAtaque(ataque, dados) {
  return dados.assetsAtaques?.[ataque.id] ?? { imagem: null };
}

function tipoIcone(tipo, dados, classe = "tipo-bola pequena") {
  const chave = normalizar(tipo);
  const src = dados.iconesTipos?.[chave];
  if (src) return `<span class="${classe}"><img src="${src}" alt="" loading="lazy" decoding="async" /></span>`;
  return `<span class="${classe}"><b>${html(String(tipo || "?").slice(0, 1).toUpperCase())}</b></span>`;
}


function focoBarrasHtml(item) {
  const focos = [
    ["Ofensivo", item.ofensivo],
    ["Defensivo", item.defensivo],
    ["Suporte", item.suporte],
    ["Utilitário", item.utilitario],
  ];
  return `<div class="foco-barras">${focos.map(([rotulo, valor]) => {
    const numero = Math.max(0, Math.min(100, Number(valor) || 0));
    return `
      <div class="foco-barra">
        <div class="foco-barra-topo"><span>${html(rotulo)}</span><strong>${formatarNumero(numero)}</strong></div>
        <div class="foco-barra-trilho"><span style="width: ${numero}%"></span></div>
      </div>
    `;
  }).join("")}</div>`;
}

function criarCardAtaque(ataque, dados) {
  const asset = assetAtaque(ataque, dados);
  const card = document.createElement("button");
  card.type = "button";
  card.className = "item-card ataque-card";
  card.dataset.ataqueId = ataque.id;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(ataque.id)}</span>
    <span class="item-card-arte ataque-card-arte">
      ${asset.imagem ? `<img src="${asset.imagem}" alt="${html(ataque.nome)}" loading="lazy" decoding="async" />` : `<span class="item-card-sem-arte">${html(ataque.nome.slice(0, 1))}</span>`}
    </span>
    <span class="item-card-nome">${html(ataque.nome)}</span>
    <span class="item-card-linha"><strong>${formatarNumero(ataque.custo)}</strong><small>Custo</small></span>
  `;
  return card;
}

function criarControladorDetalhe(dados, obterListaAtual) {
  const detalhe = document.querySelector("[data-ataque-detail]");
  let ataqueAberto = null;

  function listaNavegacao() {
    const listaAtual = typeof obterListaAtual === "function" ? obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.ataques || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }

  function abrirVizinho(direcao) {
    if (!ataqueAberto) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((ataque) => String(ataque.id) === String(ataqueAberto.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.id);
  }

  function abrirDetalhe(id) {
    const ataque = (dados.ataques || []).find((atual) => atual.id === String(id));
    if (!ataque || !detalhe) return;
    ataqueAberto = ataque;
    const asset = assetAtaque(ataque, dados);
    const imagem = detalhe.querySelector("[data-ataque-image]");
    const codigo = detalhe.querySelector("[data-ataque-code]");
    const nome = detalhe.querySelector("[data-ataque-name]");
    const tags = detalhe.querySelector("[data-ataque-tags]");
    const descricao = detalhe.querySelector("[data-ataque-description]");
    const aprimoramento = detalhe.querySelector("[data-ataque-upgrade]");
    const info = detalhe.querySelector("[data-ataque-info]");
    const focos = detalhe.querySelector("[data-ataque-focus-bars]");

    if (codigo) codigo.textContent = `#${ataque.id}`;
    if (nome) nome.textContent = ataque.nome;

    if (imagem) {
      if (asset.imagem) {
        imagem.hidden = false;
        imagem.src = asset.imagem;
        imagem.alt = ataque.nome;
      } else {
        imagem.hidden = true;
        imagem.removeAttribute("src");
      }
    }

    if (tags) {
      tags.innerHTML = `
        <span class="tipo-badge">${tipoIcone(ataque.tipo, dados)}${html(ataque.tipo)}</span>
        <span class="tag-extra">${html(ataque.estiloRotulo)}</span>
        <span class="tag-extra">Custo ${formatarNumero(ataque.custo)}</span>
        <span class="tag-extra">AP ${formatarNumero(ataque.custoAprimorado)}</span>
      `;
    }

    if (descricao) descricao.textContent = ataque.descricao || "Descrição ainda não cadastrada.";
    if (aprimoramento) aprimoramento.textContent = ataque.aprimoramento || "Aprimoramento ainda não cadastrado.";

    if (focos) focos.innerHTML = focoBarrasHtml(ataque);

    if (info) {
      const linhas = [
        ["Estilo", ataque.estiloRotulo],
        ["Motor", ataque.motorTexto],
        ["Foco", ataque.focoPrincipal],
        ["Custo após aprimoramento", formatarNumero(ataque.custoAprimorado)],
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

  detalhe?.querySelectorAll("[data-ataque-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-ataque-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-ataque-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });

  return { abrirDetalhe };
}

export function inicializarWikiAtaques(idDados = "ataques-data") {
  const dados = lerJson(idDados);
  const app = document.querySelector("[data-ataques-app]");
  if (!dados || !app) return;

  const grid = app.querySelector("[data-ataques-grid]");
  const busca = app.querySelector("[data-ataques-search]");
  const ordenacao = app.querySelector("[data-ataques-sort]");
  const direcaoBotao = app.querySelector("[data-ataques-direction]");
  const filtroEstilo = app.querySelector("[data-ataques-style]");
  const filtroMotor = app.querySelector("[data-ataques-motor]");
  const filtroFoco = app.querySelector("[data-ataques-focus]");
  const tipoChips = [...app.querySelectorAll("[data-ataques-type-chip]")];
  const contador = app.querySelector("[data-ataques-count]");
  const botaoLimpar = app.querySelector("[data-ataques-clear]");
  const vazio = app.querySelector("[data-ataques-empty]");
  const sentinela = app.querySelector("[data-ataques-sentinel]");
  const PAGE_SIZE = 36;
  const RENDER_DELAY = 18;
  let tipoSelecionado = "";
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

  function atualizarChipsTipo() {
    tipoChips.forEach((chip) => {
      const ativo = chip.dataset.ataquesTypeChip === tipoSelecionado;
      chip.classList.toggle("ativo", ativo);
      chip.setAttribute("aria-pressed", ativo ? "true" : "false");
    });
  }

  function obterResultado() {
    const termo = normalizar(busca?.value ?? "");
    const estilo = filtroEstilo?.value ?? "";
    const motor = filtroMotor?.value ?? "";
    const foco = filtroFoco?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
    const direcao = direcaoAtual();

    const filtrados = (dados.ataques || []).filter((ataque) => {
      if (termo && !ataque.busca.includes(termo)) return false;
      if (tipoSelecionado && ataque.tipoBusca !== tipoSelecionado) return false;
      if (estilo && ataque.estiloBusca !== estilo) return false;
      if (motor && !ataque.motoresBusca.includes(motor)) return false;
      if (foco && ataque.focoPrincipalBusca !== foco) return false;
      return true;
    });

    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
      custo: (a, b) => (a.custo ?? 0) - (b.custo ?? 0),
      ofensivo: (a, b) => (a.ofensivo ?? 0) - (b.ofensivo ?? 0),
      defensivo: (a, b) => (a.defensivo ?? 0) - (b.defensivo ?? 0),
      suporte: (a, b) => (a.suporte ?? 0) - (b.suporte ?? 0),
      utilitario: (a, b) => (a.utilitario ?? 0) - (b.utilitario ?? 0),
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
    atualizarChipsTipo();
  }

  function anexarCard(inicio, fim) {
    if (!grid) return;
    const fragmento = document.createDocumentFragment();
    resultadoAtual.slice(inicio, fim).forEach((ataque) => {
      const card = criarCardAtaque(ataque, dados);
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
    if (filtroMotor) filtroMotor.value = "";
    if (filtroFoco) filtroFoco.value = "";
    tipoSelecionado = "";
    if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    renderLista(true);
  }

  grid?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-ataque-id]");
    if (card) detalheController.abrirDetalhe(card.dataset.ataqueId);
  });

  [busca, ordenacao, filtroEstilo, filtroMotor, filtroFoco].forEach((elemento) => {
    elemento?.addEventListener("input", () => renderLista(true));
    elemento?.addEventListener("change", () => renderLista(true));
  });

  tipoChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const tipo = chip.dataset.ataquesTypeChip || "";
      tipoSelecionado = tipoSelecionado === tipo ? "" : tipo;
      renderLista(true);
    });
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
