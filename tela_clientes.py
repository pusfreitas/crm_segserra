import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
from database import conectar_db, ETAPAS_FUNIL, OPCOES_SERVICOS
from utils import (
    limpar_numeros, validar_cnpj_algoritmo, consultar_cnpj_api,
    somar_tempos_formatados, converter_str_data
)
from componentes import modal_editar_cliente, renderizar_edicao_atividade, ir_para_lancamento_cliente

CAMPOS_TEXTO_FORM = [
    "cad_cnpj", "cad_razao", "cad_fantasia", "cad_resp",
    "cad_tel", "cad_email", "cad_cep", "cad_logradouro", "cad_numero",
    "cad_complemento", "cad_bairro", "cad_cidade", "cad_uf"
]


def inicializar_estado_clientes():
    if "limpar_campos" not in st.session_state:
        st.session_state.limpar_campos = False
    for campo in CAMPOS_TEXTO_FORM:
        if campo not in st.session_state:
            st.session_state[campo] = ""
    if "cad_etapa" not in st.session_state:
        st.session_state.cad_etapa = ETAPAS_FUNIL[0]
    if "cad_servico" not in st.session_state:
        st.session_state.cad_servico = OPCOES_SERVICOS[0]
    if "cad_valor" not in st.session_state:
        st.session_state.cad_valor = 0.0
    if "cad_prox_contato" not in st.session_state:
        st.session_state.cad_prox_contato = date.today() + timedelta(days=3)


def preencher_dados_cnpj():
    cnpj_atual = st.session_state.cad_cnpj
    cnpj_limpo = limpar_numeros(cnpj_atual)

    if len(cnpj_limpo) != 14:
        st.session_state.feedback_cnpj = ("warning", "O CNPJ deve conter exatamente 14 dígitos numéricos.")
        return
    if not validar_cnpj_algoritmo(cnpj_limpo):
        st.session_state.feedback_cnpj = ("error", "CNPJ matematicamente inválido! Verifique os números digitados.")
        return

    dados, erro = consultar_cnpj_api(cnpj_limpo)
    if dados:
        st.session_state.cad_razao = dados.get("razao_social", "") or ""
        st.session_state.cad_fantasia = dados.get("nome_fantasia", "") or ""
        st.session_state.cad_tel = dados.get("ddd_telefone_1", "") or ""
        st.session_state.cad_email = dados.get("email", "") or ""
        st.session_state.cad_cep = dados.get("cep", "") or ""

        tipo_log = dados.get("descricao_tipo_de_logradouro", "") or ""
        nome_log = dados.get("logradouro", "") or ""
        st.session_state.cad_logradouro = f"{tipo_log} {nome_log}".strip()

        st.session_state.cad_numero = dados.get("numero", "") or ""
        st.session_state.cad_complemento = dados.get("complemento", "") or ""
        st.session_state.cad_bairro = dados.get("bairro", "") or ""
        st.session_state.cad_cidade = dados.get("municipio", "") or ""
        st.session_state.cad_uf = dados.get("uf", "") or ""
        st.session_state.feedback_cnpj = ("success",
                                          "Dados carregados automaticamente via CNPJ! Complete o cadastro abaixo.")
    else:
        st.session_state.feedback_cnpj = ("warning", erro)


def acao_enter_cnpj():
    cnpj_limpo = limpar_numeros(st.session_state.cad_cnpj)
    if len(cnpj_limpo) == 14:
        preencher_dados_cnpj()
    elif len(cnpj_limpo) > 0:
        st.session_state.feedback_cnpj = ("warning",
                                          f"Você digitou {len(cnpj_limpo)} números. O CNPJ precisa ter 14 dígitos para buscar ao apertar Enter.")


def renderizar_tela_clientes():
    inicializar_estado_clientes()

    if st.session_state.limpar_campos:
        for campo in CAMPOS_TEXTO_FORM:
            st.session_state[campo] = ""
        st.session_state.cad_etapa = ETAPAS_FUNIL[0]
        st.session_state.cad_servico = OPCOES_SERVICOS[0]
        st.session_state.cad_valor = 0.0
        st.session_state.cad_prox_contato = date.today() + timedelta(days=3)
        st.session_state.limpar_campos = False

    st.title("👥 Gestão de Clientes")

    if "msg_sucesso_cadastro" in st.session_state:
        st.success(st.session_state.msg_sucesso_cadastro)
        st.toast(st.session_state.msg_sucesso_cadastro)
        del st.session_state.msg_sucesso_cadastro

    if "msg_sucesso_atividade" in st.session_state:
        st.success(st.session_state.msg_sucesso_atividade)
        st.toast(st.session_state.msg_sucesso_atividade)
        del st.session_state.msg_sucesso_atividade

    aba_lista, aba_novo, aba_gerenciar = st.tabs([
        "🔍 Clientes Cadastrados (Pesquisa)",
        "➕ Novo Cadastro",
        "✏️ Alterar / Excluir Clientes"
    ])

    with aba_lista:
        st.subheader("Pesquisar Empresas Cadastradas")
        c_pesq, c_filtro_etapa = st.columns([3, 1.5])
        with c_pesq:
            termo_pesquisa = st.text_input(
                "Digite o Nome (Razão Social / Nome Fantasia / Responsável) ou CNPJ da empresa e pressione Enter:",
                placeholder="Ex: Nome da empresa ou 00.000.000/0001-00"
            )
        with c_filtro_etapa:
            filtro_funil = st.selectbox("Filtrar por Etapa do Funil:", ["Todas as Etapas"] + ETAPAS_FUNIL)

        conn = conectar_db()
        df_todos = pd.read_sql_query("""
            SELECT c.id as ID, c.cnpj as CNPJ, c.razao_social as 'Razão Social', 
                   c.nome_fantasia as 'Nome Fantasia', c.responsavel_pf as 'Responsável (PF)', 
                   c.etapa_funil as 'Etapa do Funil', c.proximo_contato as 'Próx. Contato',
                   c.valor_estimado as 'Valor Proposta (R$)', c.servico_interesse as 'Interesse',
                   c.telefone as Telefone, c.email as 'E-mail', c.cidade as Cidade, c.uf as UF,
                   c.bairro as Bairro, c.logradouro as Logradouro, c.numero as 'Nº', c.cep as CEP,
                   COUNT(a.id) as 'Atividades'
            FROM clientes c
            LEFT JOIN atividades a ON c.id = a.cliente_id
            GROUP BY c.id
            ORDER BY c.id DESC
        """, conn)
        conn.close()

        if df_todos.empty:
            st.info(
                "Nenhum cliente cadastrado na base de dados até o momento. Utilize a aba '➕ Novo Cadastro' para começar.")
        else:
            df_exibicao = df_todos.copy()
            if filtro_funil != "Todas as Etapas":
                df_exibicao = df_exibicao[df_exibicao["Etapa do Funil"] == filtro_funil]

            if termo_pesquisa.strip():
                termo = termo_pesquisa.strip()
                termo_num = limpar_numeros(termo)
                condicao = (
                        df_exibicao["Razão Social"].str.contains(termo, case=False, na=False) |
                        df_exibicao["Nome Fantasia"].str.contains(termo, case=False, na=False) |
                        df_exibicao["Responsável (PF)"].str.contains(termo, case=False, na=False) |
                        df_exibicao["CNPJ"].str.contains(termo, case=False, na=False)
                )
                if termo_num:
                    condicao = condicao | df_exibicao["CNPJ"].str.contains(termo_num, case=False, na=False)
                df_exibicao = df_exibicao[condicao]

            df_exibicao = df_exibicao.reset_index(drop=True)

            if df_exibicao.empty:
                st.warning("⚠️ Nenhum cadastro foi encontrado para os filtros informados.")
            else:
                st.markdown(f"**Registros localizados:** `{len(df_exibicao)}`")
                st.caption(
                    "💡 **Dica:** Clique na linha da empresa na tabela abaixo para abrir imediatamente a janela de **Alteração Cadastral, Funil e Follow-up**.")
                evento_selecao = st.dataframe(
                    df_exibicao,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key="tabela_pesquisa_clientes"
                )

                linhas_selecionadas = evento_selecao.selection.rows
                if linhas_selecionadas:
                    idx_linha = linhas_selecionadas[0]
                    id_clicado = int(df_exibicao.iloc[idx_linha]["ID"])
                    modal_editar_cliente(id_clicado)

                st.divider()
                st.subheader("📋 Consultar e Editar Atividades do Cliente")
                opcoes_hist = {
                    f"{row['Razão Social']} | {row['Etapa do Funil']} ({row['Atividades']} ativ.)": row
                    for _, row in df_exibicao.iterrows()
                }

                col_sel, col_btn_edit, col_atalho = st.columns([2.6, 1.2, 1.2])
                with col_sel:
                    cliente_hist_label = st.selectbox("Selecione a empresa listada acima:", list(opcoes_hist.keys()))
                cliente_hist_row = opcoes_hist[cliente_hist_label]

                with col_btn_edit:
                    st.write("")
                    st.write("")
                    if st.button("✏️ Alterar Cadastro", use_container_width=True):
                        modal_editar_cliente(int(cliente_hist_row["ID"]))

                with col_atalho:
                    st.write("")
                    st.write("")
                    st.button(
                        "➕ Lançar Atividade",
                        on_click=ir_para_lancamento_cliente,
                        args=(cliente_hist_row["ID"],),
                        use_container_width=True,
                        type="primary"
                    )

                conn = conectar_db()
                df_ativ_cliente = pd.read_sql_query("""
                                    SELECT id as ID, data as Data, 
                                           CASE WHEN hora_inicio != '' THEN hora_inicio ELSE horario END as 'Início',
                                           hora_fim as 'Término',
                                           tempo_total as 'Tempo Gasto',
                                           atendente as 'Atendente',
                                           modalidade as Modalidade, 
                                           descricao as 'Detalhamento do Atendimento'
                                    FROM atividades
                                    WHERE cliente_id = ?
                                    ORDER BY id DESC
                                """, conn, params=(int(cliente_hist_row["ID"]),))
                conn.close()

                if df_ativ_cliente.empty:
                    st.info(f"Nenhuma atividade registrada para **{cliente_hist_row['Razão Social']}** até o momento.")
                else:
                    tempo_acumulado = somar_tempos_formatados(df_ativ_cliente["Tempo Gasto"])
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("🏢 Empresa", cliente_hist_row["Razão Social"])
                    m2.metric("📊 Etapa do Funil", cliente_hist_row["Etapa do Funil"])
                    m3.metric("📌 Atendimentos", len(df_ativ_cliente))
                    m4.metric("⏱️ Tempo Acumulado", tempo_acumulado)

                    st.dataframe(df_ativ_cliente, use_container_width=True, hide_index=True)
                    renderizar_edicao_atividade(df_ativ_cliente, sufixo_key="aba_cliente")

    with aba_novo:
        st.subheader("1. Pesquisa e Validação de CNPJ")
        col_cnpj, col_btn = st.columns([3, 1])
        with col_cnpj:
            st.text_input(
                "Digite o CNPJ da Empresa e pressione ENTER para pesquisar *",
                key="cad_cnpj",
                placeholder="00.000.000/0001-00",
                on_change=acao_enter_cnpj
            )
        with col_btn:
            st.write("")
            st.write("")
            st.button("🔍 Buscar Dados do CNPJ", on_click=preencher_dados_cnpj, use_container_width=True)

        if "feedback_cnpj" in st.session_state:
            tipo, msg = st.session_state.feedback_cnpj
            if tipo == "success":
                st.success(msg)
            elif tipo == "error":
                st.error(msg)
            else:
                st.warning(msg)
            del st.session_state.feedback_cnpj

        st.divider()
        st.subheader("2. Dados da Empresa, Funil e Endereço")
        with st.form("form_cadastro_cliente"):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Razão Social *", key="cad_razao")
                st.text_input("Nome Fantasia", key="cad_fantasia")
                st.text_input("Nome do Cliente / Responsável (Pessoa Física) *", key="cad_resp")
            with c2:
                st.text_input("Telefone / WhatsApp", key="cad_tel")
                st.text_input("E-mail", key="cad_email")

            st.markdown("##### 📊 Classificação Comercial (Funil de Vendas & Follow-up)")
            f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.8, 1.2])
            with f1:
                st.selectbox("Etapa Inicial no Funil", ETAPAS_FUNIL, key="cad_etapa")
            with f2:
                st.number_input("Valor Estimado (R$)", min_value=0.0, step=100.0, key="cad_valor")
            with f3:
                st.selectbox("Serviço de Interesse Principal", OPCOES_SERVICOS, key="cad_servico")
            with f4:
                st.date_input("Próximo Contato (Follow-up)", key="cad_prox_contato")

            st.markdown("##### 📍 Endereço (Separado para Relatórios)")
            e1, e2, e3, e4 = st.columns([1.2, 3, 1, 1.5])
            with e1:
                st.text_input("CEP", key="cad_cep")
            with e2:
                st.text_input("Logradouro (Rua / Av.)", key="cad_logradouro")
            with e3:
                st.text_input("Número", key="cad_numero")
            with e4:
                st.text_input("Complemento", key="cad_complemento")

            e5, e6, e7 = st.columns([2.5, 2.5, 1])
            with e5:
                st.text_input("Bairro", key="cad_bairro")
            with e6:
                st.text_input("Cidade", key="cad_cidade")
            with e7:
                st.text_input("UF", key="cad_uf", max_chars=2)

            salvar = st.form_submit_button("💾 Salvar Cadastro", use_container_width=True)

            if salvar:
                cnpj_limpo = limpar_numeros(st.session_state.cad_cnpj)
                razao_val = st.session_state.cad_razao.strip()
                resp_val = st.session_state.cad_resp.strip()

                if not validar_cnpj_algoritmo(cnpj_limpo):
                    st.error("Informe um CNPJ válido antes de salvar.")
                elif not razao_val or not resp_val:
                    st.error("Os campos 'Razão Social' e 'Nome do Responsável (PF)' são obrigatórios.")
                else:
                    try:
                        str_prox = st.session_state.cad_prox_contato.strftime(
                            "%d/%m/%Y") if st.session_state.cad_prox_contato else ""
                        conn = conectar_db()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO clientes (
                                cnpj, razao_social, nome_fantasia, responsavel_pf,
                                telefone, email, cep, logradouro, numero, complemento, 
                                bairro, cidade, uf, etapa_funil, valor_estimado, servico_interesse, proximo_contato
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cnpj_limpo,
                            razao_val,
                            st.session_state.cad_fantasia.strip(),
                            resp_val,
                            st.session_state.cad_tel.strip(),
                            st.session_state.cad_email.strip(),
                            limpar_numeros(st.session_state.cad_cep),
                            st.session_state.cad_logradouro.strip(),
                            st.session_state.cad_numero.strip(),
                            st.session_state.cad_complemento.strip(),
                            st.session_state.cad_bairro.strip(),
                            st.session_state.cad_cidade.strip(),
                            st.session_state.cad_uf.strip().upper(),
                            st.session_state.cad_etapa,
                            float(st.session_state.cad_valor or 0.0),
                            st.session_state.cad_servico,
                            str_prox
                        ))
                        conn.commit()
                        conn.close()

                        st.session_state.msg_sucesso_cadastro = f"✅ Empresa '{razao_val}' cadastrada com sucesso na etapa '{st.session_state.cad_etapa}'!"
                        st.session_state.limpar_campos = True
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este CNPJ já está cadastrado no sistema!")

        st.divider()
        st.subheader("📋 Empresas Cadastradas Recentemente")
        if df_todos.empty:
            st.info("Nenhuma empresa cadastrada ainda.")
        else:
            st.dataframe(df_todos, use_container_width=True, hide_index=True)

    with aba_gerenciar:
        conn = conectar_db()
        df_clientes = pd.read_sql_query("""
            SELECT c.*, COUNT(a.id) as total_atividades 
            FROM clientes c 
            LEFT JOIN atividades a ON c.id = a.cliente_id 
            GROUP BY c.id
            ORDER BY c.id DESC
        """, conn)
        conn.close()

        if df_clientes.empty:
            st.info("Nenhum cliente cadastrado até o momento.")
        else:
            opcoes = {f"{row['id']} - {row['razao_social']} | {row['etapa_funil']}": row for _, row in
                      df_clientes.iterrows()}
            selecionado_label = st.selectbox("Selecione um cliente para Alterar ou Excluir:", list(opcoes.keys()))
            cliente_sel = opcoes[selecionado_label]

            with st.form("form_editar_cliente"):
                st.markdown(
                    f"**Editando CNPJ:** `{cliente_sel['cnpj']}` | **Atividades registradas:** `{cliente_sel['total_atividades']}`")
                c1, c2 = st.columns(2)
                with c1:
                    nova_razao = st.text_input("Razão Social *", value=cliente_sel["razao_social"] or "")
                    novo_fantasia = st.text_input("Nome Fantasia", value=cliente_sel["nome_fantasia"] or "")
                    novo_resp = st.text_input("Responsável (PF) *", value=cliente_sel["responsavel_pf"] or "")
                with c2:
                    novo_tel = st.text_input("Telefone / WhatsApp", value=cliente_sel["telefone"] or "")
                    novo_email = st.text_input("E-mail", value=cliente_sel["email"] or "")

                st.markdown("##### 📊 Funil de Vendas & Follow-up")
                f1, f2, f3, f4 = st.columns([1.6, 1.1, 1.8, 1.2])
                etapa_atual_aba = cliente_sel["etapa_funil"] if cliente_sel["etapa_funil"] in ETAPAS_FUNIL else \
                ETAPAS_FUNIL[0]
                serv_atual_aba = cliente_sel["servico_interesse"] if cliente_sel[
                                                                         "servico_interesse"] in OPCOES_SERVICOS else \
                OPCOES_SERVICOS[0]
                dt_prox_aba = converter_str_data(cliente_sel["proximo_contato"]) or (date.today() + timedelta(days=3))
                tem_data_aba = bool(str(cliente_sel["proximo_contato"] or "").strip())

                with f1:
                    nova_etapa_aba = st.selectbox("Etapa do Funil", ETAPAS_FUNIL,
                                                  index=ETAPAS_FUNIL.index(etapa_atual_aba))
                with f2:
                    novo_valor_aba = st.number_input("Valor da Proposta (R$)", min_value=0.0, step=100.0,
                                                     value=float(cliente_sel["valor_estimado"] or 0.0))
                with f3:
                    novo_servico_aba = st.selectbox("Serviço de Interesse", OPCOES_SERVICOS,
                                                    index=OPCOES_SERVICOS.index(serv_atual_aba))
                with f4:
                    nova_data_prox_aba = st.date_input("Próximo Contato", value=dt_prox_aba)
                    manter_followup_aba = st.checkbox("Manter Follow-up ativo", value=tem_data_aba)

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
                    btn_alterar = st.form_submit_button("✏️ Salvar Alterações", use_container_width=True)
                with col_exc:
                    btn_excluir = st.form_submit_button("🗑️ Excluir Cadastro", use_container_width=True)

                if btn_alterar:
                    str_prox_aba = nova_data_prox_aba.strftime("%d/%m/%Y") if manter_followup_aba else ""
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
                        nova_uf.strip().upper(), nova_etapa_aba, float(novo_valor_aba), novo_servico_aba,
                        str_prox_aba, int(cliente_sel["id"])
                    ))
                    conn.commit()
                    conn.close()
                    st.session_state.msg_sucesso_cadastro = "✅ Cadastro atualizado com sucesso!"
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