function baseSite() {
  const base = import.meta.env.BASE_URL || "/";
  return base.endsWith("/") ? base : `${base}/`;
}

function ehUrlExterna(href) {
  return /^(?:[a-z][a-z0-9+.-]*:|#)/i.test(String(href || ""));
}

export function rotaSite(href = "/") {
  const valor = String(href || "/");
  if (ehUrlExterna(valor)) return valor;
  const base = baseSite();
  const relativo = valor.startsWith("/") ? valor.slice(1) : valor;
  return `${base}${relativo}`;
}

export function caminhoSite(pathname = "/") {
  const valor = String(pathname || "/");
  const base = baseSite().replace(/\/$/, "");
  if (!base || base === "") return valor;
  if (valor === base) return "/";
  if (valor.startsWith(`${base}/`)) return valor.slice(base.length) || "/";
  return valor;
}
