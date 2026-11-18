import streamlit as st
import pandas as pd
from database import conectar_db, ETAPAS_FUNIL
from utils import formatar_moeda, avaliar_status_followup
from componentes import modal_editar_cliente, ir_para_lancamento_cliente, alterar_etapa_funil_rapido


def renderizar_tela_funil():
    st.title("📊 Funil de Vendas & Controle de Follow-up")

    conn = conectar_db()
    df_funil = pd.read_sql_query("""
        SELECT c.*, COUNT(a.id) as total_atividades, MAX(a.data) as ultima_interacao
        FROM clientes c
        LEFT JOIN atividades a ON c.id = a.cliente_id
        GROUP BY c.id
        ORDER BY c.valor_estimado DESC, c.id DESC
    """, conn)
    conn.close()

    if df_funil.empty:
        st.info(
            "Nenhuma empresa cadastrada ainda. Cadastre clientes na tela '1. Clientes' para visualizar o Funil de Vendas.")
        return

    df_funil["etapa_funil"] = df_funil["etapa_funil"].apply(lambda x: x if x in ETAPAS_FUNIL else ETAPAS_FUNIL[0])
    df_funil["valor_estimado"] = pd.to_numeric(df_funil["valor_estimado"], errors="coerce").fillna(0.0)

    status_info = df_funil["proximo_contato"].apply(avaliar_status_followup)
    df_funil["status_cod"] = [s[0] for s in status_info]
    df_funil["status_badge"] = [s[1] for s in status_info]

    etapas_abertas = ETAPAS_FUNIL[:4]
    df_aberto = df_funil[df_funil["etapa_funil"].isin(etapas_abertas)]
    df_ganho = df_funil[df_funil["etapa_funil"] == "5. Fechado (Cliente Ativo)"]
    df_perdido = df_funil[df_funil["etapa_funil"] == "Perdido / Inativo"]

    qtd_atrasados_hoje = len(df_aberto[df_aberto["status_cod"].isin(["ATRASADO", "HOJE"])])
    valor_pipeline_aberto = df_aberto["valor_estimado"].sum()
    valor_ganho = df_ganho["valor_estimado"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🏢 Oportunidades em Aberto", f"{len(df_aberto)} empresa(s)")
    k2.metric("💰 Pipeline em Negociação", formatar_moeda(valor_pipeline_aberto))
    k3.metric("✅ Clientes Fechados (Ativos)", f"{len(df_ganho)} ({formatar_moeda(valor_ganho)})")
    k4.metric("🔔 Follow-ups Hoje / Atrasados", f"{qtd_atrasados_hoje} pendente(s)")

    st.divider()

    f_busca, f_followup, f_cidade = st.columns([2.2, 1.5, 1.3])
    with f_busca:
        termo_k = st.text_input("🔍 Filtrar empresas (Nome, Responsável ou Interesse):",
                                placeholder="Digite para filtrar os cartões...")
    with f_followup:
        filtro_fw = st.selectbox("Filtrar por Status de Follow-up:", [
            "Todos os Cartões",
            "🔴 Apenas Atrasados ou Para Hoje",
            "🟢 Com Retorno Agendado",
            "⚪ Sem Retorno Definido"
        ])
    with f_cidade:
        cidades_disp = ["Todas as Cidades"] + sorted(
            [c for c in df_funil["cidade"].dropna().unique() if str(c).strip() != ""])
        cidade_k = st.selectbox("Filtrar por Cidade:", cidades_disp)

    df_kanban = df_funil.copy()
    if termo_k.strip():
        t = termo_k.strip()
        df_kanban = df_kanban[
            df_kanban["razao_social"].str.contains(t, case=False, na=False) |
            df_kanban["nome_fantasia"].str.contains(t, case=False, na=False) |
            df_kanban["responsavel_pf"].str.contains(t, case=False, na=False) |
            df_kanban["servico_interesse"].str.contains(t, case=False, na=False)
            ]
    if filtro_fw == "🔴 Apenas Atrasados ou Para Hoje":
        df_kanban = df_kanban[df_kanban["status_cod"].isin(["ATRASADO", "HOJE"])]
    elif filtro_fw == "🟢 Com Retorno Agendado":
        df_kanban = df_kanban[df_kanban["status_cod"].isin(["HOJE", "FUTURO"])]
    elif filtro_fw == "⚪ Sem Retorno Definido":
        df_kanban = df_kanban[df_kanban["status_cod"] == "SEM_DATA"]

    if cidade_k != "Todas as Cidades":
        df_kanban = df_kanban[df_kanban["cidade"] == cidade_k]

    etapas_principais = ETAPAS_FUNIL[:5]
    colunas_kanban = st.columns(5)
    cores_topo = ["🔵", "🟡", "🟠", "🟣", "🟢"]

    for idx, etapa in enumerate(etapas_principais):
        df_etapa = df_kanban[df_kanban["etapa_funil"] == etapa]
        soma_etapa = df_etapa["valor_estimado"].sum()

        with colunas_kanban[idx]:
            st.markdown(f"#### {cores_topo[idx]} {etapa}")
            st.caption(f"**{len(df_etapa)}** empresa(s) | **{formatar_moeda(soma_etapa)}**")
            st.markdown("---")

            for _, row in df_etapa.iterrows():
                cid = int(row["id"])
                with st.container(border=True):
                    st.markdown(f"**{row['razao_social']}**")
                    st.markdown(f"**{row['status_badge']}**")
                    st.markdown(f"👤 **Resp:** {row['responsavel_pf']}")
                    if row["telefone"]:
                        st.markdown(f"📞 {row['telefone']}")
                    if row["servico_interesse"]:
                        st.markdown(f"🎯 *{row['servico_interesse']}*")
                    st.markdown(f"💵 **{formatar_moeda(row['valor_estimado'])}**")
                    st.caption(f"📌 {row['total_atividades']} ativ. | 📍 {row['cidade'] or '-'}/{row['uf'] or '-'}")

                    b_esq, b_edit, b_ativ, b_dir = st.columns(4)
                    with b_esq:
                        if idx > 0:
                            etapa_ant = etapas_principais[idx - 1]
                            st.button(
                                "⬅️", key=f"prev_{cid}", help=f"Voltar para {etapa_ant}",
                                on_click=alterar_etapa_funil_rapido, args=(cid, etapa_ant), use_container_width=True
                            )
                    with b_edit:
                        if st.button("✏️", key=f"ed_k_{cid}", help="Editar Cadastro / Valor / Follow-up",
                                     use_container_width=True):
                            modal_editar_cliente(cid)
                    with b_ativ:
                        st.button(
                            "➕", key=f"at_k_{cid}", help="Lançar Atividade p/ este Cliente",
                            on_click=ir_para_lancamento_cliente, args=(cid,), use_container_width=True
                        )
                    with b_dir:
                        if idx < len(etapas_principais) - 1:
                            etapa_prox = etapas_principais[idx + 1]
                            st.button(
                                "➡️", key=f"next_{cid}", help=f"Avançar para {etapa_prox}",
                                on_click=alterar_etapa_funil_rapido, args=(cid, etapa_prox), use_container_width=True
                            )

    st.divider()
    col_resumo, col_perdidos = st.columns([1.2, 1.5])
    with col_resumo:
        st.subheader("📉 Resumo Consolidado por Etapa")
        resumo_lista = []
        for et in ETAPAS_FUNIL:
            sub = df_funil[df_funil["etapa_funil"] == et]
            resumo_lista.append({
                "Etapa do Funil": et,
                "Qtd. Empresas": len(sub),
                "Valor Total (R$)": formatar_moeda(sub["valor_estimado"].sum())
            })
        st.dataframe(pd.DataFrame(resumo_lista), use_container_width=True, hide_index=True)

    with col_perdidos:
        with st.expander(f"📁 Negócios Perdidos / Inativos ({len(df_perdido)})", expanded=False):
            if df_perdido.empty:
                st.info("Nenhuma empresa marcada como 'Perdido / Inativo'.")
            else:
                for _, row_p in df_perdido.iterrows():
                    cid_p = int(row_p["id"])
                    c_info, c_reab = st.columns([3, 1.2])
                    c_info.markdown(
                        f"**{row_p['razao_social']}** (Resp: {row_p['responsavel_pf']}) — {formatar_moeda(row_p['valor_estimado'])}")
                    c_reab.button(
                        "🔄 Reabrir no Funil", key=f"reab_{cid_p}",
                        on_click=alterar_etapa_funil_rapido, args=(cid_p, ETAPAS_FUNIL[0]), use_container_width=True
                    )