import { abrirModalDetalhe, criarWikiCatalogo, fecharModalDetalhe, html, infoHtml, lerJson, normalizar, ordenarComDirecao } from "./WikiRuntimeBase.js";

function criarCardComando(comando) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = `catalogo-card comando-card comando-${comando.local} nivel-${comando.nivel >= 2 ? "avancado" : "basico"}`;
  card.dataset.comandoId = comando.id;
  card.innerHTML = `
    <span class="catalogo-card-codigo">${html(comando.nivelRotulo)}</span>
    <span class="catalogo-card-arte comando-card-icone" aria-hidden="true">⌨</span>
    <span class="catalogo-card-nome">/${html(comando.nome)}</span>
    <span class="catalogo-card-meta">${html(comando.localRotulo)}</span>
    <span class="catalogo-card-linha"><strong>${html(comando.uso)}</strong><small>Uso</small></span>
    <span class="comando-card-descricao">${html(comando.descricao)}</span>
  `;
  return card;
}

function criarControladorDetalhe(dados, obterListaAtual) {
  const detalhe = document.querySelector("[data-comando-detail]");
  let comandoAberto = null;

  function listaNavegacao() {
    const listaAtual = typeof obterListaAtual === "function" ? obterListaAtual() : null;
    const lista = Array.isArray(listaAtual) && listaAtual.length ? listaAtual : (dados.comandos || []);
    return [...lista].sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0));
  }

  function abrirVizinho(direcao) {
    if (!comandoAberto) return;
    const lista = listaNavegacao();
    if (!lista.length) return;
    const indiceAtual = lista.findIndex((comando) => comando.id === comandoAberto.id);
    const indiceSeguro = indiceAtual === -1 ? 0 : indiceAtual;
    const proximo = lista[(indiceSeguro + direcao + lista.length) % lista.length];
    if (proximo) abrirDetalhe(proximo.id);
  }

  function abrirDetalhe(id) {
    const comando = (dados.comandos || []).find((item) => item.id === String(id));
    if (!comando || !detalhe) return;
    comandoAberto = comando;
    const nome = detalhe.querySelector("[data-comando-name]");
    const uso = detalhe.querySelector("[data-comando-use]");
    const descricao = detalhe.querySelector("[data-comando-description]");
    const tags = detalhe.querySelector("[data-comando-tags]");
    const aliases = detalhe.querySelector("[data-comando-aliases]");
    const argumentos = detalhe.querySelector("[data-comando-args]");
    const exemplos = detalhe.querySelector("[data-comando-examples]");
    const info = detalhe.querySelector("[data-comando-info]");

    if (nome) nome.textContent = `/${comando.nome}`;
    if (uso) uso.textContent = comando.uso;
    if (descricao) descricao.textContent = comando.descricao || "Descrição ainda não cadastrada.";
    if (tags) {
      tags.innerHTML = `
        <span>${html(comando.localRotulo)}</span>
        <span>${html(comando.nivelRotulo)}</span>
      `;
    }
    if (aliases) {
      aliases.innerHTML = (comando.aliases || []).length
        ? comando.aliases.map((alias) => `<span>/${html(alias)}</span>`).join("")
        : `<span>Sem aliases</span>`;
    }
    if (argumentos) {
      argumentos.innerHTML = (comando.argumentos || []).length
        ? `<ul>${comando.argumentos.map((arg) => `<li>${html(arg)}</li>`).join("")}</ul>`
        : `<p>Nenhum argumento obrigatório catalogado.</p>`;
    }
    if (exemplos) {
      exemplos.innerHTML = (comando.exemplos || []).length
        ? comando.exemplos.map((exemplo) => `<code>${html(exemplo)}</code>`).join("")
        : `<p>Sem exemplos catalogados.</p>`;
    }
    if (info) {
      info.innerHTML = infoHtml([
        ["Nome interno", comando.nome],
        ["Local", comando.localRotulo],
        ["Nível de acesso", `${comando.nivel} · ${comando.nivelRotulo}`],
        ["Aliases", (comando.aliases || []).map((alias) => `/${alias}`).join(", ") || "Nenhum"],
      ]);
    }
    abrirModalDetalhe(detalhe);
  }

  function fecharDetalhe() {
    fecharModalDetalhe(detalhe);
  }

  detalhe?.querySelectorAll("[data-comando-prev]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(-1)));
  detalhe?.querySelectorAll("[data-comando-next]").forEach((botao) => botao.addEventListener("click", () => abrirVizinho(1)));
  detalhe?.querySelectorAll("[data-comando-close]").forEach((botao) => botao.addEventListener("click", fecharDetalhe));
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && detalhe && !detalhe.hidden) fecharDetalhe();
  });
  return { abrirDetalhe };
}

export function inicializarWikiComandos() {
  const dados = lerJson("comandos-data", "Wiki Comandos");
  const app = document.querySelector("[data-comandos-app]");
  if (!dados || !app) return;
  const grid = app.querySelector("[data-comandos-grid]");
  const busca = app.querySelector("[data-comandos-search]");
  const ordenacao = app.querySelector("[data-comandos-sort]");
  const filtroNivel = app.querySelector("[data-comandos-level]");
  const filtroLocal = app.querySelector("[data-comandos-local]");
  const contador = app.querySelector("[data-comandos-count]");
  const direcaoBotao = app.querySelector("[data-comandos-direction]");
  const botaoLimpar = app.querySelector("[data-comandos-clear]");
  const vazio = app.querySelector("[data-comandos-empty]");
  const sentinela = app.querySelector("[data-comandos-sentinel]");
  let listagem;
  const detalheController = criarControladorDetalhe(dados, () => listagem?.obterResultadoAtual() ?? []);

  function obterResultado(direcao) {
    const termo = normalizar(busca?.value ?? "");
    const nivel = filtroNivel?.value ?? "";
    const local = filtroLocal?.value ?? "";
    const sort = ordenacao?.value ?? "ordem";
    const filtrados = (dados.comandos || []).filter((comando) => {
      if (termo && !comando.busca.includes(termo)) return false;
      if (nivel && String(comando.nivel) !== String(nivel)) return false;
      if (local && comando.local !== local) return false;
      return true;
    });
    const ordenadores = {
      ordem: (a, b) => a.ordem - b.ordem,
      nome: (a, b) => a.nome.localeCompare(b.nome, "pt-BR", { numeric: true }),
      nivel: (a, b) => a.nivel - b.nivel,
      local: (a, b) => a.localRotulo.localeCompare(b.localRotulo, "pt-BR", { numeric: true }),
    };
    return ordenarComDirecao(filtrados, ordenadores, sort, direcao);
  }

  listagem = criarWikiCatalogo({
    grid,
    contador,
    vazio,
    sentinela,
    direcaoBotao,
    botaoLimpar,
    controles: [busca, ordenacao, filtroNivel, filtroLocal],
    pageSize: 28,
    usarFallbackScroll: true,
    cardSelector: "[data-comando-id]",
    obterCardId: (card) => card.dataset.comandoId,
    abrirDetalhe: (id) => detalheController.abrirDetalhe(id),
    criarCard: criarCardComando,
    obterResultado,
    limparFiltros() {
      if (busca) busca.value = "";
      if (ordenacao) ordenacao.value = "ordem";
      if (filtroNivel) filtroNivel.value = "";
      if (filtroLocal) filtroLocal.value = "";
      if (direcaoBotao) direcaoBotao.dataset.sortDirection = "asc";
    },
  });
  listagem.iniciar();
}
