import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta, date
from database import conectar_db, ETAPAS_FUNIL
from utils import converter_str_data
from componentes import renderizar_edicao_atividade


def renderizar_tela_atividades():
    st.title("📋 Lançamento e Consulta de Atividades")

    if "msg_sucesso_atividade" in st.session_state:
        st.success(st.session_state.msg_sucesso_atividade)
        st.toast(st.session_state.msg_sucesso_atividade)
        del st.session_state.msg_sucesso_atividade

    conn = conectar_db()
    df_clientes = pd.read_sql_query("""
        SELECT id, cnpj, razao_social, responsavel_pf, cidade, etapa_funil, proximo_contato 
        FROM clientes 
        ORDER BY razao_social
    """, conn)
    conn.close()

    if df_clientes.empty:
        st.warning("Cadastre pelo menos um cliente antes de lançar atividades.")
        return

    opcoes_clientes = {
        f"{row['razao_social']} | Resp: {row['responsavel_pf']} ({row['etapa_funil']})": row
        for _, row in df_clientes.iterrows()
    }
    lista_labels = list(opcoes_clientes.keys())

    idx_padrao = 0
    if st.session_state.get("cliente_pre_selecionado_id") is not None:
        for idx, (_, row_c) in enumerate(opcoes_clientes.items()):
            if int(row_c['id']) == st.session_state.cliente_pre_selecionado_id:
                idx_padrao = idx
                break
        st.session_state.cliente_pre_selecionado_id = None

    if "limpar_desc_ativ" not in st.session_state:
        st.session_state.limpar_desc_ativ = False
    if st.session_state.limpar_desc_ativ:
        st.session_state.ativ_descricao = ""
        st.session_state.limpar_desc_ativ = False

    atendente_atual = st.session_state.get("nome_usuario") or st.session_state.get("usuario_atual") or "Administrador"

    st.subheader("Registrar Novo Atendimento")
    with st.container(border=True):
        st.caption(f"👤 **Atendente responsável pelo lançamento:** `{atendente_atual}`")
        col_cli, col_funil_at, col_prox_at = st.columns([2.2, 1.5, 1.2])
        with col_cli:
            cliente_escolhido_lbl = st.selectbox("Selecione o Cliente *", lista_labels, index=idx_padrao)
        cliente_row_at = opcoes_clientes[cliente_escolhido_lbl]
        etapa_cli_atual = cliente_row_at["etapa_funil"] if cliente_row_at["etapa_funil"] in ETAPAS_FUNIL else \
        ETAPAS_FUNIL[0]
        dt_prox_cli = converter_str_data(cliente_row_at["proximo_contato"]) or (date.today() + timedelta(days=7))

        with col_funil_at:
            nova_etapa_atend = st.selectbox(
                "Atualizar Etapa no Funil:",
                ETAPAS_FUNIL,
                index=ETAPAS_FUNIL.index(etapa_cli_atual)
            )
        with col_prox_at:
            novo_followup_atend = st.date_input("Agendar Próximo Contato:", value=dt_prox_cli)
            agendar_fw_check = st.checkbox("Atualizar data de retorno", value=True)

        c1, c2, c3, c4, c5 = st.columns([1.3, 1.1, 1.1, 1.3, 1.8])
        with c1:
            data_atend = st.date_input("Data do Atendimento *", value=datetime.today())
        with c2:
            hora_inicio = st.time_input("Horário Inicial (De) *", value=time(10, 0), step=timedelta(minutes=15))
        with c3:
            hora_fim = st.time_input("Horário Final (Até) *", value=time(12, 0), step=timedelta(minutes=15))

        dt_inicio = datetime.combine(data_atend, hora_inicio)
        dt_fim = datetime.combine(data_atend, hora_fim)
        segundos_totais = int((dt_fim - dt_inicio).total_seconds())

        with c4:
            if segundos_totais > 0:
                horas = segundos_totais // 3600
                minutos = (segundos_totais % 3600) // 60
                tempo_formatado = f"{horas:02d}h {minutos:02d}m"
                st.metric("⏱️ Tempo Gasto", tempo_formatado)
            else:
                tempo_formatado = "Inválido"
                st.metric("⏱️ Tempo Gasto", "Inválido")

        with c5:
            modalidade = st.selectbox("Modalidade de Atendimento *", [
                "WhatsApp", "Telefone", "Presencial / Visita Técnica", "E-mail", "Reunião Online", "Outros"
            ])

        if segundos_totais <= 0:
            st.warning("⚠️ O Horário Final ('Até') deve ser maior que o Horário Inicial ('De').")

        descricao = st.text_area("O que foi feito? (Detalhamento da atividade) *", key="ativ_descricao", height=110)

        registrar = st.button("✅ Lançar Atividade", use_container_width=True, type="primary")

        if registrar:
            if segundos_totais <= 0:
                st.error(
                    "Corrija o intervalo de horário antes de salvar (o horário final deve ser posterior ao inicial).")
            elif not descricao.strip():
                st.error("Por favor, descreva o que foi realizado no atendimento.")
            else:
                str_inicio = hora_inicio.strftime("%H:%M")
                str_fim = hora_fim.strftime("%H:%M")
                periodo_str = f"{str_inicio} às {str_fim}"
                cid_at = int(cliente_row_at["id"])

                conn = conectar_db()
                conn.execute("""
                    INSERT INTO atividades (
                        cliente_id, data, horario, hora_inicio, hora_fim, 
                        tempo_total, modalidade, descricao, atendente
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cid_at,
                    data_atend.strftime("%d/%m/%Y"),
                    periodo_str,
                    str_inicio,
                    str_fim,
                    tempo_formatado,
                    modalidade,
                    descricao.strip(),
                    atendente_atual
                ))

                if agendar_fw_check:
                    str_fw = novo_followup_atend.strftime("%d/%m/%Y")
                    conn.execute("UPDATE clientes SET etapa_funil = ?, proximo_contato = ? WHERE id = ?",
                                 (nova_etapa_atend, str_fw, cid_at))
                else:
                    conn.execute("UPDATE clientes SET etapa_funil = ? WHERE id = ?", (nova_etapa_atend, cid_at))

                conn.commit()
                conn.close()

                st.session_state.msg_sucesso_atividade = f"✅ Atividade registrada por '{atendente_atual}'! (Duração: {tempo_formatado} | Etapa: {nova_etapa_atend})"
                st.session_state.limpar_desc_ativ = True
                st.rerun()

    st.divider()
    st.subheader("Histórico Geral de Atividades Realizadas")
    conn = conectar_db()
    df_hist = pd.read_sql_query("""
        SELECT a.id as ID, a.data as Data, 
               CASE WHEN a.hora_inicio != '' THEN a.hora_inicio ELSE a.horario END as 'Início',
               a.hora_fim as 'Término',
               a.tempo_total as 'Tempo Gasto',
               a.atendente as 'Atendente',
               c.razao_social as Empresa, 
               c.etapa_funil as 'Etapa Atual',
               c.proximo_contato as 'Próx. Contato',
               c.cidade as Cidade, c.responsavel_pf as Responsável, 
               a.modalidade as Modalidade, a.descricao as Detalhamento
        FROM atividades a
        JOIN clientes c ON a.cliente_id = c.id
        ORDER BY a.id DESC
    """, conn)
    conn.close()

    if df_hist.empty:
        st.info("Nenhuma atividade registrada ainda.")
    else:
        atendentes_disp = ["Todos os Atendentes"] + sorted(
            [a for a in df_hist["Atendente"].dropna().unique() if str(a).strip() != ""])
        filtro_atend = st.selectbox("Filtrar histórico por Atendente:", atendentes_disp)

        df_mostrar = df_hist if filtro_atend == "Todos os Atendentes" else df_hist[df_hist["Atendente"] == filtro_atend]
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        renderizar_edicao_atividade(df_mostrar, sufixo_key="aba_geral")