import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta, date
from database import conectar_db, ETAPAS_FUNIL, OPCOES_SERVICOS
from utils import limpar_numeros, converter_str_data, converter_str_hora


def ir_para_lancamento_cliente(cliente_id):
    st.session_state.cliente_pre_selecionado_id = int(cliente_id)
    st.session_state.menu_pagina = "3. Lançar Atividades"


def alterar_etapa_funil_rapido(cliente_id, nova_etapa):
    conn = conectar_db()
    conn.execute("UPDATE clientes SET etapa_funil = ? WHERE id = ?", (nova_etapa, int(cliente_id)))
    conn.commit()
    conn.close()
    st.toast(f"Etapa atualizada para: {nova_etapa}")


@st.dialog("✏️ Alterar / Excluir Cadastro da Empresa", width="large")
def modal_editar_cliente(cliente_id):
    conn = conectar_db()
    df_c = pd.read_sql_query("""
        SELECT c.*, COUNT(a.id) as total_atividades 
        FROM clientes c 
        LEFT JOIN atividades a ON c.id = a.cliente_id 
        WHERE c.id = ?
        GROUP BY c.id
    """, conn, params=(int(cliente_id),))
    conn.close()

    if df_c.empty:
        st.error("Cliente não localizado.")
        return

    cliente_sel = df_c.iloc[0]
    st.markdown(f"**CNPJ:** `{cliente_sel['cnpj']}` | **Atividades registradas:** `{cliente_sel['total_atividades']}`")

    with st.form(f"form_modal_cliente_{cliente_id}"):
        c1, c2 = st.columns(2)
        with c1:
            nova_razao = st.text_input("Razão Social *", value=cliente_sel["razao_social"] or "")
            novo_fantasia = st.text_input("Nome Fantasia", value=cliente_sel["nome_fantasia"] or "")
            novo_resp = st.text_input("Responsável (PF) *", value=cliente_sel["responsavel_pf"] or "")
        with c2:
            novo_tel = st.text_input("Telefone / WhatsApp", value=cliente_sel["telefone"] or "")
            novo_email = st.text_input("E-mail", value=cliente_sel["email"] or "")

        st.markdown("##### 📊 Posição no Funil e Próximo Contato (Follow-up)")
        f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.8, 1.2])
        etapa_atual = cliente_sel["etapa_funil"] if cliente_sel["etapa_funil"] in ETAPAS_FUNIL else ETAPAS_FUNIL[0]
        serv_atual = cliente_sel["servico_interesse"] if cliente_sel["servico_interesse"] in OPCOES_SERVICOS else \
        OPCOES_SERVICOS[0]
        dt_prox_atual = converter_str_data(cliente_sel["proximo_contato"]) or (date.today() + timedelta(days=3))
        tem_data_salva = bool(str(cliente_sel["proximo_contato"] or "").strip())

        with f1:
            nova_etapa = st.selectbox("Etapa do Funil", ETAPAS_FUNIL, index=ETAPAS_FUNIL.index(etapa_atual))
        with f2:
            novo_valor = st.number_input("Valor Proposta (R$)", min_value=0.0, step=100.0,
                                         value=float(cliente_sel["valor_estimado"] or 0.0))
        with f3:
            novo_servico = st.selectbox("Serviço / Interesse Principal", OPCOES_SERVICOS,
                                        index=OPCOES_SERVICOS.index(serv_atual))
        with f4:
            nova_data_prox = st.date_input("Próximo Contato", value=dt_prox_atual)
            manter_followup = st.checkbox("Agendar Follow-up", value=tem_data_salva)

        st.markdown("##### 📍 Endereço")
        e1, e2, e3, e4 = st.columns([1.2, 3, 1, 1.5])
        with e1:
            novo_cep = st.text_input("CEP", value=cliente_sel["cep"] or "")
        with e2:
            novo_log = st.text_input("Logradouro", value=cliente_sel["logradouro"] or "")
        with e3:
            novo_num = st.text_input("Número", value=cliente_sel["numero"] or "")
        with e4:
            novo_comp = st.text_input("Complemento", value=cliente_sel["complemento"] or "")

        e5, e6, e7 = st.columns([2.5, 2.5, 1])
        with e5:
            novo_bairro = st.text_input("Bairro", value=cliente_sel["bairro"] or "")
        with e6:
            nova_cidade = st.text_input("Cidade", value=cliente_sel["cidade"] or "")
        with e7:
            nova_uf = st.text_input("UF", value=cliente_sel["uf"] or "", max_chars=2)

        col_alt, col_exc = st.columns(2)
        with col_alt:
            btn_alterar = st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary")
        with col_exc:
            btn_excluir = st.form_submit_button("🗑️ Excluir Cadastro", use_container_width=True)

        if btn_alterar:
            if not nova_razao.strip() or not novo_resp.strip():
                st.error("Os campos 'Razão Social' e 'Responsável (PF)' são obrigatórios.")
            else:
                str_prox_contato = nova_data_prox.strftime("%d/%m/%Y") if manter_followup else ""
                conn = conectar_db()
                conn.execute("""
                    UPDATE clientes 
                    SET razao_social=?, nome_fantasia=?, responsavel_pf=?, 
                        telefone=?, email=?, cep=?, logradouro=?, numero=?, complemento=?, 
                        bairro=?, cidade=?, uf=?, etapa_funil=?, valor_estimado=?, 
                        servico_interesse=?, proximo_contato=?
                    WHERE id=?
                """, (
                    nova_razao.strip(), novo_fantasia.strip(), novo_resp.strip(),
                    novo_tel.strip(), novo_email.strip(), limpar_numeros(novo_cep), novo_log.strip(),
                    novo_num.strip(), novo_comp.strip(), novo_bairro.strip(), nova_cidade.strip(),
                    nova_uf.strip().upper(), nova_etapa, float(novo_valor), novo_servico,
                    str_prox_contato, int(cliente_sel["id"])
                ))
                conn.commit()
                conn.close()
                st.session_state.msg_sucesso_cadastro = f"✅ Cadastro da empresa '{nova_razao.strip()}' atualizado com sucesso!"
                st.rerun()

        if btn_excluir:
            if int(cliente_sel["total_atividades"]) > 0:
                st.error(
                    f"Bloqueado: Este cliente possui {cliente_sel['total_atividades']} atividade(s) registrada(s) e não pode ser excluído!")
            else:
                conn = conectar_db()
                conn.execute("DELETE FROM clientes WHERE id=?", (int(cliente_sel["id"]),))
                conn.commit()
                conn.close()
                st.session_state.msg_sucesso_cadastro = "🗑️ Cliente excluído com sucesso!"
                st.rerun()


def renderizar_edicao_atividade(df_atividades, sufixo_key):
    if df_atividades.empty:
        return

    with st.expander("✏️ Editar Registro de Atividade Existente", expanded=False):
        opcoes_ativ = {}
        for _, row in df_atividades.iterrows():
            empresa_lbl = f" - {row['Empresa']}" if "Empresa" in row else ""
            resumo = str(row.get("Detalhamento", row.get("Detalhamento do Atendimento", "")))[:45]
            label = f"ID #{row['ID']} | {row['Data']} ({row['Início']} às {row['Término']}){empresa_lbl} | {row['Modalidade']} - {resumo}..."
            opcoes_ativ[label] = row

        ativ_selecionada_lbl = st.selectbox(
            "Selecione o lançamento que deseja editar:",
            list(opcoes_ativ.keys()),
            key=f"sel_edit_ativ_{sufixo_key}"
        )
        ativ_row = opcoes_ativ[ativ_selecionada_lbl]
        ativ_id = int(ativ_row["ID"])

        c1, c2, c3, c4, c5 = st.columns([1.3, 1.1, 1.1, 1.3, 1.8])
        with c1:
            nova_data = st.date_input(
                "Data *",
                value=converter_str_data(ativ_row["Data"]) or date.today(),
                key=f"ed_data_{sufixo_key}_{ativ_id}"
            )
        with c2:
            novo_inicio = st.time_input(
                "Horário Inicial (De) *",
                value=converter_str_hora(ativ_row["Início"], time(10, 0)),
                step=timedelta(minutes=15),
                key=f"ed_ini_{sufixo_key}_{ativ_id}"
            )
        with c3:
            novo_fim = st.time_input(
                "Horário Final (Até) *",
                value=converter_str_hora(ativ_row["Término"], time(12, 0)),
                step=timedelta(minutes=15),
                key=f"ed_fim_{sufixo_key}_{ativ_id}"
            )

        dt_ini = datetime.combine(nova_data, novo_inicio)
        dt_fim = datetime.combine(nova_data, novo_fim)
        segundos = int((dt_fim - dt_ini).total_seconds())

        with c4:
            if segundos > 0:
                h = segundos // 3600
                m = (segundos % 3600) // 60
                novo_tempo_fmt = f"{h:02d}h {m:02d}m"
                st.metric("⏱️ Novo Tempo", novo_tempo_fmt)
            else:
                novo_tempo_fmt = "Inválido"
                st.metric("⏱️ Novo Tempo", "Inválido")

        lista_modalidades = ["WhatsApp", "Telefone", "Presencial / Visita Técnica", "E-mail", "Reunião Online",
                             "Outros"]
        mod_atual = ativ_row["Modalidade"] if ativ_row["Modalidade"] in lista_modalidades else "Outros"
        with c5:
            nova_mod = st.selectbox(
                "Modalidade *",
                lista_modalidades,
                index=lista_modalidades.index(mod_atual),
                key=f"ed_mod_{sufixo_key}_{ativ_id}"
            )

        texto_atual = ativ_row.get("Detalhamento", ativ_row.get("Detalhamento do Atendimento", ""))
        nova_desc = st.text_area(
            "Detalhamento da atividade *",
            value=texto_atual,
            height=100,
            key=f"ed_desc_{sufixo_key}_{ativ_id}"
        )

        if st.button("💾 Salvar Alterações da Atividade", key=f"btn_salvar_ativ_{sufixo_key}_{ativ_id}", type="primary",
                     use_container_width=True):
            if segundos <= 0:
                st.error("O Horário Final ('Até') deve ser maior que o Horário Inicial ('De').")
            elif not nova_desc.strip():
                st.error("A descrição da atividade não pode ficar em branco.")
            else:
                str_ini = novo_inicio.strftime("%H:%M")
                str_fim = novo_fim.strftime("%H:%M")
                periodo = f"{str_ini} às {str_fim}"

                conn = conectar_db()
                conn.execute("""
                    UPDATE atividades
                    SET data=?, horario=?, hora_inicio=?, hora_fim=?, tempo_total=?, modalidade=?, descricao=?
                    WHERE id=?
                """, (
                    nova_data.strftime("%d/%m/%Y"),
                    periodo,
                    str_ini,
                    str_fim,
                    novo_tempo_fmt,
                    nova_mod,
                    nova_desc.strip(),
                    ativ_id
                ))
                conn.commit()
                conn.close()
                st.session_state.msg_sucesso_atividade = f"✅ Registro de atividade #{ativ_id} atualizado com sucesso!"
                st.rerun()