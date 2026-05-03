function lerJson(id) {
  const node = document.getElementById(id);
  if (!node) return null;
  try {
    return JSON.parse(node.textContent || "{}");
  } catch (erro) {
    console.error(`[Wiki Equipáveis] Não consegui ler os dados de ${id}.`, erro);
    return null;
  }
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

function assetEquipavel(equipavel, dados) {
  return dados.assetsEquipaveis?.[equipavel.id] ?? { imagem: null };
}

function tipoIcone(tipo, dados, classe = "tipo-bola pequena") {
  const chave = normalizar(tipo);
  const src = dados.iconesTipos?.[chave];
  if (src) return `<span class="${classe}"><img src="${src}" alt="" loading="lazy" decoding="async" /></span>`;
  return `<span class="${classe}"><b>${html(String(tipo || "?").slice(0, 1).toUpperCase())}</b></span>`;
}

function afinidadeHtml(equipavel, dados) {
  const afinidades = equipavel.afinidades?.length ? equipavel.afinidades : [equipavel.afinidade];
  const primeira = afinidades[0] || equipavel.afinidade;
  return `${tipoIcone(primeira, dados)}${html(equipavel.afinidade)}`;
}

function atributoIcone(atributo, dados) {
  const src = dados.iconesAtributos?.[normalizar(atributo.chave)] || dados.iconesAtributos?.[normalizar(atributo.rotulo)];
  return src ? `<img src="${src}" alt="" loading="lazy" decoding="async" />` : "";
}

function criarCardEquipavel(equipavel, dados) {
  const asset = assetEquipavel(equipavel, dados);
  const card = document.createElement("button");
  card.type = "button";
  card.className = "item-card equipavel-card";
  card.dataset.equipavelId = equipavel.id;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(equipavel.id)}</span>
    <span class="item-card-arte equipavel-card-arte">
      ${asset.imagem ? `<img src="${asset.imagem}" alt="${html(equipavel.nome)}" loading="lazy" decoding="async" />` : `<span class="item-card-sem-arte">${html(equipavel.nome.slice(0, 1))}</span>`}
    </span>
    <span class="item-card-nome">${html(equipavel.nome)}</span>
    <span class="item-card-meta equipavel-afinidade-card">${afinidadeHtml(equipavel, dados)}</span>
  `;
  return card;
}

function criarControladorDetalhe(dados, obterListaAtual) {
  const detalhe = document.querySelector("[data-equipavel-detail]");
  let equipavelAberto = null;

  function listaNavegacao() {
    const listaAtual = typeof obterListaAtual === "function" ? obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.equipaveis || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }

  function abrirVizinho(direcao) {
    if (!equipavelAberto) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((item) => String(item.id) === String(equipavelAberto.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.id);
  }

  function abrirDetalhe(id) {
    const equipavel = (dados.equipaveis || []).find((atual) => atual.id === String(id));
    if (!equipavel || !detalhe) return;
    equipavelAberto = equipavel;
    const asset = assetEquipavel(equipavel, dados);
    const imagem = detalhe.querySelector("[data-equipavel-image]");
    const codigo = detalhe.querySelector("[data-equipavel-code]");
    const nome = detalhe.querySelector("[data-equipavel-name]");
    const tags = detalhe.querySelector("[data-equipavel-tags]");
    const descricao = detalhe.querySelector("[data-equipavel-description]");
    const atributos = detalhe.querySelector("[data-equipavel-attributes]");
    const info = detalhe.querySelector("[data-equipavel-info]");

    if (codigo) codigo.textContent = `#${equipavel.id}`;
    if (nome) nome.textContent = equipavel.nome;
    if (descricao) descricao.textContent = equipavel.descricao || "Descrição ainda não cadastrada.";

    if (imagem) {
      if (asset.imagem) {
        imagem.hidden = false;
        imagem.src = asset.imagem;
        imagem.alt = equipavel.nome;
      } else {
        imagem.hidden = true;
        imagem.removeAttribute("src");
      }
    }

    if (tags) {
      tags.innerHTML = `
        <span class="tipo-badge">${afinidadeHtml(equipavel, dados)}</span>
        <span class="tag-extra">${html(equipavel.focoPrincipal)}</span>
      `;
    }

    if (atributos) {
      if (equipavel.aumentos?.length) {
        atributos.innerHTML = equipavel.aumentos.map((atributo) => `
          <div class="equipavel-atributo-linha">
            <span>${atributoIcone(atributo, dados)}${html(atributo.rotulo)}</span>
            <strong>${formatarNumero(atributo.valor)}</strong>
          </div>
        `).join("");
      } else {
        atributos.innerHTML = `<p class="wiki-vazio-texto">Nenhum aumento numérico cadastrado.</p>`;
      }
    }

    if (info) {
      const linhas = [
        ["Afinidade", equipavel.afinidade],
        ["Foco", equipavel.focoPrincipal],
        ["Maior aumento", equipavel.maiorAumento ? `${equipavel.maiorAumento} ${formatarNumero(equipavel.maiorAumentoValor)}` : "-"],
        ["Passiva", equipavel.passiva || "-"],
        ["Forma final", equipavel.formaFinal || "-"],
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

  detalhe?.querySelectorAll("[data-equipavel-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-equipavel-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-equipavel-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });

  return { abrirDetalhe };
}

export function inicializarWikiEquipaveis(idDados = "equipaveis-data") {
  const dados = lerJson(idDados);
  const app = document.querySelector("[data-equipaveis-app]");
  if (!dados || !app) return;

  const grid = app.querySelector("[data-equipaveis-grid]");
  const busca = app.querySelector("[data-equipaveis-search]");
  const ordenacao = app.querySelector("[data-equipaveis-sort]");
  const direcaoBotao = app.querySelector("[data-equipaveis-direction]");
  const filtroAtributo = app.querySelector("[data-equipaveis-attribute]");
  const filtroFoco = app.querySelector("[data-equipaveis-focus]");
  const tipoChips = [...app.querySelectorAll("[data-equipaveis-type-chip]")];
  const contador = app.querySelector("[data-equipaveis-count]");
  const botaoLimpar = app.querySelector("[data-equipaveis-clear]");
  const vazio = app.querySelector("[data-equipaveis-empty]");
  const sentinela = app.querySelector("[data-equipaveis-sentinel]");
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
      const ativo = chip.dataset.equipaveisTypeChip === tipoSelecionado;
      chip.classList.toggle("ativo", ativo);
      chip.setAttribute("aria-pressed", ativo ? "true" : "false");
    });
  }

  function obterResultado() {
    const termo = normalizar(busca?.value ?? "");
    const atributo = filtroAtributo?.value ?? "";
    const foco = filtroFoco?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
    const direcao = direcaoAtual();

    const filtrados = (dados.equipaveis || []).filter((equipavel) => {
      if (termo && !equipavel.busca.includes(termo)) return false;
      if (tipoSelecionado && !(equipavel.afinidadesBusca || [equipavel.afinidadeBusca]).includes(tipoSelecionado)) return false;
      if (atributo && !equipavel.atributosBusca.includes(atributo)) return false;
      if (foco && equipavel.focoPrincipalBusca !== foco) return false;
      return true;
    });

    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
      foco: (a, b) => a.focoPrincipal.localeCompare(b.focoPrincipal, "pt-BR", { numeric: true }),
      atributo: (a, b) => {
        const chave = atributo || "maiorAumento";
        const av = chave === "maiorAumento" ? Math.abs(a.maiorAumentoValor ?? 0) : Math.abs(a.atributos?.[chave] ?? 0);
        const bv = chave === "maiorAumento" ? Math.abs(b.maiorAumentoValor ?? 0) : Math.abs(b.atributos?.[chave] ?? 0);
        return av - bv;
      },
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
    resultadoAtual.slice(inicio, fim).forEach((equipavel) => {
      const card = criarCardEquipavel(equipavel, dados);
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
    if (!grid) return;
    if (reset) {
      const idRender = ++renderRequest;
      resultadoAtual = obterResultado();
      visiveis = Math.min(PAGE_SIZE, resultadoAtual.length);
      grid.replaceChildren();
      renderizando = false;
      atualizarEstado();
      renderizarAte(visiveis, idRender);
      return;
    }
    if (renderizando || visiveis >= resultadoAtual.length) return;
    const idRender = ++renderRequest;
    visiveis = Math.min(visiveis + PAGE_SIZE, resultadoAtual.length);
    atualizarEstado();
    renderizarAte(visiveis, idRender);
  }

  [busca, ordenacao, filtroAtributo, filtroFoco].forEach((controle) => {
    controle?.addEventListener("input", () => renderLista(true));
    controle?.addEventListener("change", () => renderLista(true));
  });

  tipoChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      tipoSelecionado = tipoSelecionado === chip.dataset.equipaveisTypeChip ? "" : chip.dataset.equipaveisTypeChip;
      renderLista(true);
    });
  });

  direcaoBotao?.addEventListener("click", () => {
    direcaoBotao.dataset.sortDirection = direcaoAtual() === "asc" ? "desc" : "asc";
    renderLista(true);
  });

  botaoLimpar?.addEventListener("click", () => {
    if (busca) busca.value = "";
    if (ordenacao) ordenacao.value = "ordem";
    if (filtroAtributo) filtroAtributo.value = "";
    if (filtroFoco) filtroFoco.value = "";
    if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    tipoSelecionado = "";
    renderLista(true);
  });

  grid?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-equipavel-id]");
    if (!card) return;
    detalheController.abrirDetalhe(card.dataset.equipavelId);
  });

  if (sentinela && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entradas) => {
      if (entradas.some((entrada) => entrada.isIntersecting)) renderLista(false);
    }, { rootMargin: "360px 0px" });
    observer.observe(sentinela);
  }

  atualizarDirecao();
  renderLista(true);
}
