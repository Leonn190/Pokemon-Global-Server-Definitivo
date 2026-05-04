import { criarCardNpc, criarControladorDetalheNpc } from "./NpcsRuntime.js";
import { criarControladorDetalhe as criarControladorPokemonDetalhe } from "./PokedexRuntime.js";
import { aplicarImagemDetalhe, criarGridProgressiva, html, lerJson } from "./WikiRuntimeBase.js";
function assetEstadio(estadio, dados) {
  return dados.assetsEstadios?.[estadio.id] ?? { imagem: null };
}
function criarCardEstadio(estadio, dados) {
  const asset = assetEstadio(estadio, dados);
  const card = document.createElement("button");
  card.type = "button";
  card.className = "item-card estadio-card";
  card.dataset.estadioId = estadio.id;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(estadio.id)}</span>
    <span class="item-card-arte estadio-card-arte">
      ${asset.imagem ? `<img src="${asset.imagem}" alt="${html(estadio.nome)}" loading="lazy" decoding="async" />` : `<span class="item-card-sem-arte">${html(estadio.nomeTipo.slice(0, 1))}</span>`}
    </span>
    <span class="item-card-nome">${html(estadio.nome)}</span>
  `;
  return card;
}
function agruparMembros(estadio, dados) {
  const porId = Object.fromEntries((dados.npcs || []).map((npc) => [npc.id, npc]));
  const membros = (estadio.membrosIds || []).map((id) => porId[id]).filter(Boolean);
  const grupos = [
    ["Líder", membros.filter((npc) => npc.cargoBusca === "lider")],
    ["Capitão", membros.filter((npc) => npc.cargoBusca === "capitao")],
    ["Desafiante", membros.filter((npc) => npc.cargoBusca === "desafiante")],
    ["Associados", membros.filter((npc) => !["lider", "capitao", "desafiante"].includes(npc.cargoBusca))],
  ];
  return grupos.filter(([, lista]) => lista.length);
}
function criarControladorEstadio(dados, obterListaAtual, npcController) {
  const detalhe = document.querySelector("[data-estadio-detail]");
  let estadioAberto = null;
  function listaNavegacao() {
    const listaAtual = typeof obterListaAtual === "function" ? obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.estadios || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }
  function abrirVizinho(direcao) {
    if (!estadioAberto) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((item) => String(item.id) === String(estadioAberto.id));
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.id);
  }
  function abrirDetalhe(id) {
    const estadio = (dados.estadios || []).find((item) => item.id === String(id));
    if (!estadio || !detalhe) return;
    estadioAberto = estadio;
    const asset = assetEstadio(estadio, dados);
    const imagem = detalhe.querySelector("[data-estadio-image]");
    const codigo = detalhe.querySelector("[data-estadio-code]");
    const nome = detalhe.querySelector("[data-estadio-name]");
    const tags = detalhe.querySelector("[data-estadio-tags]");
    const membros = detalhe.querySelector("[data-estadio-members]");
    if (codigo) codigo.textContent = `#${estadio.id}`;
    if (nome) nome.textContent = estadio.nome;
    if (tags) {
      tags.innerHTML = `
        <span class="tag-extra">Tipo ${html(estadio.nomeTipo)}</span>
        <span class="tag-extra">${html(estadio.membrosQuantidade)} associados</span>
      `;
    }
    aplicarImagemDetalhe(imagem, asset.imagem, estadio.nome);
    if (membros) {
      membros.replaceChildren();
      const grupos = agruparMembros(estadio, dados);
      if (!grupos.length) {
        membros.innerHTML = `<p class="wiki-vazio-texto">Nenhum membro cadastrado.</p>`;
      } else {
        const listaMembros = document.createElement("div");
        listaMembros.className = "estadio-membros-lista";
        grupos.forEach(([cargo, lista]) => {
          lista.forEach((npc) => {
            const item = document.createElement("article");
            item.className = "estadio-membro-item";
            item.innerHTML = `<h3>${html(cargo)}</h3>`;
            item.appendChild(criarCardNpc(npc, dados, "estadio"));
            listaMembros.appendChild(item);
          });
        });
        membros.appendChild(listaMembros);
      }
    }
    detalhe.hidden = false;
    document.body.classList.add("detalhe-aberto");
  }
  function fecharDetalhe() {
    if (detalhe) detalhe.hidden = true;
    document.body.classList.remove("detalhe-aberto");
  }
  detalhe?.querySelectorAll("[data-estadio-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-estadio-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-estadio-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  detalhe?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-npc-id]");
    if (!card) return;
    npcController.abrirDetalhe(card.dataset.npcId);
  });
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });
  return { abrirDetalhe };
}
export function inicializarWikiEstadios(idDados = "estadios-data") {
  const dados = lerJson(idDados);
  const pokedex = lerJson("estadios-pokedex-data");
  const app = document.querySelector("[data-estadios-app]");
  if (!dados || !pokedex || !app) return;
  const grid = app.querySelector("[data-estadios-grid]");
  if (!grid) return;
  const npcController = criarControladorDetalheNpc(dados, pokedex, {
    seletorDetalhe: "[data-estadio-npc-detail]",
    obterListaAtual: () => dados.npcs || [],
  });
  const pokemonController = criarControladorPokemonDetalhe(pokedex, {
    seletorDetalhe: "[data-estadio-pokemon-detail]",
    mostrarLinhagem: true,
  });
  const estadioController = criarControladorEstadio(dados, () => dados.estadios || [], npcController);
  criarGridProgressiva({
    grid,
    itens: dados.estadios || [],
    criarCard: (estadio) => criarCardEstadio(estadio, dados),
    cardSelector: "[data-estadio-id]",
    obterCardId: (card) => card.dataset.estadioId,
    abrirDetalhe: estadioController.abrirDetalhe,
  })?.iniciar();
  document.querySelector("[data-estadio-npc-detail]")?.addEventListener("click", (evento) => {
    const card = evento.target.closest("[data-pokemon-id]");
    if (!card) return;
    pokemonController.abrirDetalhe(card.dataset.pokemonId);
  });
}
