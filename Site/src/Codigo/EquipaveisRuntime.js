import { aplicarImagemDetalhe, criarListagemPaginada, formatarNumero, html, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";
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
    const focos = detalhe.querySelector("[data-equipavel-focus-bars]");
    if (codigo) codigo.textContent = `#${equipavel.id}`;
    if (nome) nome.textContent = equipavel.nome;
    if (descricao) descricao.textContent = equipavel.descricao || "Descrição ainda não cadastrada.";
    aplicarImagemDetalhe(imagem, asset.imagem, equipavel.nome);
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
    if (focos) focos.innerHTML = focoBarrasHtml(equipavel);
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
  let tipoSelecionado = "";
  let listagem;
  const detalheController = criarControladorDetalhe(dados, () => listagem?.obterResultadoAtual() ?? []);
  function atualizarChipsTipo() {
    tipoChips.forEach((chip) => {
      const ativo = chip.dataset.equipaveisTypeChip === tipoSelecionado;
      chip.classList.toggle("ativo", ativo);
      chip.setAttribute("aria-pressed", ativo ? "true" : "false");
    });
  }
  function obterResultado(direcao) {
    const termo = normalizar(busca?.value ?? "");
    const atributo = filtroAtributo?.value ?? "";
    const foco = filtroFoco?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
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
    return ordenarComDirecao(filtrados, ordenadores, sort, direcao);
  }
  listagem = criarListagemPaginada({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    controles: [busca, ordenacao, filtroAtributo, filtroFoco],
    botaoLimpar,
    cardSelector: "[data-equipavel-id]",
    obterCardId: (card) => card.dataset.equipavelId,
    abrirDetalhe: (id) => detalheController.abrirDetalhe(id),
    criarCard: (equipavel) => criarCardEquipavel(equipavel, dados),
    obterResultado,
    aoAtualizarEstado: atualizarChipsTipo,
    limparFiltros: () => {
      if (busca) busca.value = "";
      if (ordenacao) ordenacao.value = "ordem";
      if (filtroAtributo) filtroAtributo.value = "";
      if (filtroFoco) filtroFoco.value = "";
      if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
      tipoSelecionado = "";
    },
  });
  tipoChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      tipoSelecionado = tipoSelecionado === chip.dataset.equipaveisTypeChip ? "" : chip.dataset.equipaveisTypeChip;
      listagem.renderLista(true);
    });
  });
  listagem.iniciar();
}
