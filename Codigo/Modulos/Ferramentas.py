import time


class GerenciadorFPS:
    def __init__(self, fps_alvo=60, intervalo_print=3.0, limite_alerta_fps=3.0):
        self.fps_alvo = max(1.0, float(fps_alvo))
        self.intervalo_print = max(0.5, float(intervalo_print))
        self.limite_alerta_fps = max(0.0, float(limite_alerta_fps))
        self._tempo_quadro_ideal = 1.0 / self.fps_alvo
        self._trechos = {}
        self._entradas = {}
        self._ultimo_print = time.perf_counter()

    def iniciar_trecho(self, nome):
        self._entradas[str(nome)] = time.perf_counter()

    def finalizar_trecho(self, nome):
        chave = str(nome)
        inicio = self._entradas.pop(chave, None)
        if inicio is None:
            return
        duracao = time.perf_counter() - inicio
        trecho = self._trechos.setdefault(
            chave,
            {
                "tempo_total": 0.0,
                "execucoes": 0,
                "tempo_max": 0.0,
            },
        )
        trecho["tempo_total"] += duracao
        trecho["execucoes"] += 1
        trecho["tempo_max"] = max(trecho["tempo_max"], duracao)

    def imprimir_relatorio(self):
        agora = time.perf_counter()
        if agora - self._ultimo_print < self.intervalo_print:
            return

        self._ultimo_print = agora
        if not self._trechos:
            return

        print("\n[GerenciadorFPS] Perda de FPS por trecho:")
        for nome, dados in sorted(self._trechos.items()):
            execucoes = max(1, int(dados["execucoes"]))
            tempo_medio = dados["tempo_total"] / execucoes
            tempo_max = float(dados["tempo_max"])
            fps_medio = 1.0 / (self._tempo_quadro_ideal + tempo_medio)
            fps_pico = 1.0 / (self._tempo_quadro_ideal + tempo_max)
            perda_media = max(0.0, self.fps_alvo - fps_medio)
            perda_max = max(0.0, self.fps_alvo - fps_pico)

            mensagem = (
                f" - {nome}: medio={tempo_medio * 1000:.2f}ms "
                f"(perda ~{perda_media:.2f} fps), "
                f"pico={tempo_max * 1000:.2f}ms "
                f"(perda ~{perda_max:.2f} fps)"
            )
            if perda_media >= self.limite_alerta_fps:
                mensagem += " [ALERTA]"
            print(mensagem)

        self._trechos.clear()
