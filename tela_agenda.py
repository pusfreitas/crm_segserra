import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import conectar_db
from utils import converter_str_data, avaliar_status_followup, formatar_moeda
from componentes import modal_editar_cliente, ir_para_lancamento_cliente

def reagendar_followup_rapido(cliente_id, nova_data_obj):
    data_fmt = nova_data_obj.strftime("%d/%m/%Y")
    conn = conectar_db()
    conn.execute("UPDATE clientes SET proximo_contato = ? WHERE id = ?", (data_fmt, int(cliente_id)))
    conn.commit()
    conn.close()
    st.toast(f"Follow-up reagendado para {data_fmt}!")

def renderizar_alerta_dia_topo():
    """Exibe um banner chamativo no topo do sistema quando há follow-ups para hoje ou atrasados."""
    conn = conectar_db()
    df_c = pd.read_sql_query("""
        SELECT id, razao_social, responsavel_pf, telefone, proximo_contato, etapa_funil, categoria
        FROM clientes
        WHERE proximo_contato IS NOT NULL AND TRIM(proximo_contato) != ''
    """, conn)
    conn.close()

    if df_c.empty:
        return

    hoje = date.today()
    atrasados = []
    para_hoje = []

    for _, r in df_c.iterrows():
        dt = converter_str_data(r["proximo_contato"])
        if not dt:
            continue
        dias = (dt - hoje).days
        if dias < 0:
            atrasados.append((r, abs(dias)))
        elif dias == 0:
            para_hoje.append(r)

    if atrasados or para_hoje:
        with st.container(border=True):
            st.markdown(
                """
                <div style="background: linear-gradient(90deg, #0f5257 0%, #0d9488 100%); 
                            color: #ffffff; padding: 12px 18px; border-radius: 8px; 
                            border-left: 6px solid #facc15; margin-bottom: 8px;">
                    <span style="font-size: 16px; font-weight: 700;">
                        🚨 CENTRAL DE AVISOS DO DIA — ATENÇÃO AOS FOLLOW-UPS!
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
            c1, c2, c3 = st.columns([2, 2, 1.2])
            with c1:
                if para_hoje:
                    st.warning(f"🟡 **{len(para_hoje)} retorno(s) agendado(s) para HOJE ({hoje.strftime('%d/%m/%Y')}):**\n" +
                               "\n".join([f"• {x['razao_social']} ({x['responsavel_pf']})" for x in para_hoje[:4]]))
                else:
                    st.info("🟡 Nenhum retorno agendado especificamente para hoje.")
            with c2:
                if atrasados:
                    st.error(f"🔴 **{len(atrasados)} follow-up(s) ATRASADO(S):**\n" +
                             "\n".join([f"• {x[0]['razao_social']} ({x[1]}d de atraso)" for x in atrasados[:4]]))
                else:
                    st.success("🟢 Nenhum follow-up atrasado!")
            with c3:
                st.write("")
                if st.button("📅 Abrir Agenda Completa", key="btn_ir_agenda_topo", type="primary", use_container_width=True):
                    st.session_state.menu_pagina = "5. Agenda & Follow-ups"
                    st.rerun()

def renderizar_tela_agenda():
    st.title("📅 Agenda Comercial & Controle de Follow-up")

    conn = conectar_db()
    df_clientes = pd.read_sql_query("""
        SELECT c.*, COUNT(a.id) as total_atividades
        FROM clientes c
        LEFT JOIN atividades a ON c.id = a.cliente_id
        GROUP BY c.id
    """, conn)
    conn.close()

    if df_clientes.empty:
        st.info("Nenhuma empresa cadastrada ainda.")
        return

    hoje = date.today()
    limite_semana = hoje + timedelta(days=7)

    registros = []
    for _, r in df_clientes.iterrows():
        dt_fw = converter_str_data(r["proximo_contato"])
        status_cod, status_badge = avaliar_status_followup(r["proximo_contato"])
        registros.append({
            **r.to_dict(),
            "dt_fw": dt_fw,
            "status_cod": status_cod,
            "status_badge": status_badge
        })

    df_ag = pd.DataFrame(registros)
    df_com_data = df_ag[df_ag["dt_fw"].notna()].sort_values("dt_fw")

    df_hoje_atraso = df_com_data[df_com_data["dt_fw"] <= hoje]
    df_semana = df_com_data[(df_com_data["dt_fw"] > hoje) & (df_com_data["dt_fw"] <= limite_semana)]
    df_sem_data = df_ag[df_ag["dt_fw"].isna()]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🚨 Hoje / Atrasados", len(df_hoje_atraso))
    m2.metric("📆 Próximos 7 Dias", len(df_semana))
    m3.metric("📋 Total Agendados", len(df_com_data))
    m4.metric("⚪ Sem Data Definida", len(df_sem_data))

    st.divider()

    aba_urgente, aba_semana, aba_todos, aba_sem_data = st.tabs([
        f"🚨 Hoje e Atrasados ({len(df_hoje_atraso)})",
        f"📆 Próximos 7 Dias ({len(df_semana)})",
        f"📋 Todos Agendados ({len(df_com_data)})",
        f"⚪ Sem Follow-up ({len(df_sem_data)})"
    ])

    def exibir_lista_cartoes(df_subset, key_prefix):
        if df_subset.empty:
            st.success("Nenhum registro nesta faixa de agenda.")
            return

        for _, row in df_subset.iterrows():
            cid = int(row["id"])
            with st.container(border=True):
                c_info, c_reag, c_acoes = st.columns([2.5, 1.5, 1.3])
                with c_info:
                    st.markdown(f"### {row['razao_social']}")
                    st.markdown(f"**{row['status_badge']}** | Categoria: **{row.get('categoria', 'Prospecto')}** | Etapa: *{row['etapa_funil']}*")
                    st.markdown(
                        f"👤 **Responsável:** {row['responsavel_pf']} | "
                        f"📞 **Fone:** {row['telefone'] or '-'} | "
                        f"💵 **Proposta:** {formatar_moeda(row['valor_estimado'])}"
                    )
                    if row.get("servico_interesse"):
                        st.caption(f"🎯 Interesse: {row['servico_interesse']} | 📍 {row['cidade'] or '-'}/{row['uf'] or '-'}")
                with c_reag:
                    data_padrao = row["dt_fw"] if pd.notna(row["dt_fw"]) else (hoje + timedelta(days=3))
                    nova_dt = st.date_input("Reagendar para:", value=data_padrao, key=f"ag_dt_{key_prefix}_{cid}")
                    if st.button("🔄 Salvar Nova Data", key=f"ag_btn_{key_prefix}_{cid}", use_container_width=True):
                        reagendar_followup_rapido(cid, nova_dt)
                        st.rerun()
                with c_acoes:
                    st.write("")
                    if st.button("✏️ Editar Cadastro", key=f"ag_ed_{key_prefix}_{cid}", use_container_width=True):
                        modal_editar_cliente(cid)
                    st.button(
                        "➕ Lançar Atividade",
                        key=f"ag_at_{key_prefix}_{cid}",
                        on_click=ir_para_lancamento_cliente,
                        args=(cid,),
                        type="primary",
                        use_container_width=True
                    )

    with aba_urgente:
        exibir_lista_cartoes(df_hoje_atraso, "urg")
    with aba_semana:
        exibir_lista_cartoes(df_semana, "sem")
    with aba_todos:
        exibir_lista_cartoes(df_com_data, "tod")
    with aba_sem_data:
        exibir_lista_cartoes(df_sem_data, "sdata")