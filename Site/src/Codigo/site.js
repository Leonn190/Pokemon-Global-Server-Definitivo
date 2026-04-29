const topbar = document.querySelector("[data-topbar]");
const menu = document.querySelector("[data-menu]");
const botaoMenu = document.querySelector("[data-menu-mobile]");
const logoPrincipal = document.querySelector("[data-logo-principal]");
const botoesLogo = document.querySelectorAll("[data-logo-src]");
const statusSite = document.querySelector("[data-status-site]");
const botoesAlerta = document.querySelectorAll("[data-alerta]");

function atualizarTopbar() {
  if (!topbar) return;
  topbar.classList.toggle("compacto", window.scrollY > 24);
}

function trocarLogo(botao) {
  if (!logoPrincipal || !botao) return;

  const src = botao.dataset.logoSrc;
  const nome = botao.dataset.logoNome || "visual";

  logoPrincipal.src = src;
  logoPrincipal.alt = `Visual ${nome} do Pokémon Global Server`;

  botoesLogo.forEach((outroBotao) => outroBotao.classList.remove("ativo"));
  botao.classList.add("ativo");

  if (statusSite) {
    statusSite.textContent = `Logo trocada para ${nome}. Imagem importada pela estrutura Astro.`;
  }
}

window.addEventListener("scroll", atualizarTopbar, { passive: true });
atualizarTopbar();

if (botaoMenu && menu) {
  botaoMenu.addEventListener("click", () => {
    menu.classList.toggle("aberto");
  });

  menu.addEventListener("click", (evento) => {
    if (evento.target instanceof HTMLAnchorElement) {
      menu.classList.remove("aberto");
    }
  });
}

botoesLogo.forEach((botao) => {
  botao.addEventListener("click", () => trocarLogo(botao));
});

botoesAlerta.forEach((botao) => {
  botao.addEventListener("click", () => {
    const mensagem = botao.dataset.alerta || "JS funcionando.";
    alert(mensagem);
  });
});
