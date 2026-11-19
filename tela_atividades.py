import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, time, timedelta, date
from database import conectar_db, CATEGORIAS_CLIENTE
from utils import (
    limpar_numeros,
    formatar_cep,
    consultar_cep_api,
    validar_cnpj_algoritmo,
    somar_tempos_formatados,
)
from componentes import renderizar_edicao_atividade


def _renderizar_bloco_novo_cliente_atividade():
    with st.expander("➕ Incluir Novo Cliente", expanded=False):
        st.caption("Cadastre um novo cliente rapidamente para já lançar a atividade em seguida.")

        cep_rapido = st.text_input(
            "CEP (opcional — preenche endereço ao informar 8 dígitos)",
            placeholder="00000-000",
            key="ativ_nc_cep",
        )
        cep_fmt = formatar_cep(cep_rapido)
        cep_limpo = limpar_numeros(cep_fmt)

        log_ini, bairro_ini, cid_ini, uf_ini = "", "", "", "RS"
        if len(cep_limpo) == 8:
            dados_cep, erro_cep = consultar_cep_api(cep_limpo)
            if dados_cep:
                log_ini = dados_cep.get("logradouro") or ""
                bairro_ini = dados_cep.get("bairro") or ""
                cid_ini = dados_cep.get("cidade") or ""
                uf_ini = dados_cep.get("uf") or "RS"
            elif erro_cep:
                st.caption(f"ℹ️ {erro_cep}")

        with st.form("form_novo_cliente_em_atividade", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.4, 2.2, 1.3])
            with c1:
                nc_cnpj = st.text_input("CNPJ *", placeholder="00.000.000/0001-00")
            with c2:
                nc_razao = st.text_input("Razão Social *")
            with c3:
                nc_cat = st.selectbox("Categoria *", CATEGORIAS_CLIENTE, index=0)

            r1, r2, r3 = st.columns([1.8, 1.4, 1.6])
            with r1:
                nc_resp = st.text_input("Responsável *")
            with r2:
                nc_tel = st.text_input("Telefone / WhatsApp")
            with r3:
                nc_email = st.text_input("E-mail")

            e1, e2, e3, e4 = st.columns([2.5, 1.0, 1.8, 0.9])
            with e1:
                nc_log = st.text_input("Logradouro", value=log_ini)
            with e2:
                nc_num = st.text_input("Número")
            with e3:
                nc_cid = st.text_input("Cidade", value=cid_ini)
            with e4:
                nc_uf = st.text_input("UF", value=uf_ini, max_chars=2)

            nc_bairro = st.text_input("Bairro", value=bairro_ini)

            if st.form_submit_button("💾 Cadastrar e Selecionar Cliente", type="primary", use_container_width=True):
                cnpj_limpo = limpar_numeros(nc_cnpj)
                if not validar_cnpj_algoritmo(cnpj_limpo):
                    st.error("CNPJ inválido. Verifique os 14 dígitos.")
                elif not nc_razao.strip() or not nc_resp.strip():
                    st.error("Preencha 'Razão Social' e 'Responsável'.")
                else:
                    try:
                        conn = conectar_db()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO clientes (
                                cnpj, razao_social, nome_fantasia, responsavel_pf,
                                telefone, email, cep, logradouro, numero, bairro, cidade, uf, categoria
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cnpj_limpo,
                            nc_razao.strip(),
                            nc_razao.strip(),
                            nc_resp.strip(),
                            nc_tel.strip(),
                            nc_email.strip(),
                            cep_fmt,
                            nc_log.strip(),
                            nc_num.strip(),
                            nc_bairro.strip(),
                            nc_cid.strip(),
                            nc_uf.strip().upper(),
                            nc_cat,
                        ))
                        novo_id = int(cur.lastrowid)
                        conn.commit()
                        conn.close()
                        st.session_state.cliente_pre_selecionado_id = novo_id
                        st.session_state.msg_sucesso_atividade = f"✅ Cliente '{nc_razao.strip()}' cadastrado e selecionado!"
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Já existe um cliente cadastrado com este CNPJ.")


def renderizar_tela_atividades():
    st.title("📝 Lançar Atividades e Atendimentos")

    if "msg_sucesso_atividade" in st.session_state:
        st.success(st.session_state.msg_sucesso_atividade)
        st.toast(st.session_state.msg_sucesso_atividade)
        del st.session_state.msg_sucesso_atividade

    _renderizar_bloco_novo_cliente_atividade()

    conn = conectar_db()
    df_clientes = pd.read_sql_query("""
        SELECT id, cnpj, razao_social, responsavel_pf
        FROM clientes
        ORDER BY razao_social ASC
    """, conn)
    conn.close()

    if df_clientes.empty:
        st.warning("Cadastre pelo menos uma empresa antes de registrar atividades.")
        return

    opcoes_cli = {
        f"{r['razao_social']} | CNPJ: {r['cnpj']}": dict(r)
        for _, r in df_clientes.iterrows()
    }
    chaves_cli = list(opcoes_cli.keys())

    idx_padrao = 0
    pre_id = st.session_state.get("cliente_pre_selecionado_id")
    if pre_id is not None:
        for i_pos, k_txt in enumerate(chaves_cli):
            if int(opcoes_cli[k_txt]["id"]) == int(pre_id):
                idx_padrao = i_pos
                break
        st.session_state.cliente_pre_selecionado_id = None

    if "limpar_desc_ativ" not in st.session_state:
        st.session_state.limpar_desc_ativ = False
    if st.session_state.limpar_desc_ativ:
        st.session_state.ativ_descricao = ""
        st.session_state.limpar_desc_ativ = False

    atendente_atual = (
        st.session_state.get("nome_usuario")
        or st.session_state.get("usuario_atual")
        or "Administrador"
    )

    st.subheader("Registrar Novo Atendimento")
    with st.container(border=True):
        cli_lbl = st.selectbox("Empresa / Cliente *", chaves_cli, index=idx_padrao, key="ativ_sel_cliente")
        cli_sel = opcoes_cli[cli_lbl]

        c1, c2, c3, c4, c5 = st.columns([1.3, 1.1, 1.1, 1.3, 1.8])
        with c1:
            data_ativ = st.date_input("Data *", value=date.today(), key="ativ_data")
        with c2:
            hora_inicio = st.time_input(
                "Horário Inicial (De) *",
                value=time(9, 0),
                step=timedelta(minutes=15),
                key="ativ_hora_ini",
            )
        with c3:
            hora_fim = st.time_input(
                "Horário Final (Até) *",
                value=time(10, 0),
                step=timedelta(minutes=15),
                key="ativ_hora_fim",
            )

        dt_ini = datetime.combine(data_ativ, hora_inicio)
        dt_fim = datetime.combine(data_ativ, hora_fim)
        segundos = int((dt_fim - dt_ini).total_seconds())

        with c4:
            if segundos > 0:
                h = segundos // 3600
                m = (segundos % 3600) // 60
                tempo_total_fmt = f"{h:02d}h {m:02d}m"
                st.metric("⏱️ Tempo Total", tempo_total_fmt)
            else:
                tempo_total_fmt = "Inválido"
                st.metric("⏱️ Tempo Total", "Inválido")

        lista_modalidades = [
            "WhatsApp",
            "Telefone",
            "Presencial / Visita Técnica",
            "E-mail",
            "Reunião Online",
            "Outros",
        ]
        with c5:
            modalidade = st.selectbox("Modalidade *", lista_modalidades, key="ativ_modalidade")

        descricao = st.text_area(
            "Detalhamento do Atendimento / Atividade *",
            height=110,
            placeholder="Descreva o que foi tratado, pendências levantadas ou próximos passos...",
            key="ativ_descricao",
        )

        if st.button("💾 Salvar Registro de Atividade", type="primary", use_container_width=True, key="btn_salvar_ativ"):
            if segundos <= 0:
                st.error("O Horário Final ('Até') deve ser maior que o Horário Inicial ('De').")
            elif not descricao.strip():
                st.error("A descrição da atividade não pode ficar em branco.")
            else:
                str_ini = hora_inicio.strftime("%H:%M")
                str_fim = hora_fim.strftime("%H:%M")
                periodo_str = f"{str_ini} às {str_fim}"

                conn = conectar_db()
                conn.execute("""
                    INSERT INTO atividades (
                        cliente_id, data, horario, hora_inicio, hora_fim, 
                        tempo_total, modalidade, descricao, atendente
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(cli_sel["id"]),
                    data_ativ.strftime("%d/%m/%Y"),
                    periodo_str,
                    str_ini,
                    str_fim,
                    tempo_total_fmt,
                    modalidade,
                    descricao.strip(),
                    atendente_atual,
                ))
                conn.commit()
                conn.close()

                st.session_state.limpar_desc_ativ = True
                st.session_state.msg_sucesso_atividade = (
                    f"✅ Atividade registrada para '{cli_sel['razao_social']}' ({tempo_total_fmt})!"
                )
                st.rerun()

    st.divider()
    st.subheader("📋 Histórico de Atividades Registradas")

    conn = conectar_db()
    df_hist = pd.read_sql_query("""
        SELECT a.id as ID,
               a.data as 'Data',
               a.hora_inicio as 'Início',
               a.hora_fim as 'Término',
               a.tempo_total as 'Duração',
               c.razao_social as 'Empresa',
               a.modalidade as 'Modalidade',
               a.descricao as 'Detalhamento',
               a.atendente as 'Atendente'
        FROM atividades a
        JOIN clientes c ON a.cliente_id = c.id
        ORDER BY a.id DESC
    """, conn)
    conn.close()

    if df_hist.empty:
        st.info("Nenhuma atividade registrada até o momento.")
    else:
        total_horas = somar_tempos_formatados(df_hist["Duração"])
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Total de Registros", len(df_hist))
        with m2:
            st.metric("⏱️ Tempo Acumulado", total_horas)

        st.dataframe(df_hist, use_container_width=True, hide_index=True)
        renderizar_edicao_atividade(df_hist, sufixo_key="tela_ativ")