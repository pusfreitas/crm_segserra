import streamlit as st
from database import inicializar_db, obter_permissoes_perfil
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

try:
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
                st.divider()

                pagina = st.radio(
                    "NAVEGAÇÃO DO SISTEMA",
                    telas_autorizadas,
                    index=idx_pagina,
                    key="radio_menu_pagina"
                )
                st.session_state.pagina_ativa = pagina

                st.divider()
                menu_fixo_ativo = st.checkbox(
                    "📌 Deixar menu lateral fixo",
                    value=st.session_state.menu_fixo,
                    key="chk_menu_fixo"
                )
                if menu_fixo_ativo != st.session_state.menu_fixo:
                    st.session_state.menu_fixo = menu_fixo_ativo
                    st.rerun()

                st.write("")
                st.divider()

                if st.session_state.usuario_atual:
                    st.markdown(f"👤 **{st.session_state.get('nome_usuario', st.session_state.usuario_atual)}**")
                    st.caption(
                        f"Login: `{st.session_state.usuario_atual}` | Perfil: **{perfil_atual}**"
                    )

                st.button("🚪 Sair (Logout)", on_click=realizar_logout, use_container_width=True)
                st.caption("📍 SegSerra — Bento Gonçalves/RS")

            if pagina not in ("Dashboard", "Agenda & Follow-ups"):
                renderizar_alerta_dia_topo()

            if pagina not in telas_autorizadas:
                st.error("Acesso bloqueado: seu perfil não tem permissão para acessar esta tela.")
            elif pagina == "Dashboard":
                renderizar_tela_dashboard()
            elif pagina == "Clientes (Consulta e Cadastro)":
                renderizar_tela_clientes()
            elif pagina == "Funil de Vendas (Pipeline)":
                renderizar_tela_funil()
            elif pagina == "Lançar Atividades":
                renderizar_tela_atividades()
            elif pagina == "Agenda & Follow-ups":
                renderizar_tela_agenda()
            elif pagina == "Emissão de Propostas":
                renderizar_tela_propostas()
            elif pagina == "Checklist Visita Técnica":
                renderizar_tela_checklist()
            elif pagina == "Usuários e Senhas":
                renderizar_gestao_usuarios()

except Exception as e:
    st.error("Ocorreu um erro ao carregar o CRM:")
    st.exception(e)