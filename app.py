import streamlit as st
import pandas as pd
from support_functions import list_files, search_engine
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
    sample = pd.read_csv(Path(files[0]), sep=";", encoding="utf-8", nrows=1, dtype=str)
    coluna_busca = st.selectbox("Coluna para buscar:", sample.columns, index=1)

# ---------- Campo de texto e botão ----------
query = st.text_input("Digite o termo para buscar:")

# ---------- Busca principal ----------
if st.button("Buscar"):
    if not query.strip():
        st.warning("Digite algo para buscar 📌")
    else:
        with st.spinner("Buscando em todos os arquivos..."):
            result_df = search_engine(query, files, column=coluna_busca, exact_match=False)

        if result_df.empty:
            st.info("Nenhum resultado encontrado.")
            st.session_state.result_df = None
            st.session_state.cnpj_options = ["-- Selecione um CNPJ --"]
        else:
            st.session_state.result_df = result_df
            if "CNPJ" in result_df.columns:
                result_df["CNPJ"] = result_df["CNPJ"].astype(str)
                opts = sorted(result_df["CNPJ"].dropna().unique().tolist())
            else:
                opts = []

            st.session_state.cnpj_options = ["-- Selecione um CNPJ --"] + opts

        st.session_state.selected_cnpj = "-- Selecione um CNPJ --"  # reset

# ---------- Resultado principal ----------
if st.session_state.result_df is not None:
    st.success(f"{len(st.session_state.result_df)} registros encontrados.")
    st.dataframe(st.session_state.result_df.astype(str), use_container_width=True)

# ---------- Selectbox de CNPJ ----------
if st.session_state.result_df is not None and "CNPJ" in st.session_state.result_df.columns:

    # 1) cria o selectbox com OUTRA chave
    selected = st.sidebar.selectbox(
        "Escolha um CNPJ para ver detalhes:",
        st.session_state.cnpj_options,
        key="cnpj_select",  # <- chave só do widget
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
        nome_fantasia = dados.get('nome_fantasia') or "sem nome fantasia"

        st.markdown("---")
        st.header(f"📑 Detalhes do CNPJ {cnpj} - {nome_fantasia}")

        if dados.get("cnaes_secundarios"):
            st.subheader("CNAEs Secundários")
            st.dataframe(pd.DataFrame(dados["cnaes_secundarios"]).astype(str),
                         use_container_width=True)

        if dados.get("qsa"):
            st.subheader("QSA (Quadro de Sócios e Administradores)")
            qsa = [
                {"Sócio": f"#{i + 1}",
                 **{k: ("" if v is None else str(v)) for k, v in s.items()}}
                for i, s in enumerate(dados["qsa"])
            ]
            st.dataframe(pd.DataFrame(qsa).astype(str), use_container_width=True)
else:
    if st.session_state.result_df is not None:
        st.sidebar.info("A coluna **CNPJ** não existe na sua busca.")
