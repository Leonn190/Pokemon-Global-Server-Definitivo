const topbar = document.querySelector("[data-topbar]");
const menu = document.querySelector("[data-menu]");
const botaoMenu = document.querySelector("[data-menu-mobile]");
const logoPrincipal = document.querySelector("[data-logo-principal]");
const botoesLogo = document.querySelectorAll("[data-logo-src]");
const statusSite = document.querySelector("[data-status-site]");
const botoesAlerta = document.querySelectorAll("[data-alerta]");

function atualizarTopbar() {
  topbar?.classList.toggle("compacto", window.scrollY > 24);
}
function trocarLogo(botao) {
  if (!logoPrincipal || !botao) return;
  const src = botao.dataset.logoSrc;
  const nome = botao.dataset.logoNome || "visual";
  logoPrincipal.src = src;
  logoPrincipal.alt = `Visual ${nome} do Pokémon Global Server`;
  botoesLogo.forEach((outroBotao) => outroBotao.classList.remove("ativo"));
  botao.classList.add("ativo");
  if (statusSite) statusSite.textContent = `Logo trocada para ${nome}.`;
}
function normalizarTexto(valor) {
  return String(valor || "").trim();
}
function normalizarEmail(valor) {
  return normalizarTexto(valor).toLowerCase();
}
function definirMensagem(elemento, texto, tipo = "") {
  if (!elemento) return;
  elemento.textContent = texto;
  elemento.classList.remove("ok", "erro");
  if (tipo) elemento.classList.add(tipo);
}
function configurarAbasConta() {
  const botoes = document.querySelectorAll("[data-account-tab]");
  const paineis = document.querySelectorAll("[data-account-panel]");
  if (!botoes.length || !paineis.length) return;
  botoes.forEach((botao) => {
    botao.addEventListener("click", () => {
      const alvo = botao.dataset.accountTab;
      botoes.forEach((item) => {
        const ativo = item === botao;
        item.classList.toggle("ativa", ativo);
        item.setAttribute("aria-selected", ativo ? "true" : "false");
      });
      paineis.forEach((painel) => painel.classList.toggle("escondido", painel.dataset.accountPanel !== alvo));
    });
  });
}
function configurarLogin() {
  const form = document.querySelector("[data-login-form]");
  const mensagem = document.querySelector("[data-login-message]");
  if (!form) return;
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    definirMensagem(mensagem, "Não encontramos uma conta ativa com esses dados. Confira as informações ou crie uma conta com token.", "erro");
  });
}
function configurarCadastro() {
  const form = document.querySelector("[data-signup-form]");
  const mensagem = document.querySelector("[data-signup-message]");
  if (!form) return;
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const dados = new FormData(form);
    const senha = String(dados.get("senha") || "");
    const confirmar = String(dados.get("confirmar") || "");
    const token = normalizarTexto(dados.get("token"));
    if (senha !== confirmar) {
      definirMensagem(mensagem, "As senhas não conferem.", "erro");
      return;
    }
    if (token.length < 4) {
      definirMensagem(mensagem, "Informe um token de acesso válido.", "erro");
      return;
    }
    definirMensagem(mensagem, "Dados recebidos. O acesso será confirmado pelo Gmail informado.", "ok");
    form.reset();
  });
}
function configurarContato() {
  const form = document.querySelector("[data-contact-form]");
  const mensagem = document.querySelector("[data-contact-message]");
  if (!form) return;
  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const dados = new FormData(form);
    const email = normalizarEmail(dados.get("email"));
    const motivo = normalizarTexto(dados.get("motivo"));
    if (!email.endsWith("@gmail.com")) {
      definirMensagem(mensagem, "Use um Gmail válido para receber a resposta.", "erro");
      return;
    }
    form.reset();
    definirMensagem(mensagem, `Contato enviado como ${motivo || "Outros"}. Aguarde o retorno pelo Gmail informado.`, "ok");
  });
}


function configurarEntradaHome() {
  if (!document.querySelector(".hero-home")) return;
  const seletores = [
    ".logo-palco",
    ".hero-copy .selo",
    ".hero-copy h1",
    ".subtitulo-home",
    ".hero-acoes",
    ".intro-home",
    ".pokemon-destaque-copy",
    ".pokemon-carrossel-janela",
    ".pokemon-carrossel-acoes",
    ".instalar-card",
    ".aviso-legal",
  ];
  const elementos = seletores.flatMap((seletor) => Array.from(document.querySelectorAll(seletor)));
  if (!elementos.length) return;
  const reduzirMovimento = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  elementos.forEach((elemento, indice) => {
    elemento.classList.add("home-entrada");
    elemento.style.setProperty("--home-delay", `${Math.min(indice * 70, 420)}ms`);
  });
  document.body.classList.add("home-entrada-pronta");
  const revelarTudo = () => elementos.forEach((elemento) => elemento.classList.add("visivel"));
  if (reduzirMovimento || !("IntersectionObserver" in window)) {
    revelarTudo();
    return;
  }
  const iniciarEntrada = () => {
    const observador = new IntersectionObserver((entradas) => {
      entradas.forEach((entrada) => {
        if (!entrada.isIntersecting) return;
        entrada.target.classList.add("visivel");
        observador.unobserve(entrada.target);
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -5% 0px" });
    elementos.forEach((elemento) => observador.observe(elemento));
  };
  requestAnimationFrame(() => requestAnimationFrame(iniciarEntrada));
}

function configurarSelectsWiki() {
  const grupos = [...document.querySelectorAll(".filtro-select-wiki")];
  if (!grupos.length) return;
  const fecharTodos = (exceto = null) => {
    grupos.forEach((grupo) => {
      if (grupo !== exceto) grupo.classList.remove("select-aberto");
    });
  };
  grupos.forEach((grupo) => {
    const select = grupo.querySelector("select");
    if (!select) return;
    select.addEventListener("pointerdown", () => {
      const estavaAberto = grupo.classList.contains("select-aberto");
      fecharTodos(grupo);
      grupo.classList.toggle("select-aberto", !estavaAberto);
    });
    select.addEventListener("keydown", (evento) => {
      if (["Enter", " ", "ArrowDown", "ArrowUp"].includes(evento.key)) {
        fecharTodos(grupo);
        grupo.classList.add("select-aberto");
      }
      if (["Escape", "Tab"].includes(evento.key)) grupo.classList.remove("select-aberto");
    });
    select.addEventListener("change", () => window.setTimeout(() => grupo.classList.remove("select-aberto"), 0));
    select.addEventListener("blur", () => grupo.classList.remove("select-aberto"));
  });
  document.addEventListener("pointerdown", (evento) => {
    if (!evento.target.closest?.(".filtro-select-wiki")) fecharTodos();
  });
}

function configurarTransicaoPorLogo() {
  const links = document.querySelectorAll("[data-page-fade-link]");
  if (!links.length) return;
  const reduzirMovimento = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  links.forEach((link) => {
    link.addEventListener("click", (evento) => {
      if (reduzirMovimento || evento.defaultPrevented || evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return;
      const destino = link.href;
      if (!destino || destino === window.location.href) return;
      evento.preventDefault();
      document.body.classList.add("pagina-saindo");
      window.setTimeout(() => {
        window.location.href = destino;
      }, 170);
    });
  });
}

window.addEventListener("scroll", atualizarTopbar, { passive: true });
atualizarTopbar();

if (botaoMenu && menu) {
  const definirMenuAberto = (aberto) => {
    menu.classList.toggle("aberto", aberto);
    botaoMenu.setAttribute("aria-expanded", aberto ? "true" : "false");
    botaoMenu.setAttribute("aria-label", aberto ? "Fechar menu" : "Abrir menu");
  };
  botaoMenu.addEventListener("click", () => definirMenuAberto(!menu.classList.contains("aberto")));
  menu.addEventListener("click", (evento) => {
    if (evento.target instanceof HTMLAnchorElement) definirMenuAberto(false);
  });
}

botoesLogo.forEach((botao) => botao.addEventListener("click", () => trocarLogo(botao)));
botoesAlerta.forEach((botao) => botao.addEventListener("click", () => alert(botao.dataset.alerta || "JS funcionando.")));
configurarAbasConta();
configurarLogin();
configurarCadastro();
configurarContato();
configurarEntradaHome();
configurarSelectsWiki();
configurarTransicaoPorLogo();
