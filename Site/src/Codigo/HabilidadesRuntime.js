import { abrirModalDetalhe, criarWikiCatalogo, fecharModalDetalhe, html, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";

function criarCardHabilidade(skill) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = `item-card habilidade-card habilidade-${skill.ramo}`;
  card.dataset.skillId = skill.id;
  card.innerHTML = `
    <span class="item-card-codigo">#${html(skill.codigo || skill.id)}</span>
    <span class="item-card-arte habilidade-card-arte" aria-hidden="true"><span class="item-card-sem-arte habilidade-card-emoji">${html(skill.grupoEmoji || "✦")}</span></span>
    <span class="item-card-nome">${html(skill.nome)}</span>
    <span class="item-card-meta">${html(skill.sigla || `N${skill.nivel}`)}</span>
    <span class="item-card-linha"><strong>${html(skill.grupoRotulo)}</strong><small>Grupo</small></span>
  `;
  return card;
}

function criarCardGrupoHabilidade(skill, atualId) {
  const selecionada = String(skill.id) === String(atualId);
  return `
    <button type="button" class="habilidade-grupo-card${selecionada ? " atual" : ""}" data-skill-related-id="${html(skill.id)}">
      <span class="habilidade-grupo-id">#${html(skill.codigo || skill.id)}</span>
      <span class="habilidade-grupo-icone" aria-hidden="true">${html(skill.grupoEmoji || "✦")}</span>
      <strong>${html(skill.nome)}</strong>
      <small>${html(skill.sigla || `N${skill.nivel}`)}</small>
    </button>
  `;
}

function criarControladorDetalhe(dados, obterListaAtual) {
  const detalhe = document.querySelector("[data-skill-detail]");
  let skillAberta = null;

  function listaNavegacao() {
    const listaAtual = typeof obterListaAtual === "function" ? obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.habilidades || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }

  function abrirVizinho(direcao) {
    if (!skillAberta) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((skill) => skill.id === skillAberta.id);
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proxima = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proxima) abrirDetalhe(proxima.id);
  }

  function abrirDetalhe(id) {
    const skill = (dados.habilidades || []).find((item) => item.id === String(id));
    if (!skill || !detalhe) return;
    skillAberta = skill;
    const icone = detalhe.querySelector("[data-skill-icon]");
    const nome = detalhe.querySelector("[data-skill-name]");
    const descricao = detalhe.querySelector("[data-skill-description]");
    const tags = detalhe.querySelector("[data-skill-tags]");
    const efeitos = detalhe.querySelector("[data-skill-effects]");
    const pais = detalhe.querySelector("[data-skill-parents]");
    const grupo = detalhe.querySelector("[data-skill-group]");

    if (icone) icone.textContent = skill.grupoEmoji || "✦";
    if (nome) nome.textContent = skill.nome;
    if (descricao) descricao.textContent = skill.descricao || "Descrição ainda não cadastrada.";
    if (tags) {
      tags.innerHTML = `
        <span>${html(skill.ramoRotulo)}</span>
        <span>Nível ${html(skill.nivel)}</span>
        <span>${html(skill.grupoRotulo)}</span>
      `;
    }
    if (efeitos) {
      efeitos.innerHTML = (skill.efeitos || []).length
        ? skill.efeitos.map((efeito) => `<span><strong>${html(efeito.chave)}</strong>${html(efeito.texto.replace(`${efeito.chave}:`, "").trim())}</span>`).join("")
        : `<p>Sem efeito técnico catalogado.</p>`;
    }
    if (pais) {
      pais.innerHTML = (skill.pais || []).length
        ? skill.pais.map((pai) => `<code>${html(pai)}</code>`).join("")
        : `<code>root</code>`;
    }
    if (grupo) {
      const mesmoGrupo = (dados.habilidades || [])
        .filter((item) => item.grupoChave === skill.grupoChave)
        .sort((a, b) => (a.nivel - b.nivel) || (a.ordem - b.ordem));
      grupo.innerHTML = mesmoGrupo.length
        ? mesmoGrupo.map((item) => criarCardGrupoHabilidade(item, skill.id)).join("")
        : `<p class="wiki-vazio-texto">Nenhuma outra habilidade cadastrada no grupo ${html(skill.grupoRotulo)}.</p>`;
      grupo.querySelectorAll("[data-skill-related-id]").forEach((botao) => {
        botao.addEventListener("click", () => abrirDetalhe(botao.dataset.skillRelatedId));
      });
    }
    abrirModalDetalhe(detalhe);
  }

  function fecharDetalhe() {
    fecharModalDetalhe(detalhe);
  }

  detalhe?.querySelectorAll("[data-skill-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-skill-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-skill-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });
  return { abrirDetalhe };
}

export function inicializarWikiHabilidades() {
  const dados = lerJson("habilidades-data", "Wiki Habilidades");
  const app = document.querySelector("[data-habilidades-app]");
  if (!dados || !app) return;
  const grid = app.querySelector("[data-habilidades-grid]");
  const busca = app.querySelector("[data-habilidades-search]");
  const ordenacao = app.querySelector("[data-habilidades-sort]");
  const filtroRamo = app.querySelector("[data-habilidades-branch]");
  const filtroNivel = app.querySelector("[data-habilidades-level]");
  const contador = app.querySelector("[data-habilidades-count]");
  const direcaoBotao = app.querySelector("[data-habilidades-direction]");
  const botaoLimpar = app.querySelector("[data-habilidades-clear]");
  const vazio = app.querySelector("[data-habilidades-empty]");
  const sentinela = app.querySelector("[data-habilidades-sentinel]");
  let listagem;
  const detalheController = criarControladorDetalhe(dados, () => listagem?.obterResultadoAtual() ?? []);

  function obterResultado(direcao) {
    const termo = normalizar(busca?.value ?? "");
    const ramo = filtroRamo?.value ?? "";
    const nivel = filtroNivel?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
    const filtradas = (dados.habilidades || []).filter((skill) => {
      if (termo && !skill.busca.includes(termo)) return false;
      if (ramo && skill.ramo !== ramo) return false;
      if (nivel && String(skill.nivel) !== String(nivel)) return false;
      return true;
    });
    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
      nivel: (a, b) => a.nivel - b.nivel,
      ramo: (a, b) => a.ramoRotulo.localeCompare(b.ramoRotulo, "pt-BR", { numeric: true }),
      grupo: (a, b) => a.grupoRotulo.localeCompare(b.grupoRotulo, "pt-BR", { numeric: true }),
    };
    return ordenarComDirecao(filtradas, ordenadores, sort, direcao);
  }

  listagem = criarWikiCatalogo({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    botaoLimpar,
    controles: [busca, ordenacao, filtroRamo, filtroNivel],
    pageSize: 30,
    usarFallbackScroll: true,
    cardSelector: "[data-skill-id]",
    obterCardId: (card) => card.dataset.skillId,
    abrirDetalhe: (id) => detalheController.abrirDetalhe(id),
    criarCard: criarCardHabilidade,
    obterResultado,
    limparFiltros() {
      if (busca) busca.value = "";
      if (ordenacao) ordenacao.value = "ordem";
      if (filtroRamo) filtroRamo.value = "";
      if (filtroNivel) filtroNivel.value = "";
      if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    },
  });
  listagem.iniciar();
}
