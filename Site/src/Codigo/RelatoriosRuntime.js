import { lerJson } from "./WikiRuntimeBase.js";

function formatarData(valor) {
  if (!valor) return "";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "";
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function inicializarRelatorios(idDados = "relatorios-data") {
  const dados = lerJson(idDados, "Relatórios");
  const app = document.querySelector("[data-relatorios-app]");
  if (!dados || !app) return;
  const select = app.querySelector("[data-relatorio-select]");
  const titulo = app.querySelector("[data-relatorio-titulo]");
  const arquivo = app.querySelector("[data-relatorio-arquivo]");
  const conteudo = app.querySelector("[data-relatorio-conteudo]");
  const meta = app.querySelector("[data-relatorio-meta]");
  const porId = Object.fromEntries((dados.relatorios || []).map((relatorio) => [relatorio.id, relatorio]));
  function aplicarRelatorio(id) {
    const relatorio = porId[id] ?? dados.relatorios?.[0];
    if (!relatorio) return;
    if (titulo) titulo.textContent = relatorio.titulo;
    if (arquivo) arquivo.textContent = relatorio.arquivo;
    if (conteudo) conteudo.innerHTML = relatorio.html || "";
    if (meta) {
      const data = formatarData(relatorio.atualizadoEm);
      meta.innerHTML = `Arquivo selecionado: <strong>${relatorio.arquivo}</strong>${data ? ` • atualizado em ${data}` : ""}`;
    }
  }
  select?.addEventListener("change", () => aplicarRelatorio(select.value));
  if (select?.value) aplicarRelatorio(select.value);
}
