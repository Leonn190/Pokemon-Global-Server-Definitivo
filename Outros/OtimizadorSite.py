from pathlib import Path
from PIL import Image, ImageOps

# Estrutura esperada:
# Pokemon-Global-Server-Definitivo/
#   Outros/
#     otimizar_public.py
#   Site/
#     public/
#
# Como este script fica em Outros, subimos uma pasta e entramos em Site/public.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PUBLIC_DIR = RAIZ_PROJETO / "Site" / "public"

MIN_BYTES_WEBP = 8 * 1024  # 8 KB

# Antes você usava 750x750.
# Agora os ataques maiores que isso serão reduzidos para este tamanho.
# Se quiser mais agressivo, use (384, 384).
ATAQUES_TAMANHO_NOVO = (512, 512)

WEBP_QUALITY = 92

EXTENSOES_IMAGEM = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
}


def esta_na_pasta_ataques(caminho: Path) -> bool:
    try:
        relativo = caminho.relative_to(PUBLIC_DIR)
    except ValueError:
        return False

    if not relativo.parts:
        return False

    primeira_pasta = relativo.parts[0].lower()
    return primeira_pasta in {"ataques", "ataque"}


def imagem_maior_que_tamanho(imagem: Image.Image, tamanho_limite: tuple[int, int]) -> bool:
    largura, altura = imagem.size
    limite_largura, limite_altura = tamanho_limite

    return largura > limite_largura or altura > limite_altura


def redimensionar_ataque(imagem: Image.Image) -> Image.Image:
    """
    Reduz imagens de ataques para o tamanho configurado.

    Se a imagem for quadrada, redimensiona exatamente para ATAQUES_TAMANHO_NOVO.
    Se não for quadrada, mantém proporção para evitar distorção.
    """
    largura, altura = imagem.size

    if largura == altura:
        return imagem.resize(ATAQUES_TAMANHO_NOVO, Image.Resampling.LANCZOS)

    return ImageOps.contain(imagem, ATAQUES_TAMANHO_NOVO, Image.Resampling.LANCZOS)


def salvar_webp(imagem: Image.Image, destino: Path):
    """
    Salva a imagem como WebP.
    Mantém transparência quando existir.
    """
    if imagem.mode in ("RGBA", "LA") or "transparency" in imagem.info:
        imagem = imagem.convert("RGBA")
    else:
        imagem = imagem.convert("RGB")

    imagem.save(
        destino,
        "WEBP",
        quality=WEBP_QUALITY,
        method=6,
        optimize=True,
    )


def processar_imagem(caminho: Path):
    tamanho_original_bytes = caminho.stat().st_size
    tamanho_original_kb = tamanho_original_bytes / 1024

    try:
        with Image.open(caminho) as img:
            if getattr(img, "is_animated", False):
                print(f"[PULOU ANIMADA] {caminho}")
                return

            img = ImageOps.exif_transpose(img)
            img.load()

            esta_em_ataques = esta_na_pasta_ataques(caminho)
            ja_eh_webp = caminho.suffix.lower() == ".webp"

            tamanho_original_px = img.size

            precisa_redimensionar_ataque = (
                esta_em_ataques
                and imagem_maior_que_tamanho(img, ATAQUES_TAMANHO_NOVO)
            )

            # Só converte para WebP se ainda NÃO for WebP.
            # Isso evita recomprimir WebPs antigos sem necessidade.
            precisa_converter_webp = (
                tamanho_original_bytes > MIN_BYTES_WEBP
                and not ja_eh_webp
            )

            if not precisa_redimensionar_ataque and not precisa_converter_webp:
                print(f"[MANTEVE] {caminho.relative_to(PUBLIC_DIR)} ({tamanho_original_kb:.1f} KB)")
                return

            if precisa_redimensionar_ataque:
                img = redimensionar_ataque(img)

            destino_webp = caminho.with_suffix(".webp")

            if destino_webp == caminho:
                temporario = caminho.with_name(caminho.stem + ".__tmp__.webp")
            else:
                temporario = destino_webp.with_name(destino_webp.stem + ".__tmp__.webp")

            salvar_webp(img, temporario)

            if destino_webp.exists() and destino_webp != caminho:
                destino_webp.unlink()

            temporario.replace(destino_webp)

            if caminho != destino_webp and caminho.exists():
                caminho.unlink()

            tamanho_novo_kb = destino_webp.stat().st_size / 1024

            acoes = []

            if precisa_redimensionar_ataque:
                acoes.append(
                    f"redimensionou ataque {tamanho_original_px[0]}x{tamanho_original_px[1]} "
                    f"-> {img.size[0]}x{img.size[1]}"
                )

            if precisa_converter_webp or not ja_eh_webp:
                acoes.append("converteu para .webp")
            elif precisa_redimensionar_ataque and ja_eh_webp:
                acoes.append("resalvou .webp reduzido")

            print(
                f"[OK] {caminho.relative_to(PUBLIC_DIR)} -> "
                f"{destino_webp.relative_to(PUBLIC_DIR)} | "
                f"{tamanho_original_kb:.1f} KB -> {tamanho_novo_kb:.1f} KB | "
                f"{', '.join(acoes)}"
            )

    except Exception as erro:
        print(f"[ERRO] {caminho} | {erro}")


def main():
    print(f"Raiz do projeto: {RAIZ_PROJETO}")
    print(f"Pasta public: {PUBLIC_DIR}")

    if not PUBLIC_DIR.exists():
        print()
        print("ERRO: pasta public não encontrada.")
        print("Confira se o script está em:")
        print("  Outros/otimizar_public.py")
        print("E se a pasta existe em:")
        print("  Site/public")
        return

    imagens = [
        caminho
        for caminho in PUBLIC_DIR.rglob("*")
        if caminho.is_file() and caminho.suffix.lower() in EXTENSOES_IMAGEM
    ]

    print(f"Imagens encontradas: {len(imagens)}")
    print(f"Tamanho novo dos ataques: {ATAQUES_TAMANHO_NOVO[0]}x{ATAQUES_TAMANHO_NOVO[1]}")
    print("Começando otimização...\n")

    for caminho in imagens:
        processar_imagem(caminho)

    print("\nFinalizado.")


if __name__ == "__main__":
    main()