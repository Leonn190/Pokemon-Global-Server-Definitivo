from pathlib import Path
import shutil


PASTAS_PARA_ZIPAR = ("Codigo", "Dados", "SimuladorServerJogo")


def copiar_pastas(raiz: Path, destino: Path) -> None:
    if destino.exists():
        shutil.rmtree(destino)

    destino.mkdir()

    for nome_pasta in PASTAS_PARA_ZIPAR:
        origem = raiz / nome_pasta

        if not origem.is_dir():
            raise FileNotFoundError(f"Pasta nao encontrada: {origem}")

        shutil.copytree(origem, destino / nome_pasta)


def criar_zip(pasta_gs: Path) -> Path:
    zip_path = pasta_gs.with_suffix(".zip")

    if zip_path.exists():
        zip_path.unlink()

    shutil.make_archive(str(pasta_gs), "zip", root_dir=pasta_gs)
    return zip_path


def main() -> None:
    raiz = Path(__file__).resolve().parents[1]
    pasta_gs = raiz / "GS"

    copiar_pastas(raiz, pasta_gs)
    zip_path = criar_zip(pasta_gs)
    shutil.rmtree(pasta_gs)

    print(f"Zip criado com sucesso: {zip_path}")


if __name__ == "__main__":
    main()
