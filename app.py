import streamlit as st
from database import inicializar_db
from utils import aplicar_identidade_visual, renderizar_logo_segserra
from tela_login import renderizar_tela_login, realizar_logout, renderizar_gestao_usuarios
from tela_clientes import renderizar_tela_clientes
from tela_funil import renderizar_tela_funil
from tela_atividades import renderizar_tela_atividades

st.set_page_config(
    page_title="SegSerra CRM - Gestão Comercial e SST",
    page_icon="➕",
    layout="wide"
)

# Aplica o CSS oficial (Bree Serif + #2dd2cd) e inicializa o banco
aplicar_identidade_visual()
inicializar_db()

if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario_atual" not in st.session_state:
    st.session_state.usuario_atual = None

if "menu_pagina" not in st.session_state:
    st.session_state.menu_pagina = "1. Clientes (Consulta e Cadastro)"

if not st.session_state.logado:
    renderizar_tela_login()
else:
    with st.sidebar:
        renderizar_logo_segserra(centralizado=True, tema_escuro=True)
        st.divider()
        if st.session_state.usuario_atual:
            st.markdown(f"👤 **{st.session_state.get('nome_usuario', st.session_state.usuario_atual)}**")
            st.caption(
                f"Login: `{st.session_state.usuario_atual}` | Perfil: **{st.session_state.get('perfil_usuario', '')}**"
            )
        st.divider()

        pagina = st.radio(
            "NAVEGAÇÃO DO SISTEMA",
            [
                "1. Clientes (Consulta e Cadastro)",
                "2. Funil de Vendas (Pipeline)",
                "3. Lançar Atividades",
                "4. Usuários e Senhas"
            ],
            key="menu_pagina"
        )
        st.divider()
        st.button("🚪 Sair (Logout)", on_click=realizar_logout, use_container_width=True)
        st.caption("📍 SegSerra — Bento Gonçalves/RS")

    if pagina == "1. Clientes (Consulta e Cadastro)":
        renderizar_tela_clientes()
    elif pagina == "2. Funil de Vendas (Pipeline)":
        renderizar_tela_funil()
    elif pagina == "3. Lançar Atividades":
        renderizar_tela_atividades()
    elif pagina == "4. Usuários e Senhas":
        renderizar_gestao_usuarios()