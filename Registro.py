from pathlib import Path
from collections import Counter, defaultdict
import re


def bytes_para_gb(num_bytes: int) -> float:
    return num_bytes / (1024 ** 3)  # GiB


def contar_linhas_py(path: Path) -> int:
    total = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                total += 1
    except OSError:
        return 0
    return total


CLASS_RE = re.compile(r"^\s*class\s+[A-Za-z_]\w*\s*(\(|:)")


def contar_classes_py(path: Path) -> int:
    """
    Conta linhas que parecem definição de classe: class Nome(...):
    Heurística simples e rápida.
    """
    n = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if CLASS_RE.match(line):
                    n += 1
    except OSError:
        return 0
    return n


def main() -> None:
    repo_root = Path(__file__).resolve().parent

    total_size = 0
    total_files = 0
    total_dirs = 0

    ext_count = Counter()
    ext_size = defaultdict(int)

    py_files = 0
    py_lines = 0
    py_classes = 0

    for p in repo_root.rglob("*"):
        try:
            if p.is_dir():
                total_dirs += 1
                continue

            if not p.is_file():
                continue

            total_files += 1
            size = p.stat().st_size
            total_size += size

            ext = p.suffix.lower() if p.suffix else "(sem_ext)"
            ext_count[ext] += 1
            ext_size[ext] += size

            if p.suffix.lower() == ".py":
                py_files += 1
                py_lines += contar_linhas_py(p)
                py_classes += contar_classes_py(p)

        except OSError:
            continue

    print("Relatorio Pokemon Global Server")
    print(f"Pastas: {total_dirs}")
    print(f"Arquivos: {total_files}")
    print(f"Tamanho total: {bytes_para_gb(total_size):.3f} GB ({total_size:,} bytes)\n")

    print("Python:")
    print(f"  .py arquivos: {py_files}")
    print(f"  linhas totais: {py_lines}")
    print(f"  classes encontradas: {py_classes}")

    print("Top extensões por tamanho:")
    for ext, sz in sorted(ext_size.items(), key=lambda kv: kv[1], reverse=True)[:12]:
        print(f"  {ext:>10}  {bytes_para_gb(sz):>8.3f} GB  |  {ext_count[ext]} arquivo(s)")


if __name__ == "__main__":
    main()