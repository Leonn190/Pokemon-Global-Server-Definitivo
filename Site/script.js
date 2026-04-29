// Caminho relativo considerando que a pasta Site fica na raiz do repo.
const PASTA_ICONES = "../Recursos/Visual/Icones/GlobalServer";

const logoPrincipal = document.querySelector("[data-logo-principal]");
const botoesLogo = document.querySelectorAll("[data-logo]");
const statusSite = document.querySelector("[data-status-site]");
const botaoAlerta = document.querySelector("[data-botao-alerta]");

function trocarLogo(nomeArquivo) {
  if (!logoPrincipal) return;

  logoPrincipal.src = `${PASTA_ICONES}/${nomeArquivo}`;
  logoPrincipal.alt = `Visual ${nomeArquivo} do Pokémon Global Server`;

  if (statusSite) {
    statusSite.textContent = `Logo trocada para ${nomeArquivo}. Caminho usado: ${PASTA_ICONES}/${nomeArquivo}`;
  }
}

botoesLogo.forEach((botao) => {
  botao.addEventListener("click", () => {
    botoesLogo.forEach((outroBotao) => outroBotao.classList.remove("ativo"));
    botao.classList.add("ativo");
    trocarLogo(botao.dataset.logo);
  });
});

if (botaoAlerta) {
  botaoAlerta.addEventListener("click", () => {
    alert("JS funcionando! Depois esse botão pode abrir cadastro, launcher, chave beta etc.");
  });
}
