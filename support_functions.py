import pandas as pd
from tqdm import tqdm
from pathlib import Path
from typing import List, Optional


def list_files(dir_path: str, extension: Optional[str] = None, recursive: bool = True) -> List[str]:
    """
    Lista todos os arquivos no diretório `dir_path`.
    Se `extension` for fornecida (ex: 'csv' ou '.csv'),
    filtra apenas arquivos com essa extensão.
    Por padrão, pesquisa recursivamente (subpastas).
    """
    base = Path(dir_path)
    if extension:
        ext = extension if extension.startswith('.') else f".{extension}"
        pattern = f"**/*{ext}" if recursive else f"*{ext}"
    else:
        pattern = "**/*" if recursive else "*"
    return [str(p.resolve()) for p in tqdm(base.rglob(pattern), desc="Lendo arquivos...") if p.is_file()]


def search_engine(query: str, files: list, column: str = "BAIRRO", exact_match: bool = True) -> pd.DataFrame:
    """
    Busca por 'query' na coluna especificada em todos os arquivos listados.
    Pode fazer busca exata ou por substring (case-insensitive).
    """
    q_lower = query.lower()
    dfs = []

    for arquivo in tqdm(files, desc="Buscando"):
        df = pd.read_csv(
            arquivo,
            sep=";",
            encoding="utf-8",
            dtype=str,       # garante leitura como string
            low_memory=False
        )

        if column not in df.columns:
            continue

        df[column] = df[column].astype(str).str.lower()

        # Se busca exata
        if exact_match:
            df_match = df[df[column] == q_lower]
        # Se busca por substring
        else:
            df_match = df[df[column].str.contains(q_lower, na=False)]

        if not df_match.empty:
            df_match["_arquivo"] = Path(arquivo).name
            dfs.append(df_match)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=[column])
