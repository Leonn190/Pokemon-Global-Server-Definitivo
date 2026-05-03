import { aplicarImagemDetalhe, criarGridProgressiva, html, lerJson } from "./WikiRuntimeBase.js";
function assetEstrutura(estrutura, dados) {
  return dados.assetsEstruturas?.[estrutura.id] ?? { imagem: null };
}
function criarCardEstrutura(estrutura, dados) {
  const asset = assetEstrutura(estrutura, dados);
  const card = document.createElement("button");
  card.type = "button";
  card.className = "item-card mundo-card";
  card.dataset.mundoEstruturaId = estrutura.id;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(estrutura.id)}</span>
    <span class="item-card-arte mundo-card-arte">
      ${asset.imagem ? `<img src="${asset.imagem}" alt="${html(estrutura.nome)}" loading="lazy" decoding="async" />` : `<span class="item-card-sem-arte">${html(estrutura.nome.slice(0, 1))}</span>`}
    </span>
    <span class="item-card-nome">${html(estrutura.nome)}</span>
    <span class="item-card-meta mundo-card-material">${html(estrutura.material || "Sem material")}</span>
  `;
  return card;
}
function montarLinhasInfo(estrutura) {
  return [
    ["Material", estrutura.material || "Sem material"],
    ["Ferramenta", estrutura.ferramenta],
    ["Dureza", estrutura.durezaTexto],
    ["Quantidade", estrutura.quantidadeTexto],
    ["Onde aparece", estrutura.biomasTexto],
    ["Coletável", estrutura.dropAtivo ? "Sim" : "Não"],
    ["Colisão", estrutura.raioColisaoTexto],
    ["Interação", estrutura.raioInteracaoTexto],
    ["Inquebrável", estrutura.inquebravel ? "Sim" : "Não"],
  ];
}
function criarControladorDetalhe(dados) {
  const detalhe = document.querySelector("[data-mundo-detail]");
  let estruturaAberta = null;
  function listaNavegacao() {
    return [...(dados.estruturas || [])].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }
  function abrirVizinho(direcao) {
    if (!estruturaAberta) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((estrutura) => String(estrutura.id) === String(estruturaAberta.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proxima = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proxima) abrirDetalhe(proxima.id);
  }
  function abrirDetalhe(id) {
    const estrutura = (dados.estruturas || []).find((atual) => atual.id === String(id));
    if (!estrutura || !detalhe) return;
    estruturaAberta = estrutura;
    const asset = assetEstrutura(estrutura, dados);
    const imagem = detalhe.querySelector("[data-mundo-image]");
    const codigo = detalhe.querySelector("[data-mundo-code]");
    const nome = detalhe.querySelector("[data-mundo-name]");
    const descricao = detalhe.querySelector("[data-mundo-description]");
    const info = detalhe.querySelector("[data-mundo-info]");
    const biomas = detalhe.querySelector("[data-mundo-biomes]");
    if (codigo) codigo.textContent = `#${estrutura.id}`;
    if (nome) nome.textContent = estrutura.nome;
    if (descricao) descricao.textContent = estrutura.descricao || "Estrutura natural registrada nas regras do mundo.";
    aplicarImagemDetalhe(imagem, asset.imagem, estrutura.nome);
    if (info) {
      info.innerHTML = montarLinhasInfo(estrutura)
        .map(([chave, valor]) => `<div><dt>${html(chave)}</dt><dd>${html(valor)}</dd></div>`)
        .join("");
    }
    if (biomas) {
      const listaBiomas = Array.isArray(estrutura.biomas) && estrutura.biomas.length
        ? estrutura.biomas.map((bioma) => bioma.nome)
        : [estrutura.biomasTexto];
      biomas.innerHTML = listaBiomas.map((bioma) => `<span>${html(bioma)}</span>`).join("");
    }
    detalhe.hidden = false;
    document.body.classList.add("detalhe-aberto");
  }
  function fecharDetalhe() {
    if (detalhe) detalhe.hidden = true;
    document.body.classList.remove("detalhe-aberto");
  }
  detalhe?.querySelectorAll("[data-mundo-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-mundo-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-mundo-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });
  return { abrirDetalhe };
}
export function inicializarWikiMundo(idDados = "mundo-data") {
  const dados = lerJson(idDados);
  const app = document.querySelector("[data-mundo-app]");
  if (!dados || !app) return;
  const grid = app.querySelector("[data-mundo-estruturas-grid]");
  const detalheController = criarControladorDetalhe(dados);
  criarGridProgressiva({
    grid,
    itens: dados.estruturas || [],
    criarCard: (estrutura) => criarCardEstrutura(estrutura, dados),
    cardSelector: "[data-mundo-estrutura-id]",
    obterCardId: (card) => card.dataset.mundoEstruturaId,
    abrirDetalhe: detalheController.abrirDetalhe,
  })?.iniciar();
}
