import { fecharModalDetalhe, abrirModalDetalhe, aplicarImagemDetalhe, criarWikiCatalogo, formatarNumero, html, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";
function assetAtaque(ataque, dados) {
  return dados.assetsAtaques?.[ataque.uid] ?? dados.assetsAtaques?.[ataque.id] ?? { imagem: null };
}
function tipoIcone(tipo, dados, classe = "tipo-bola pequena") {
  const chave = normalizar(tipo);
  const src = dados.iconesTipos?.[chave];
  if (src) return `<span class="${classe}" data-tipo="${html(chave)}"><img src="${src}" alt="" loading="lazy" decoding="async" /></span>`;
  return `<span class="${classe}" data-tipo="${html(chave)}"><b>${html(String(tipo || "?").slice(0, 1).toUpperCase())}</b></span>`;
}
function focoBarrasHtml(item) {
  const focos = [
    ["Ofensivo", item.ofensivo, 100],
    ["Defensivo", item.defensivo, 100],
    ["Suporte", item.suporte, 100],
    ["Utilitário", item.utilitario, 100],
    ["Custo", item.custo, 150],
  ];
  return `<div class="foco-barras">${focos.map(([rotulo, valor, maximo]) => {
    const numero = Math.max(0, Number(valor) || 0);
    const largura = Math.max(0, Math.min(100, (numero / maximo) * 100));
    return `
      <div class="foco-barra">
        <div class="foco-barra-topo"><span>${html(rotulo)}</span><strong>${formatarNumero(numero)}</strong></div>
        <div class="foco-barra-trilho"><span style="width: ${largura}%"></span></div>
      </div>
    `;
  }).join("")}</div>`;
}
function criarCardAtaque(ataque, dados) {
  const asset = assetAtaque(ataque, dados);
  const card = document.createElement("button");
  card.type = "button";
  card.className = "item-card ataque-card";
  card.dataset.ataqueId = ataque.uid || ataque.id;
  card.dataset.tipo = ataque.tipoBusca || "";
  card.innerHTML = `
    <span class="item-card-codigo">#${html(ataque.codigoExibicao || ataque.id)}</span>
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
    const indiceAtual = lista.findIndex((ataque) => String(ataque.uid || ataque.id) === String(ataqueAberto.uid || ataqueAberto.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.uid || proximo.id);
  }
  function abrirDetalhe(id) {
    const ataque = (dados.ataques || []).find((atual) => String(atual.uid || atual.id) === String(id));
    if (!ataque || !detalhe) return;
    ataqueAberto = ataque;
    const asset = assetAtaque(ataque, dados);
    const imagem = detalhe.querySelector("[data-ataque-image]");
    const codigo = detalhe.querySelector("[data-ataque-code]");
    const nome = detalhe.querySelector("[data-ataque-name]");
    const tags = detalhe.querySelector("[data-ataque-tags]");
    const descricao = detalhe.querySelector("[data-ataque-description]");
    const aprimoramento = detalhe.querySelector("[data-ataque-upgrade]");
    const focos = detalhe.querySelector("[data-ataque-focus-bars]");
    if (codigo) codigo.textContent = `#${ataque.codigoExibicao || ataque.id}`;
    if (nome) nome.textContent = ataque.nome;
    aplicarImagemDetalhe(imagem, asset.imagem, ataque.nome);
    if (tags) {
      tags.innerHTML = `
        <span class="tipo-badge">${tipoIcone(ataque.tipo, dados)}${html(ataque.tipo)}</span>
        <span class="tag-extra">${html(ataque.estiloRotulo)}</span>
      `;
    }
    if (descricao) descricao.textContent = ataque.descricao || "Descrição ainda não cadastrada.";
    if (aprimoramento) {
      aprimoramento.innerHTML = `<p>${html(ataque.aprimoramento || "Aprimoramento ainda não cadastrado.")}</p><span class="custo-aprimoramento">Custo após aprimoramento: ${formatarNumero(ataque.custoAprimorado)}</span>`;
    }
    if (focos) focos.innerHTML = focoBarrasHtml(ataque);
    abrirModalDetalhe(detalhe);
  }
  function fecharDetalhe() {
    fecharModalDetalhe(detalhe);
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
  let tipoSelecionado = "";
  let listagem;
  const detalheController = criarControladorDetalhe(dados, () => listagem?.obterResultadoAtual() ?? []);
  function atualizarChipsTipo() {
    tipoChips.forEach((chip) => {
      const ativo = chip.dataset.ataquesTypeChip === tipoSelecionado;
      chip.classList.toggle("ativo", ativo);
      chip.setAttribute("aria-pressed", ativo ? "true" : "false");
    });
  }
  function obterResultado(direcao) {
    const termo = normalizar(busca?.value ?? "");
    const estilo = filtroEstilo?.value ?? "";
    const motor = filtroMotor?.value ?? "";
    const foco = filtroFoco?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
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
    return ordenarComDirecao(filtrados, ordenadores, sort, direcao);
  }
  listagem = criarWikiCatalogo({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    controles: [busca, ordenacao, filtroEstilo, filtroMotor, filtroFoco],
    botaoLimpar,
    rootMargin: "220px",
    cardSelector: "[data-ataque-id]",
    obterCardId: (card) => card.dataset.ataqueId,
    abrirDetalhe: (id) => detalheController.abrirDetalhe(id),
    criarCard: (ataque) => criarCardAtaque(ataque, dados),
    obterResultado,
    aoAtualizarEstado: atualizarChipsTipo,
    limparFiltros: () => {
      if (busca) busca.value = "";
      if (ordenacao) ordenacao.value = "ordem";
      if (filtroEstilo) filtroEstilo.value = "";
      if (filtroMotor) filtroMotor.value = "";
      if (filtroFoco) filtroFoco.value = "";
      tipoSelecionado = "";
      if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    },
  });
  tipoChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const tipo = chip.dataset.ataquesTypeChip || "";
      tipoSelecionado = tipoSelecionado === tipo ? "" : tipo;
      listagem.renderLista(true);
    });
  });
  listagem.iniciar();
}
