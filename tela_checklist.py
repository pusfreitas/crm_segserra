import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, time, timedelta, datetime
from database import conectar_db, ITENS_CHECKLIST_SST

OPCOES_RESPOSTA = ["Sim", "Não", "Não aplicável"]

GRUPOS_CHECKLIST_SST = [
    ("1", "PGR e Inventário de Riscos", ["1.1", "1.2", "1.3"]),
    ("2", "CIPA / Representação", ["2.1"]),
    ("3", "EPIs e Controle de Entrega", ["3.1", "3.2", "3.3"]),
    ("4", "PCMSO e Exames Ocupacionais", ["4.1", "4.2", "4.3"]),
    ("5", "Avaliações, Riscos e FISPQ/FDS", ["5.1", "5.2", "5.3", "5.4"]),
    ("6", "Instalações Elétricas", ["6.1", "6.2", "6.3", "6.4", "6.5", "6.6"]),
    ("7", "Empilhadeiras e Movimentação", ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7"]),
    ("8", "Máquinas e Equipamentos (NR-12)", ["8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "8.7", "8.8", "8.9", "8.10", "8.11"]),
    ("9", "Vasos de Pressão e Compressores", ["9.1", "9.2"]),
    ("10", "LTIP (Insalubridade e Periculosidade)", ["10.1"]),
    ("11", "Inflamáveis e Combustíveis", ["11.1", "11.2", "11.3", "11.4", "11.5", "11.6"]),
]


def _resetar_selecao_tabela_checklist():
    st.session_state.tabela_checklist_nonce = int(st.session_state.get("tabela_checklist_nonce", 0)) + 1
    st.session_state.checklist_selecionado_id = None


def _focar_primeiro_campo_checklist():
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const anchor = doc.getElementById("ancora_novo_checklist");
            if (anchor) {
                anchor.scrollIntoView({ behavior: "smooth", block: "start" });
            }
            setTimeout(() => {
                const container = anchor ? anchor.parentElement : doc;
                const inputs = container.querySelectorAll('div[data-baseweb="select"] input, input, textarea');
                for (const el of inputs) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && !el.disabled) {
                        el.focus();
                        break;
                    }
                }
            }, 120);
        })();
        </script>
        """,
        height=0,
    )


def _validar_intervalo_horario(hora_de, hora_ate):
    """Garante que a hora final seja estritamente maior que a hora inicial."""
    if not isinstance(hora_de, time) or not isinstance(hora_ate, time):
        return False, "Informe horários válidos para 'De' e 'Até'."
    dt_ini = datetime.combine(date.today(), hora_de)
    dt_fim = datetime.combine(date.today(), hora_ate)
    if dt_fim <= dt_ini:
        return False, "O horário final ('Até') não pode ser menor ou igual ao horário inicial ('De')."
    return True, ""


def _renderizar_itens_verificacao(mapa_perguntas):
    st.markdown("#### Itens de Verificação em Campo")
    st.caption(
        "Marque **Sim**, **Não** ou **Não aplicável** para cada item. "
        "Clique em **Observações do grupo** abaixo de cada bloco apenas quando quiser anotar algo."
    )

    respostas_dict = {}
    obs_grupos_dict = {}
    codigos_mapeados = set()

    for grp_cod, grp_titulo, lista_cods in GRUPOS_CHECKLIST_SST:
        st.markdown(f"**Grupo {grp_cod} — {grp_titulo}**")
        for codigo in lista_cods:
            if codigo not in mapa_perguntas:
                continue
            codigos_mapeados.add(codigo)
            pergunta = mapa_perguntas[codigo]
            col_item, col_resp = st.columns([3.4, 1.6])
            with col_item:
                st.markdown(f"**{codigo}** — {pergunta}")
            with col_resp:
                escolha = st.radio(
                    f"Resposta {codigo}",
                    OPCOES_RESPOSTA,
                    horizontal=True,
                    key=f"chk_{codigo}",
                    label_visibility="collapsed"
                )
                respostas_dict[codigo] = escolha

        with st.expander(f"📝 Observações do Grupo {grp_cod} ({lista_cods[0]} a {lista_cods[-1]})", expanded=False):
            obs_grp_val = st.text_area(
                f"Observações — Grupo {grp_cod}",
                key=f"obs_grp_{grp_cod}",
                height=75,
                placeholder="Escreva aqui observações específicas deste grupo (opcional)..."
            )
            obs_grupos_dict[grp_cod] = obs_grp_val.strip()

    itens_restantes = [(cod, perg) for cod, perg in ITENS_CHECKLIST_SST if cod not in codigos_mapeados]
    if itens_restantes:
        st.markdown("**Outros Itens**")
        for codigo, pergunta in itens_restantes:
            col_item, col_resp = st.columns([3.4, 1.6])
            with col_item:
                st.markdown(f"**{codigo}** — {pergunta}")
            with col_resp:
                escolha = st.radio(
                    f"Resposta {codigo}",
                    OPCOES_RESPOSTA,
                    horizontal=True,
                    key=f"chk_{codigo}",
                    label_visibility="collapsed"
                )
                respostas_dict[codigo] = escolha

    return respostas_dict, obs_grupos_dict


def _renderizar_detalhes_checklist_selecionado(row_h, mapa_perguntas):
    st.divider()
    with st.container(border=True):
        col_t, col_fechar = st.columns([3.5, 1.0])
        with col_t:
            horario_txt = f" ({row_h['De'] or ''} às {row_h['Até'] or ''})" if (row_h.get("De") or row_h.get("Até")) else ""
            st.subheader(f"📄 Checklist #{row_h['ID']} — {row_h['Empresa']} | {row_h['Data']}{horario_txt}")
        with col_fechar:
            st.write("")
            if st.button("Fechar", key="btn_fechar_detalhe_chk", use_container_width=True):
                _resetar_selecao_tabela_checklist()
                st.rerun()

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Responsável Técnico", row_h.get("Responsável Técnico") or "—")
        with m2:
            st.metric("✅ Sim", int(row_h.get("Sim") or 0))
        with m3:
            st.metric("⚠️ Não (Pendências)", int(row_h.get("Não (Pendências)") or 0))
        with m4:
            st.metric("➖ N/A", int(row_h.get("N/A") or 0))

        if (row_h.get("Acompanhantes") or "").strip():
            st.markdown(f"**Acompanhantes na visita:** {row_h['Acompanhantes']}")

        try:
            dados_resp = json.loads(row_h.get("respostas_json") or "{}")
        except Exception:
            dados_resp = {}

        try:
            dados_obs_grp = json.loads(row_h.get("obs_grupos_json") or "{}")
        except Exception:
            dados_obs_grp = {}

        pendencias = [
            f"• **{cod}** — {mapa_perguntas.get(cod, '')}"
            for cod, val in dados_resp.items() if val == "Não"
        ]
        if pendencias:
            st.warning("**Itens assinalados como 'Não' (Pendências):**\n\n" + "\n".join(pendencias))
        else:
            st.success("Nenhum item marcado como 'Não' neste checklist.")

        obs_preenchidas = [
            f"• **Grupo {grp_cod}:** {txt}"
            for grp_cod, txt in dados_obs_grp.items() if str(txt or "").strip()
        ]
        if obs_preenchidas:
            st.info("**Observações registradas por grupo:**\n\n" + "\n".join(obs_preenchidas))

        if (row_h.get("Observações") or "").strip():
            st.markdown(f"**Observações Gerais:**\n\n{row_h['Observações']}")


def renderizar_tela_checklist():
    st.title("✅ Checklist de Visita Técnica (SST)")

    if "msg_sucesso_checklist" in st.session_state:
        st.success(st.session_state.msg_sucesso_checklist)
        st.toast(st.session_state.msg_sucesso_checklist)
        del st.session_state.msg_sucesso_checklist

    if "exibir_form_novo_checklist" not in st.session_state:
        st.session_state.exibir_form_novo_checklist = False

    if "exibir_itens_verificacao" not in st.session_state:
        st.session_state.exibir_itens_verificacao = False

    if "checklist_selecionado_id" not in st.session_state:
        st.session_state.checklist_selecionado_id = None

    if "tabela_checklist_nonce" not in st.session_state:
        st.session_state.tabela_checklist_nonce = 0

    conn = conectar_db()
    df_clientes = pd.read_sql_query("""
        SELECT id, cnpj, razao_social, cidade, uf
        FROM clientes
        ORDER BY razao_social
    """, conn)

    df_hist = pd.read_sql_query("""
        SELECT ch.id as ID, ch.data_visita as 'Data',
               ch.hora_inicio as 'De', ch.hora_fim as 'Até',
               c.razao_social as 'Empresa',
               ch.responsavel_tecnico as 'Responsável Técnico',
               ch.pessoas_acompanhamento as 'Acompanhantes',
               ch.qtd_sim as 'Sim', ch.qtd_nao as 'Não (Pendências)', ch.qtd_na as 'N/A',
               ch.respostas_json, ch.obs_grupos_json, ch.observacoes_gerais as 'Observações'
        FROM checklists_visita ch
        JOIN clientes c ON ch.cliente_id = c.id
        ORDER BY ch.id DESC
    """, conn)
    conn.close()

    mapa_perguntas = {cod: perg for cod, perg in ITENS_CHECKLIST_SST}

    with st.container(border=True):
        col_tit, col_btn_novo = st.columns([3.2, 1.3])
        with col_tit:
            st.subheader("📋 Checklists Emitidos")
        with col_btn_novo:
            st.write("")
            if not st.session_state.exibir_form_novo_checklist:
                if st.button("➕ Novo Checklist", type="primary", use_container_width=True, key="btn_abrir_novo_chk"):
                    _resetar_selecao_tabela_checklist()
                    st.session_state.exibir_form_novo_checklist = True
                    st.session_state.exibir_itens_verificacao = False
                    st.session_state.focar_novo_checklist = True
                    st.rerun()
            else:
                if st.button("✖️ Ocultar Formulário", use_container_width=True, key="btn_fechar_novo_chk"):
                    st.session_state.exibir_form_novo_checklist = False
                    st.session_state.focar_novo_checklist = False
                    st.rerun()

        if df_hist.empty:
            st.info("Nenhum checklist de visita técnica emitido até o momento. Clique em 'Novo Checklist' para iniciar.")
        else:
            f1, f2, f3 = st.columns([2.0, 1.6, 1.3])
            with f1:
                empresas_op = ["Todas"] + sorted([
                    e for e in df_hist["Empresa"].dropna().astype(str).unique() if e
                ])
                emp_filtro = st.selectbox("Filtrar por Empresa", empresas_op, key="filtro_chk_empresa")
            with f2:
                resps_op = ["Todos"] + sorted([
                    r for r in df_hist["Responsável Técnico"].dropna().astype(str).unique() if r
                ])
                resp_filtro = st.selectbox("Filtrar por Responsável Técnico", resps_op, key="filtro_chk_resp")
            with f3:
                pend_filtro = st.selectbox(
                    "Pendências ('Não')",
                    ["Todos", "Com Pendências (> 0)", "Sem Pendências (0)"],
                    key="filtro_chk_pend"
                )

            df_view = df_hist.copy()
            if emp_filtro != "Todas":
                df_view = df_view[df_view["Empresa"] == emp_filtro]
            if resp_filtro != "Todos":
                df_view = df_view[df_view["Responsável Técnico"] == resp_filtro]
            if pend_filtro == "Com Pendências (> 0)":
                df_view = df_view[df_view["Não (Pendências)"].fillna(0) > 0]
            elif pend_filtro == "Sem Pendências (0)":
                df_view = df_view[df_view["Não (Pendências)"].fillna(0) == 0]

            if df_view.empty:
                st.info("Nenhum checklist encontrado com os filtros selecionados.")
            else:
                st.caption("Clique em uma linha da tabela para abrir e visualizar o checklist emitido.")
                df_tab_chk = df_view[[
                    "ID", "Data", "De", "Até", "Empresa", "Responsável Técnico",
                    "Acompanhantes", "Sim", "Não (Pendências)", "N/A", "Observações"
                ]].reset_index(drop=True)

                nonce_chk = int(st.session_state.get("tabela_checklist_nonce", 0))
                evento_chk = st.dataframe(
                    df_tab_chk,
                    use_container_width=True,
                    hide_index=True,
                    height=380,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"tabela_checklists_emitidos_{nonce_chk}"
                )

                linhas_chk = evento_chk.selection.rows if (evento_chk and evento_chk.selection) else []
                if linhas_chk and len(df_tab_chk) > 0:
                    idx_chk = int(linhas_chk[0])
                    if 0 <= idx_chk < len(df_tab_chk):
                        id_chk_tab = int(df_tab_chk.iloc[idx_chk]["ID"])
                        if st.session_state.get("checklist_selecionado_id") != id_chk_tab:
                            st.session_state.checklist_selecionado_id = id_chk_tab
                            st.session_state.exibir_form_novo_checklist = False

    if st.session_state.get("checklist_selecionado_id") and not df_hist.empty:
        corresp = df_hist[df_hist["ID"] == int(st.session_state.checklist_selecionado_id)]
        if not corresp.empty:
            _renderizar_detalhes_checklist_selecionado(dict(corresp.iloc[0]), mapa_perguntas)

    if not st.session_state.exibir_form_novo_checklist:
        return

    if df_clientes.empty:
        st.warning("Cadastre pelo menos uma empresa na aba de Clientes antes de preencher o checklist.")
        return

    opcoes_cli = {
        f"{r['razao_social']} | CNPJ: {r['cnpj']} ({r['cidade'] or '-'}/{r['uf'] or '-'})": r
        for _, r in df_clientes.iterrows()
    }
    resp_padrao = st.session_state.get("nome_usuario") or st.session_state.get("usuario_atual") or "Administrador"

    st.divider()
    with st.container(border=True):
        st.markdown('<div id="ancora_novo_checklist"></div>', unsafe_allow_html=True)
        st.subheader("Novo Checklist de Visita Técnica")

        c1, c2 = st.columns([2.5, 1.2])
        with c1:
            cli_lbl = st.selectbox("Empresa / Cliente *", list(opcoes_cli.keys()), key="chk_form_cli")
        with c2:
            dt_visita = st.date_input("Data da Visita *", value=date.today(), key="chk_form_data")

        h1, h2, h3 = st.columns([1.0, 1.0, 2.2])
        with h1:
            hora_de = st.time_input("Horário - De *", value=time(9, 0), step=timedelta(minutes=15), key="chk_form_hora_de")
        with h2:
            hora_ate = st.time_input("Horário - Até *", value=time(10, 30), step=timedelta(minutes=15), key="chk_form_hora_ate")
        with h3:
            responsavel_tec = st.text_input("Responsável Técnico *", value=resp_padrao, key="chk_form_resp")

        horario_ok, msg_horario = _validar_intervalo_horario(hora_de, hora_ate)
        if not horario_ok:
            st.error(f"⛔ {msg_horario}")

        pessoas_acompanhamento = st.text_input(
            "Pessoas com quem conversamos / acompanharam a visita",
            placeholder="Ex: João Silva (Gerente Industrial), Maria Souza (RH / Segurança)",
            key="chk_form_acomp"
        )

        st.divider()
        col_add_it, col_hide_it, _ = st.columns([1.7, 1.5, 2.0])
        with col_add_it:
            if not st.session_state.exibir_itens_verificacao:
                if st.button("➕ Mostrar Itens de Verificação", type="primary", use_container_width=True, key="btn_add_itens_chk"):
                    st.session_state.exibir_itens_verificacao = True
                    st.rerun()
        with col_hide_it:
            if st.session_state.exibir_itens_verificacao:
                if st.button("➖ Ocultar Itens de Verificação", use_container_width=True, key="btn_hide_itens_chk"):
                    st.session_state.exibir_itens_verificacao = False
                    st.rerun()

        respostas_dict = {}
        obs_grupos_dict = {}
        if st.session_state.exibir_itens_verificacao:
            respostas_dict, obs_grupos_dict = _renderizar_itens_verificacao(mapa_perguntas)
        else:
            st.info("Os itens de verificação em campo estão ocultos. Clique em **+ Mostrar Itens de Verificação** para preenchê-los.")

        st.divider()
        obs_gerais = st.text_area(
            "Observações Gerais / Plano de Ação / Recomendações",
            height=110,
            placeholder="Registre observações técnicas gerais, prioridades ou orientações para o cliente...",
            key="chk_form_obs_gerais"
        )

        if st.button("💾 Salvar Checklist da Visita Técnica", type="primary", use_container_width=True, key="btn_salvar_chk_visita"):
            valido_hr, erro_hr = _validar_intervalo_horario(hora_de, hora_ate)
            if not valido_hr:
                st.error(erro_hr)
            elif not responsavel_tec.strip():
                st.error("Informe o nome do Responsável Técnico.")
            else:
                qtd_sim = sum(1 for v in respostas_dict.values() if v == "Sim")
                qtd_nao = sum(1 for v in respostas_dict.values() if v == "Não")
                qtd_na = sum(1 for v in respostas_dict.values() if v == "Não aplicável")

                cli_row = opcoes_cli[cli_lbl]
                conn = conectar_db()
                conn.execute("""
                    INSERT INTO checklists_visita (
                        cliente_id, data_visita, hora_inicio, hora_fim,
                        responsavel_tecnico, pessoas_acompanhamento,
                        respostas_json, obs_grupos_json, qtd_sim, qtd_nao,
                        qtd_na, observacoes_gerais
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(cli_row["id"]),
                    dt_visita.strftime("%d/%m/%Y"),
                    hora_de.strftime("%H:%M"),
                    hora_ate.strftime("%H:%M"),
                    responsavel_tec.strip(),
                    pessoas_acompanhamento.strip(),
                    json.dumps(respostas_dict, ensure_ascii=False),
                    json.dumps(obs_grupos_dict, ensure_ascii=False),
                    qtd_sim,
                    qtd_nao,
                    qtd_na,
                    obs_gerais.strip()
                ))
                conn.commit()
                conn.close()

                st.session_state.exibir_form_novo_checklist = False
                st.session_state.exibir_itens_verificacao = False
                _resetar_selecao_tabela_checklist()
                st.session_state.msg_sucesso_checklist = (
                    f"✅ Checklist salvo para '{cli_row['razao_social']}'! "
                    f"(Sim: {qtd_sim} | Não: {qtd_nao} | N/A: {qtd_na})"
                )
                st.rerun()

    if st.session_state.get("focar_novo_checklist"):
        st.session_state.focar_novo_checklist = False
        _focar_primeiro_campo_checklist()