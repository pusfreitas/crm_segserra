import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import conectar_db, obter_permissoes_perfil
from utils import formatar_moeda, avaliar_status_followup, converter_str_data

PERFIS_COM_PROPOSTAS = {"Administrador", "Comercial / Atendimento"}


def _solicitar_navegacao(nome_tela):
    perfil_usr = st.session_state.get("perfil_usuario") or "Comercial / Atendimento"
    perms = obter_permissoes_perfil(perfil_usr)
    telas_permitidas = perms.get("telas") or ["Dashboard"]
    if nome_tela in telas_permitidas:
        st.session_state.navegar_para_pendente = nome_tela
    else:
        st.session_state.aviso_navegacao_dashboard = (
            f"Seu perfil ({perfil_usr}) não possui acesso à tela '{nome_tela}'."
        )


def _reagendar_dashboard(cliente_id, nova_data_obj):
    data_str = nova_data_obj.strftime("%d/%m/%Y")
    conn = conectar_db()
    conn.execute(
        "UPDATE clientes SET proximo_contato = ? WHERE id = ?",
        (data_str, int(cliente_id))
    )
    conn.commit()
    conn.close()
    st.session_state.msg_sucesso_dashboard = f"✅ Follow-up atualizado para {data_str}!"


def _renderizar_card_followups(df_urgentes):
    with st.container(border=True):
        st.subheader("⏰ Follow-ups Vencidos ou Vencendo Hoje")
        if df_urgentes.empty:
            st.success("Nenhum follow-up vencido ou previsto para hoje.")
        else:
            df_exib_f = df_urgentes[[
                "Empresa", "Responsável", "Contato", "Data Follow-up", "Status"
            ]]
            st.dataframe(df_exib_f, use_container_width=True, hide_index=True)

            opcoes_cli_urg = {
                f"{r['Empresa']} ({r['Status']})": r["id"]
                for _, r in df_urgentes.iterrows()
            }
            c_sel, c_dt, c_btn = st.columns([2.2, 1.3, 1.1])
            with c_sel:
                cli_urg_lbl = st.selectbox(
                    "Reagendar retorno:",
                    list(opcoes_cli_urg.keys()),
                    key="dash_sel_cli_fu"
                )
            with c_dt:
                nova_dt = st.date_input(
                    "Nova data",
                    value=date.today() + timedelta(days=3),
                    key="dash_nova_dt_fu"
                )
            with c_btn:
                st.write("")
                st.write("")
                if st.button("Salvar", key="dash_btn_reagendar", type="primary", use_container_width=True):
                    _reagendar_dashboard(opcoes_cli_urg[cli_urg_lbl], nova_dt)
                    st.rerun()

        st.button(
            "Abrir Agenda Completa",
            use_container_width=True,
            key="dash_btn_abrir_agenda",
            on_click=_solicitar_navegacao,
            args=("Agenda & Follow-ups",)
        )


def renderizar_tela_dashboard():
    st.title("📊 Dashboard")
    nome_usr = st.session_state.get("nome_usuario") or st.session_state.get("usuario_atual") or "Usuário"
    perfil_usr = st.session_state.get("perfil_usuario") or "Comercial / Atendimento"
    pode_ver_propostas = perfil_usr in PERFIS_COM_PROPOSTAS

    st.caption(f"Bem-vindo(a), **{nome_usr}** — Visão rápida de acompanhamentos e registros do sistema.")

    if "aviso_navegacao_dashboard" in st.session_state:
        st.warning(st.session_state.aviso_navegacao_dashboard)
        del st.session_state.aviso_navegacao_dashboard

    if "msg_sucesso_dashboard" in st.session_state:
        st.success(st.session_state.msg_sucesso_dashboard)
        st.toast(st.session_state.msg_sucesso_dashboard)
        del st.session_state.msg_sucesso_dashboard

    conn = conectar_db()
    df_prop = pd.read_sql_query("""
        SELECT p.id, p.data_emissao, c.razao_social, p.solicitante,
               p.valor_investimento, p.status_proposta
        FROM propostas p
        JOIN clientes c ON p.cliente_id = c.id
        ORDER BY p.id DESC
    """, conn) if pode_ver_propostas else pd.DataFrame()

    df_cli = pd.read_sql_query("""
        SELECT id, razao_social, responsavel_pf, telefone, email,
               etapa_funil, valor_estimado, proximo_contato
        FROM clientes
        ORDER BY razao_social ASC
    """, conn)

    df_chk = pd.read_sql_query("""
        SELECT ch.id as ID, ch.data_visita as 'Data',
               c.razao_social as 'Empresa',
               ch.responsavel_tecnico as 'Responsável Técnico',
               ch.qtd_nao as 'Pendências (Não)'
        FROM checklists_visita ch
        JOIN clientes c ON ch.cliente_id = c.id
        ORDER BY ch.id DESC
    """, conn)
    conn.close()

    if pode_ver_propostas and not df_prop.empty:
        df_prop["status_normalizado"] = df_prop["status_proposta"].fillna("Aguardando Aceite")
        df_abertas = df_prop[df_prop["status_normalizado"] == "Aguardando Aceite"].copy()
    else:
        df_abertas = pd.DataFrame()

    qtd_abertas = len(df_abertas)
    total_aberto = float(df_abertas["valor_investimento"].sum()) if not df_abertas.empty else 0.0

    vencidos_rows = []
    hoje_rows = []
    for _, r in df_cli.iterrows():
        status_cod, status_lbl = avaliar_status_followup(r.get("proximo_contato") or "")
        item = {
            "id": int(r["id"]),
            "Empresa": r["razao_social"],
            "Responsável": r["responsavel_pf"] or "—",
            "Contato": r["telefone"] or r["email"] or "—",
            "Etapa": r["etapa_funil"] or "—",
            "Data Follow-up": r["proximo_contato"] or "",
            "Status": status_lbl,
            "_data_obj": converter_str_data(r.get("proximo_contato") or ""),
        }
        if status_cod == "ATRASADO":
            vencidos_rows.append(item)
        elif status_cod == "HOJE":
            hoje_rows.append(item)

    vencidos_rows.sort(key=lambda x: x["_data_obj"] or date.max)
    df_vencidos = pd.DataFrame(vencidos_rows)
    df_hoje = pd.DataFrame(hoje_rows)
    df_urgentes = pd.concat([df_vencidos, df_hoje], ignore_index=True)

    qtd_checklists = len(df_chk)
    total_pendencias_chk = int(df_chk["Pendências (Não)"].sum()) if not df_chk.empty else 0

    if pode_ver_propostas:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("📄 Propostas em Aberto", qtd_abertas)
        with m2:
            st.metric("💰 Valor em Aberto", formatar_moeda(total_aberto))
        with m3:
            st.metric("🔴 Follow-ups Vencidos", len(df_vencidos))
        with m4:
            st.metric("🟡 Follow-ups para Hoje", len(df_hoje))
    else:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("🔴 Follow-ups Vencidos", len(df_vencidos))
        with m2:
            st.metric("🟡 Follow-ups para Hoje", len(df_hoje))
        with m3:
            st.metric("✅ Checklists Emitidos", qtd_checklists)

    st.divider()

    if pode_ver_propostas:
        col_esq, col_dir = st.columns([1.15, 1.25])
        with col_esq:
            with st.container(border=True):
                st.subheader("📄 Propostas em Aberto")
                if df_abertas.empty:
                    st.info("Não há propostas aguardando aceite no momento.")
                else:
                    df_exib_p = df_abertas[[
                        "id", "data_emissao", "razao_social", "solicitante", "valor_investimento"
                    ]].rename(columns={
                        "id": "Nº",
                        "data_emissao": "Emissão",
                        "razao_social": "Cliente",
                        "solicitante": "Solicitante",
                        "valor_investimento": "Valor (R$)",
                    })
                    st.dataframe(df_exib_p, use_container_width=True, hide_index=True)

                st.button(
                    "Ir para Emissão de Propostas",
                    use_container_width=True,
                    key="dash_btn_ir_propostas",
                    on_click=_solicitar_navegacao,
                    args=("Emissão de Propostas",)
                )

        with col_dir:
            _renderizar_card_followups(df_urgentes)
    else:
        _renderizar_card_followups(df_urgentes)

    st.divider()

    with st.container(border=True):
        st.subheader("✅ Checklists de Visita Técnica Emitidos")
        k1, k2 = st.columns(2)
        with k1:
            st.metric("Total de Checklists Emitidos", qtd_checklists)
        with k2:
            st.metric("Total de Pendências ('Não')", total_pendencias_chk)

        if df_chk.empty:
            st.info("Nenhum checklist de visita técnica emitido até o momento.")
        else:
            st.dataframe(df_chk.head(10), use_container_width=True, hide_index=True)

        st.button(
            "Ir para Checklist Visita Técnica",
            use_container_width=True,
            key="dash_btn_checklist",
            on_click=_solicitar_navegacao,
            args=("Checklist Visita Técnica",)
        )