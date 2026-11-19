import streamlit as st
from utils import aplicar_identidade_visual, renderizar_logo_segserra
from tela_login import renderizar_tela_login, realizar_logout, renderizar_gestao_usuarios
from tela_dashboard import renderizar_tela_dashboard
from tela_clientes import renderizar_tela_clientes
from tela_funil import renderizar_tela_funil
from tela_atividades import renderizar_tela_atividades
from tela_agenda import renderizar_tela_agenda, renderizar_alerta_dia_topo
from tela_propostas import renderizar_tela_propostas, renderizar_aceite_cliente_por_token
from tela_checklist import renderizar_tela_checklist

ORDEM_MENU = [
    "Dashboard",
    "Clientes (Consulta e Cadastro)",
    "Funil de Vendas (Pipeline)",
    "Lançar Atividades",
    "Agenda & Follow-ups",
    "Emissão de Propostas",
    "Checklist Visita Técnica",
    "Usuários e Senhas"
]

st.set_page_config(
    page_title="SegSerra CRM - Gestão Comercial e SST",
    page_icon="➕",
    layout="wide"
)

    inicializar_db()

    token_proposta_url = st.query_params.get("proposta")
    if token_proposta_url:
        renderizar_aceite_cliente_por_token(token_proposta_url)
    else:
        if "menu_fixo" not in st.session_state:
            st.session_state.menu_fixo = True

        aplicar_identidade_visual(menu_fixo=st.session_state.menu_fixo)

        if "logado" not in st.session_state:
            st.session_state.logado = False

if "usuario_atual" not in st.session_state:
    st.session_state.usuario_atual = None

if "menu_pagina" not in st.session_state:
    st.session_state.menu_pagina = "1. Clientes (Consulta e Cadastro)"

if not st.session_state.logado:
    renderizar_tela_login()
else:
    perfil_atual = st.session_state.get("perfil_usuario", "Comercial / Atendimento")
            perms_atual = obter_permissoes_perfil(perfil_atual)
            telas_autorizadas = [t for t in ORDEM_MENU if t in (perms_atual.get("telas") or [])]
            if not telas_autorizadas:
                telas_autorizadas = ["Dashboard"]

            destino_pendente = st.session_state.get("navegar_para_pendente")
            if destino_pendente:
                st.session_state.navegar_para_pendente = None
                if destino_pendente in telas_autorizadas:
                    st.session_state.pagina_ativa = destino_pendente

            if "pagina_ativa" not in st.session_state or st.session_state.pagina_ativa not in telas_autorizadas:
                st.session_state.pagina_ativa = telas_autorizadas[0]

            idx_pagina = telas_autorizadas.index(st.session_state.pagina_ativa)

            with st.sidebar:
                renderizar_logo_segserra(centralizado=True, tema_escuro=True)
                st.divider()if st.session_state.usuario_atual:
            st.markdown(f"👤 **{st.session_state.get('nome_usuario', st.session_state.usuario_atual)}**")
            st.caption(
                f"Login: `{st.session_state.usuario_atual}` | Perfil: **{st.session_state.get('perfil_usuario', '')}**"
            )
        st.divider()

                pagina = st.radio(
                    "NAVEGAÇÃO DO SISTEMA",
                )
                st.divider()
                st.button("🚪 Sair (Logout)", on_click=realizar_logout, use_container_width=True)
                st.caption("📍 SegSerra — Bento Gonçalves/RS")

                renderizar_tela_clientes()
                renderizar_tela_funil()
                renderizar_tela_atividades()
                renderizar_gestao_usuarios()