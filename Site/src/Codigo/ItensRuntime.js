import { fecharModalDetalhe, abrirModalDetalhe, infoHtml, aplicarImagemDetalhe, criarWikiCatalogo, formatarNumero, html, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";
function assetItem(item, assetsItens) {
  return assetsItens?.[item.id] ?? { imagem: null };
}
export function criarCardItem(item, dados) {
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
function itemPorId(dados, id) {
  return (dados.itens || []).find((item) => String(item.id) === String(id));
}
function imagemCelulaReceita(celula, dados) {
  if (!celula?.itemId) return null;
  return assetItem({ id: celula.itemId }, dados.assetsItens).imagem;
}
function receitaCelulaHtml(celula, dados) {
  if (!celula) return `<span class="item-receita-celula vazia" aria-hidden="true"></span>`;
  const item = itemPorId(dados, celula.itemId);
  const imagem = imagemCelulaReceita(celula, dados);
  const nome = item?.nome || celula.nome;
  const quantidade = Number(celula.quantidade) > 1 ? `<b>x${html(celula.quantidade)}</b>` : "";
  return `
    <span class="item-receita-celula preenchida" title="${html(nome)}">
      ${imagem ? `<img src="${imagem}" alt="" loading="lazy" decoding="async" />` : `<i>${html(nome.slice(0, 1))}</i>`}
      <small>${html(nome)}</small>
      ${quantidade}
    </span>
  `;
}
function receitaHtml(item, dados) {
  const linhas = item.receita?.matriz || [];
  const celulas = linhas.flat().slice(0, 9);
  while (celulas.length < 9) celulas.push(null);
  return celulas.map((celula) => receitaCelulaHtml(celula, dados)).join("");
}
export function criarControladorDetalheItens(dados, obterListaAtual) {
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
    const receitaPainel = detalhe.querySelector("[data-item-recipe-panel]");
    const receitaResumo = detalhe.querySelector("[data-item-recipe-summary]");
    const receitaGrade = detalhe.querySelector("[data-item-recipe-grid]");
    if (codigo) codigo.textContent = `#${item.id}`;
    if (nome) nome.textContent = item.nome;
    if (raridade) {
      raridade.className = `raridade-pill ${item.raridadeClasse || "raridade-comum"}`;
      raridade.textContent = item.raridadeNome;
    }
    if (descricao) descricao.textContent = item.descricaoMelhor || "Descrição detalhada ainda não cadastrada.";
    aplicarImagemDetalhe(imagem, asset.imagem, item.nome);
    if (info) {
      const linhas = [
        ["Valor médio", formatarNumero(item.valor)],
        ["Estilo", item.estiloRotulo],
        ["Aparece em baús", item.bauTexto],
        ["Venda", item.vendaTexto],
        ["Stacks", formatarNumero(item.stacks)],
        ["Raridade", item.raridadeNome],
      ];
      info.innerHTML = infoHtml(linhas);
    }
    if (receitaPainel && receitaGrade && receitaResumo) {
      const temReceita = !!item.receita?.matriz;
      receitaPainel.hidden = !temReceita;
      if (temReceita) {
        const quantidade = Number(item.receita.quantidadeResultado || 1);
        receitaResumo.innerHTML = `<span>Resultado</span><strong>${html(item.nome)}</strong>${quantidade > 1 ? `<em>x${html(quantidade)}</em>` : ""}`;
        receitaGrade.innerHTML = receitaHtml(item, dados);
      } else {
        receitaResumo.innerHTML = "";
        receitaGrade.innerHTML = "";
      }
    }
    abrirModalDetalhe(detalhe);
  }
  function fecharDetalhe() {
    fecharModalDetalhe(detalhe);
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
  let listagem;
  const detalheController = criarControladorDetalheItens(dados, () => listagem?.obterResultadoAtual() ?? []);
  function obterResultado(direcao) {
    const termo = normalizar(busca?.value ?? "");
    const estilo = filtroEstilo?.value ?? "";
    const raridade = filtroRaridade?.value ?? "";
    const bau = filtroBau?.value ?? "";
    const venda = filtroVenda?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
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
    return ordenarComDirecao(filtrados, ordenadores, sort, direcao);
  }
  listagem = criarWikiCatalogo({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    controles: [busca, ordenacao, filtroEstilo, filtroRaridade, filtroBau, filtroVenda],
    botaoLimpar,
    usarFallbackScroll: true,
    cardSelector: "[data-item-id]",
    obterCardId: (card) => card.dataset.itemId,
    abrirDetalhe: (id) => detalheController.abrirDetalhe(id),
    criarCard: (item) => criarCardItem(item, dados),
    obterResultado,
    limparFiltros: () => {
      if (busca) busca.value = "";
      if (ordenacao) ordenacao.value = "ordem";
      if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
      if (filtroEstilo) filtroEstilo.value = "";
      if (filtroRaridade) filtroRaridade.value = "";
      if (filtroBau) filtroBau.value = "";
      if (filtroVenda) filtroVenda.value = "";
    },
  });
  listagem.iniciar();
}
