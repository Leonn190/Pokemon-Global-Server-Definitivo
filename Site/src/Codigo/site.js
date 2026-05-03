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

window.addEventListener("scroll", atualizarTopbar, { passive: true });
atualizarTopbar();

if (botaoMenu && menu) {
  botaoMenu.addEventListener("click", () => menu.classList.toggle("aberto"));
  menu.addEventListener("click", (evento) => {
    if (evento.target instanceof HTMLAnchorElement) menu.classList.remove("aberto");
  });
}

botoesLogo.forEach((botao) => botao.addEventListener("click", () => trocarLogo(botao)));
botoesAlerta.forEach((botao) => botao.addEventListener("click", () => alert(botao.dataset.alerta || "JS funcionando.")));
configurarAbasConta();
configurarLogin();
configurarCadastro();
configurarContato();
