from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    all_files = [path for path in repo_root.rglob('*') if path.is_file()]
    py_files = [path for path in all_files if path.suffix == '.py']

    total_python_lines = 0
    for py_file in py_files:
        with py_file.open('r', encoding='utf-8', errors='ignore') as file:
            total_python_lines += sum(1 for _ in file)

    total_repo_size_bytes = sum(path.stat().st_size for path in all_files)

    print(f'numero de linhas python totais do repositorio: {total_python_lines}')
    print(f'tamanho peso do jogo (bytes): {total_repo_size_bytes}')
    print(f'numero de arquivos totais: {len(all_files)}')
    print(f'numero de arquivos .py: {len(py_files)}')


if __name__ == '__main__':
    main()