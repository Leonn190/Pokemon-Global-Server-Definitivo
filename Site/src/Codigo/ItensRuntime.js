function normalizar(valor) {
  return String(valor ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function html(valor) {
  return String(valor ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#039;",
    '"': "&quot;",
  })[char]);
}

function lerJson(id) {
  const node = document.getElementById(id);
  if (!node) return null;
  try {
    return JSON.parse(node.textContent || "{}");
  } catch (erro) {
    console.error(`[Wiki Itens] Não consegui ler os dados de ${id}.`, erro);
    return null;
  }
}

function formatarNumero(valor, sufixo = "") {
  if (valor === null || valor === undefined || valor === "" || Number.isNaN(Number(valor))) return "-";
  const numero = Number(valor);
  const texto = Number.isInteger(numero) ? String(numero) : numero.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  return `${texto}${sufixo}`;
}

function assetItem(item, assetsItens) {
  return assetsItens?.[item.id] ?? { imagem: null };
}

function criarCardItem(item, dados) {
  const asset = assetItem(item, dados.assetsItens);
  const card = document.createElement("button");
  card.type = "button";
  card.className = `item-card ${item.raridadeClasse || "raridade-comum"}`;
  card.dataset.itemId = item.id;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(item.id)}</span>
    <span class="item-card-arte">
      ${asset.imagem ? `<img src="${asset.imagem}" alt="${html(item.nome)}" loading="lazy" decoding="async" />` : `<span class="item-card-sem-arte">${html(item.nome.slice(0, 1))}</span>`}
    </span>
    <span class="item-card-nome">${html(item.nome)}</span>
    <span class="item-card-meta">${html(item.estiloRotulo)}</span>
    <span class="item-card-linha"><strong>${formatarNumero(item.valor)}</strong><small>Valor médio</small></span>
    <span class="raridade-pill ${html(item.raridadeClasse)}">${html(item.raridadeNome)}</span>
  `;
  return card;
}

function criarControladorDetalhe(dados, obterListaAtual) {
  const detalhe = document.querySelector("[data-item-detail]");
  let itemAberto = null;

  function listaNavegacao() {
    const listaAtual = typeof obterListaAtual === "function" ? obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.itens || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }

  function abrirVizinho(direcao) {
    if (!itemAberto) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((item) => String(item.id) === String(itemAberto.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.id);
  }

  function abrirDetalhe(id) {
    const item = (dados.itens || []).find((atual) => atual.id === String(id));
    if (!item || !detalhe) return;
    itemAberto = item;
    const asset = assetItem(item, dados.assetsItens);
    const imagem = detalhe.querySelector("[data-item-image]");
    const codigo = detalhe.querySelector("[data-item-code]");
    const nome = detalhe.querySelector("[data-item-name]");
    const raridade = detalhe.querySelector("[data-item-rarity]");
    const descricao = detalhe.querySelector("[data-item-description]");
    const info = detalhe.querySelector("[data-item-info]");

    if (codigo) codigo.textContent = `#${item.id}`;
    if (nome) nome.textContent = item.nome;
    if (raridade) {
      raridade.className = `raridade-pill ${item.raridadeClasse || "raridade-comum"}`;
      raridade.textContent = item.raridadeNome;
    }
    if (descricao) descricao.textContent = item.descricaoMelhor || "Descrição detalhada ainda não cadastrada.";

    if (imagem) {
      if (asset.imagem) {
        imagem.hidden = false;
        imagem.src = asset.imagem;
        imagem.alt = item.nome;
      } else {
        imagem.hidden = true;
        imagem.removeAttribute("src");
      }
    }

    if (info) {
      const linhas = [
        ["Valor médio", formatarNumero(item.valor)],
        ["Estilo", item.estiloRotulo],
        ["Aparece em baús", item.bauTexto],
        ["Venda", item.vendaTexto],
        ["Stacks", formatarNumero(item.stacks)],
        ["Raridade", item.raridadeNome],
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

  detalhe?.querySelectorAll("[data-item-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-item-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-item-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });

  return { abrirDetalhe };
}

export function inicializarWikiItens(idDados = "itens-data") {
  const dados = lerJson(idDados);
  const app = document.querySelector("[data-itens-app]");
  if (!dados || !app) return;

  const grid = app.querySelector("[data-itens-grid]");
  const busca = app.querySelector("[data-itens-search]");
  const ordenacao = app.querySelector("[data-itens-sort]");
  const direcaoBotao = app.querySelector("[data-itens-direction]");
  const filtroEstilo = app.querySelector("[data-itens-style]");
  const filtroRaridade = app.querySelector("[data-itens-rarity]");
  const filtroBau = app.querySelector("[data-itens-chest]");
  const filtroVenda = app.querySelector("[data-itens-sale]");
  const contador = app.querySelector("[data-itens-count]");
  const botaoLimpar = app.querySelector("[data-itens-clear]");
  const vazio = app.querySelector("[data-itens-empty]");
  const sentinela = app.querySelector("[data-itens-sentinel]");
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
    const raridade = filtroRaridade?.value ?? "";
    const bau = filtroBau?.value ?? "";
    const venda = filtroVenda?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
    const direcao = direcaoAtual();

    const filtrados = (dados.itens || []).filter((item) => {
      if (termo && !item.busca.includes(termo)) return false;
      if (estilo && item.estiloBusca !== estilo) return false;
      if (raridade && String(item.raridadeNumero) !== raridade) return false;
      if (bau && (item.bau ? "s" : "n") !== bau) return false;
      if (venda && item.vendaCodigo !== venda) return false;
      return true;
    });

    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
      valor: (a, b) => (a.valor ?? 0) - (b.valor ?? 0),
      raridade: (a, b) => (a.raridadeNumero ?? 0) - (b.raridadeNumero ?? 0),
      estilo: (a, b) => a.estiloRotulo.localeCompare(b.estiloRotulo, "pt-BR", { numeric: true }),
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
    resultadoAtual.slice(inicio, fim).forEach((item) => {
      const card = criarCardItem(item, dados);
      card.classList.add("pokemon-card-entrando");
      fragmento.appendChild(card);
    });
    grid.appendChild(fragmento);
  }

  function renderizarAte(limite, idRender) {
    if (!grid || idRender !== renderRequest) return;
    const jaRenderizados = grid.children.length;
    const alvo = Math.min(limite, resultadoAtual.length);
    if (jaRenderizados >= alvo) {
      renderizando = false;
      atualizarEstado();
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
    const idRender = ++renderRequest;
    if (!grid) return;
    if (reset) {
      resultadoAtual = obterResultado();
      visiveis = Math.min(PAGE_SIZE, resultadoAtual.length);
      grid.replaceChildren();
      renderizando = false;
      atualizarEstado();
      renderizarAte(visiveis, idRender);
      return;
    }
    if (renderizando || visiveis >= resultadoAtual.length) return;
    visiveis = Math.min(visiveis + PAGE_SIZE, resultadoAtual.length);
    atualizarEstado();
    renderizarAte(visiveis, idRender);
  }

  [busca, ordenacao, filtroEstilo, filtroRaridade, filtroBau, filtroVenda].forEach((controle) => {
    controle?.addEventListener("input", () => renderLista(true));
    controle?.addEventListener("change", () => renderLista(true));
  });

  direcaoBotao?.addEventListener("click", () => {
    direcaoBotao.dataset.sortDirection = direcaoAtual() === "asc" ? "desc" : "asc";
    atualizarDirecao();
    renderLista(true);
  });

  botaoLimpar?.addEventListener("click", () => {
    if (busca) busca.value = "";
    if (ordenacao) ordenacao.value = "ordem";
    if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    if (filtroEstilo) filtroEstilo.value = "";
    if (filtroRaridade) filtroRaridade.value = "";
    if (filtroBau) filtroBau.value = "";
    if (filtroVenda) filtroVenda.value = "";
    renderLista(true);
  });

  grid?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-item-id]");
    if (!card) return;
    detalheController.abrirDetalhe(card.dataset.itemId);
  });

  if (sentinela && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entradas) => {
      if (entradas.some((entrada) => entrada.isIntersecting)) renderLista(false);
    }, { rootMargin: "360px 0px" });
    observer.observe(sentinela);
  } else {
    window.addEventListener("scroll", () => {
      const restante = document.documentElement.scrollHeight - window.scrollY - window.innerHeight;
      if (restante < 360) renderLista(false);
    }, { passive: true });
  }

  atualizarDirecao();
  renderLista(true);
}
