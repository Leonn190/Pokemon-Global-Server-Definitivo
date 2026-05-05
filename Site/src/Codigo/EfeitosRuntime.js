import { infoHtml, aplicarImagemDetalhe, criarWikiCatalogo, html, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";
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
    aplicarImagemDetalhe(imagem, asset.imagem, efeito.nome);
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
      info.innerHTML = infoHtml(linhas);
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
  let listagem;
  const detalheController = criarControladorDetalhe(dados, () => listagem?.obterResultadoAtual() ?? []);
  function obterResultado(direcao) {
    const termo = normalizar(busca?.value ?? "");
    const estilo = filtroEstilo?.value ?? "";
    const sentido = filtroSentido?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
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
    return ordenarComDirecao(filtrados, ordenadores, sort, direcao);
  }
  listagem = criarWikiCatalogo({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    controles: [busca, ordenacao, filtroEstilo, filtroSentido],
    botaoLimpar,
    cardSelector: "[data-efeito-id]",
    obterCardId: (card) => card.dataset.efeitoId,
    abrirDetalhe: (id) => detalheController.abrirDetalhe(id),
    criarCard: (efeito) => criarCardEfeito(efeito, dados),
    obterResultado,
    limparFiltros: () => {
      if (busca) busca.value = "";
      if (ordenacao) ordenacao.value = "ordem";
      if (filtroEstilo) filtroEstilo.value = "";
      if (filtroSentido) filtroSentido.value = "";
      if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    },
  });
  listagem.iniciar();
}
