import streamlit as st
import polars as pl
import pandas as pd
from support_functions import list_files  # aproveitamos apenas esta
from brasilapy import BrasilAPI
from pathlib import Path

client = BrasilAPI()

# ---------- Estado ----------
st.session_state.setdefault("result_df", None)
st.session_state.setdefault("cnpj_options", ["-- Selecione um CNPJ --"])
st.session_state.setdefault("selected_cnpj", "-- Selecione um CNPJ --")

# ---------- Configuração ----------
st.set_page_config("Buscador de CNPJ por Endereço", layout="wide")
st.title("🔎 Buscador de CNPJ por Endereço")

# ---------- Arquivos ----------
files = list_files("arquivosTestes", ".csv")
if not files:
    st.error("Nenhum arquivo CSV encontrado em *arquivosTestes*.")
    st.stop()

# ---------- Barra lateral – coluna de busca ----------
with st.sidebar:
    sample = pl.read_csv(Path(files[0]), separator=";", encoding="utf8-lossy",
                         infer_schema=False, n_rows=1)
    coluna_busca = st.selectbox("Coluna para buscar:", sample.columns, index=1)

# ---------- Campo de texto e botão ----------
query = st.text_input("Digite o termo para buscar:")

# ---------- Busca principal ----------
if st.button("Buscar"):
    if not query.strip():
        st.warning("Digite algo para buscar 📌")
    else:
        total = len(files)
        progresso = st.progress(0, text=f"0 / {total} arquivos analisados")
        encontrados = []

        for i, f in enumerate(files, 1):
            df = pl.read_csv(Path(f), separator=";", encoding="utf8-lossy",
                             infer_schema=False)
            # converte coluna para texto e aplica filtro case-insensitive ↓
            df = df.with_columns(pl.col(coluna_busca).cast(pl.Utf8))
            mask = df[coluna_busca].str.to_lowercase().str.contains(query.lower())
            if mask.any():
                encontrados.append(df.filter(mask))

            progresso.progress(i/total,
                               text=f"{i} / {total} arquivos analisados")

        progresso.empty()  # remove barra após término

        if not encontrados:
            st.info("Nenhum resultado encontrado.")
            st.session_state.result_df = None
            st.session_state.cnpj_options = ["-- Selecione um CNPJ --"]
        else:
            result_df = pl.concat(encontrados)
            if "CNPJ" in result_df.columns:
                result_df = result_df.with_columns(pl.col("CNPJ").cast(pl.Utf8))

            st.session_state.result_df = result_df
            opts = sorted(result_df["CNPJ"].unique().to_list()) \
                   if "CNPJ" in result_df.columns else []
            st.session_state.cnpj_options = ["-- Selecione um CNPJ --"] + opts

        st.session_state.selected_cnpj = "-- Selecione um CNPJ --"  # reset

# ---------- Resultado principal ----------
if st.session_state.result_df is not None:
    st.success(f"{st.session_state.result_df.height} registros encontrados.")
    st.dataframe(st.session_state.result_df.to_pandas().astype(str),
                 use_container_width=True)

# ---------- Selectbox de CNPJ ----------
if st.session_state.result_df is not None and "CNPJ" in st.session_state.result_df.columns:

    # 1) cria o selectbox com OUTRA chave
    selected = st.sidebar.selectbox(
        "Escolha um CNPJ para ver detalhes:",
        st.session_state.cnpj_options,
        key="cnpj_select",                  # <- chave só do widget
    )

    # 2) se o usuário mudou, gravamos no estado da aplicação
    if selected != st.session_state.get("selected_cnpj"):
        st.session_state.selected_cnpj = selected

    # 3) usar o valor que acabamos de gravar
    cnpj = st.session_state.selected_cnpj
    st.write(cnpj)

    if cnpj != "-- Selecione um CNPJ --":
        with st.status("🔄 Obtendo dados da BrasilAPI...", state="running"):
            with st.spinner(f"Consultando BrasilAPI para {cnpj}…"):
                try:
                    dados = client.processor.get_data(f"/cnpj/v1/{cnpj}")
                except Exception as e:
                    st.error(f"Erro BrasilAPI: {e}")
                    dados = {}

        # Verificando nome fantasia
        nome_fantasia = dados['nome_fantasia'] if dados['nome_fantasia'] != '' else "sem nome fantasia"

        st.markdown("---")
        st.header(f"📑 Detalhes do CNPJ {cnpj} - {nome_fantasia}")

        if dados.get("cnaes_secundarios"):
            st.subheader("CNAEs Secundários")
            st.dataframe(pd.DataFrame(dados["cnaes_secundarios"]).astype(str),
                         use_container_width=True)

        if dados.get("qsa"):
            st.subheader("QSA (Quadro de Sócios e Administradores)")
            qsa = [
                {"Sócio": f"#{i+1}",
                 **{k: ("" if v is None else str(v)) for k, v in s.items()}}
                for i, s in enumerate(dados["qsa"])
            ]
            st.dataframe(pd.DataFrame(qsa).astype(str), use_container_width=True)
else:
    if st.session_state.result_df is not None:
        st.sidebar.info("A coluna **CNPJ** não existe na sua busca.")
