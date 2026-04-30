const topbar = document.querySelector("[data-topbar]");
const menu = document.querySelector("[data-menu]");
const botaoMenu = document.querySelector("[data-menu-mobile]");
const logoPrincipal = document.querySelector("[data-logo-principal]");
const botoesLogo = document.querySelectorAll("[data-logo-src]");
const statusSite = document.querySelector("[data-status-site]");
const botoesAlerta = document.querySelectorAll("[data-alerta]");

const CHAVE_SESSAO = "pgs_sessao_local";
const CHAVE_CADASTRO = "pgs_cadastro_simulado";
const TOKEN_VALIDO = "LN1900";
const CONTA_DEMO = {
  email: "euleonsoto@gmail.com",
  usuario: "Leon190",
  senha: "Senha",
};

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

function lerSessao() {
  try {
    const bruto = localStorage.getItem(CHAVE_SESSAO);
    if (!bruto) return null;
    const sessao = JSON.parse(bruto);
    if (!sessao || sessao.logado !== true) return null;
    return sessao;
  } catch (_erro) {
    return null;
  }
}

function salvarSessao(sessao) {
  localStorage.setItem(CHAVE_SESSAO, JSON.stringify(sessao));
}

function limparSessao() {
  localStorage.removeItem(CHAVE_SESSAO);
}

function normalizarEmail(valor) {
  return String(valor || "").trim().toLowerCase();
}

function normalizarTexto(valor) {
  return String(valor || "").trim();
}

function definirMensagem(elemento, texto, tipo = "") {
  if (!elemento) return;
  elemento.textContent = texto;
  elemento.classList.remove("ok", "erro");
  if (tipo) elemento.classList.add(tipo);
}

function atualizarContaNaTela() {
  const sessao = lerSessao();
  const titulo = document.querySelector("[data-session-title]");
  const texto = document.querySelector("[data-session-text]");
  const ponto = document.querySelector("[data-session-dot]");
  const userCard = document.querySelector("[data-user-card]");
  const userName = document.querySelector("[data-user-name]");
  const userEmail = document.querySelector("[data-user-email]");
  const logout = document.querySelector("[data-logout-button]");
  const linkDownload = document.querySelector("[data-account-download-link]");

  if (!titulo || !texto) return;

  if (sessao) {
    titulo.textContent = "Modo logado";
    texto.textContent = "Sessão local ativa. A página de download reconhece este estado e libera a área beta, embora o instalador real ainda não exista.";
    ponto?.classList.add("online");
    if (userCard) userCard.hidden = false;
    if (userName) userName.textContent = sessao.usuario || CONTA_DEMO.usuario;
    if (userEmail) userEmail.textContent = sessao.email || CONTA_DEMO.email;
    if (logout) logout.hidden = false;
    if (linkDownload) linkDownload.textContent = "Ir para download liberado";
  } else {
    titulo.textContent = "Modo deslogado";
    texto.textContent = "Faça login com a conta de teste para liberar a tela de download. O estado fica salvo apenas neste navegador.";
    ponto?.classList.remove("online");
    if (userCard) userCard.hidden = true;
    if (logout) logout.hidden = true;
    if (linkDownload) linkDownload.textContent = "Ver download";
  }
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

      paineis.forEach((painel) => {
        painel.classList.toggle("escondido", painel.dataset.accountPanel !== alvo);
      });
    });
  });
}

function configurarLogin() {
  const form = document.querySelector("[data-login-form]");
  const mensagem = document.querySelector("[data-login-message]");
  if (!form) return;

  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const dados = new FormData(form);
    const identificador = normalizarTexto(dados.get("identificador"));
    const senha = String(dados.get("senha") || "");

    const idCorreto =
      normalizarEmail(identificador) === CONTA_DEMO.email ||
      identificador === CONTA_DEMO.usuario;

    if (!idCorreto || senha !== CONTA_DEMO.senha) {
      definirMensagem(mensagem, "Login recusado. Neste protótipo só a conta de teste entra de verdade.", "erro");
      return;
    }

    salvarSessao({
      logado: true,
      usuario: CONTA_DEMO.usuario,
      email: CONTA_DEMO.email,
      origem: "demo-local",
      conectadoEm: new Date().toISOString(),
    });

    definirMensagem(mensagem, "Login aceito. Download beta liberado neste navegador.", "ok");
    atualizarContaNaTela();
    atualizarDownloadNaTela();
  });
}

function configurarCadastro() {
  const form = document.querySelector("[data-signup-form]");
  const mensagem = document.querySelector("[data-signup-message]");
  if (!form) return;

  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const dados = new FormData(form);
    const usuario = normalizarTexto(dados.get("usuario"));
    const email = normalizarEmail(dados.get("email"));
    const senha = String(dados.get("senha") || "");
    const confirmar = String(dados.get("confirmar") || "");
    const token = normalizarTexto(dados.get("token")).toUpperCase();

    if (senha !== confirmar) {
      definirMensagem(mensagem, "As senhas não conferem.", "erro");
      return;
    }

    if (token !== TOKEN_VALIDO) {
      definirMensagem(mensagem, "Token inválido. Para este protótipo, use LN1900 ou solicite um token pelo contato.", "erro");
      return;
    }

    localStorage.setItem(
      CHAVE_CADASTRO,
      JSON.stringify({ usuario, email, token, criadoEm: new Date().toISOString() }),
    );

    definirMensagem(
      mensagem,
      "Token aceito e cadastro simulado concluído. Como ainda não existe banco/servidor, essa conta não vira login real; use a conta de teste para entrar.",
      "ok",
    );
    form.reset();
  });
}

function configurarLogout() {
  const logout = document.querySelector("[data-logout-button]");
  if (!logout) return;

  logout.addEventListener("click", () => {
    limparSessao();
    atualizarContaNaTela();
    atualizarDownloadNaTela();
  });
}

function atualizarDownloadNaTela() {
  const gate = document.querySelector(".download-gate");
  const titulo = document.querySelector("[data-download-title]");
  const texto = document.querySelector("[data-download-text]");
  const badge = document.querySelector("[data-download-badge]");
  const icone = document.querySelector("[data-download-icon]");
  const acoes = document.querySelector("[data-download-actions]");
  const botaoReal = document.querySelector("[data-download-real]");
  if (!gate || !titulo || !texto) return;

  const sessao = lerSessao();

  if (sessao) {
    gate.classList.add("liberado");
    titulo.textContent = "Acesso beta liberado";
    texto.textContent = "Você está logado neste navegador. O instalador real ainda não foi publicado, então o botão abaixo fica em modo aviso.";
    if (badge) badge.textContent = "Sessão conectada";
    if (icone) icone.textContent = "✅";
    if (acoes) acoes.hidden = true;
    if (botaoReal) {
      botaoReal.hidden = false;
      botaoReal.disabled = true;
      botaoReal.textContent = "Instalador ainda não publicado";
    }
  } else {
    gate.classList.remove("liberado");
    titulo.textContent = "Entre para liberar o download";
    texto.textContent = "O botão de download real só aparece para uma sessão logada. Entre com a conta de teste na aba Conta.";
    if (badge) badge.textContent = "Acesso protegido";
    if (icone) icone.textContent = "🔒";
    if (acoes) acoes.hidden = false;
    if (botaoReal) botaoReal.hidden = true;
  }
}

function configurarContato() {
  const form = document.querySelector("[data-contact-form]");
  const mensagem = document.querySelector("[data-contact-message]");
  if (!form) return;

  form.addEventListener("submit", (evento) => {
    evento.preventDefault();
    const dados = new FormData(form);
    const email = normalizarEmail(dados.get("email"));
    const nome = normalizarTexto(dados.get("nome"));
    const textoLivre = normalizarTexto(dados.get("mensagem"));

    const assunto = "Solicitação de token beta - Pokémon Global Server";
    const corpo = [
      "Olá, Pokémon Global Server.",
      "",
      "Quero solicitar avaliação para receber um token de acesso ao beta fechado.",
      "",
      `Gmail para contato: ${email}`,
      nome ? `Nome/apelido: ${nome}` : "Nome/apelido: não informado",
      "",
      textoLivre || "Mensagem: Quero participar do beta fechado quando possível.",
    ].join("\n");

    const url = new URL("https://mail.google.com/mail/");
    url.searchParams.set("view", "cm");
    url.searchParams.set("fs", "1");
    url.searchParams.set("to", "pokemonglobalserver@gmail.com");
    url.searchParams.set("su", assunto);
    url.searchParams.set("body", corpo);

    window.open(url.toString(), "_blank", "noopener,noreferrer");
    definirMensagem(mensagem, "Gmail aberto com a mensagem preenchida. Revise e envie manualmente.", "ok");
  });
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

configurarAbasConta();
configurarLogin();
configurarCadastro();
configurarLogout();
configurarContato();
atualizarContaNaTela();
atualizarDownloadNaTela();
