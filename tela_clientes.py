import math
import sqlite3
import pandas as pd
import streamlit as st
from database import conectar_db, CATEGORIAS_CLIENTE, STATUS_CLIENTE
from utils import (
    limpar_numeros,
    formatar_cep,
    consultar_cep_api,
    validar_cnpj_algoritmo,
    consultar_cnpj_api,
    formatar_cnaes_api,
)
from componentes import modal_editar_cliente

CAMPOS_CADASTRO = [
    "input_cnpj_api",
    "fld_cnpj",
    "fld_razao",
    "fld_fantasia",
    "fld_categoria",
    "fld_status",
    "fld_resp",
    "fld_tel",
    "fld_email",
    "fld_cep",
    "fld_log",
    "fld_num",
    "fld_comp",
    "fld_bairro",
    "fld_cidade",
    "fld_uf",
    "fld_cnae_prin",
    "fld_cnaes_sec",
]


def _extrair_responsaveis_qsa(dados_api):
    """Extrai nomes do quadro societário separando múltiplos nomes por ' / '."""
    if not isinstance(dados_api, dict):
        return ""
    qsa = dados_api.get("qsa")
    if not isinstance(qsa, list):
        return ""

    nomes = []
    for socio in qsa:
        if isinstance(socio, dict):
            nome = (
                socio.get("nome_socio")
                or socio.get("nome")
                or socio.get("nome_representante")
                or ""
            ).strip()
            if nome and nome not in nomes:
                nomes.append(nome)
        elif isinstance(socio, str) and socio.strip():
            nome_str = socio.strip()
            if nome_str not in nomes:
                nomes.append(nome_str)

    return " / ".join(nomes)


def _extrair_email_api(dados_api):
    """Extrai o e-mail retornado pela consulta de CNPJ quando disponível."""
    if not isinstance(dados_api, dict):
        return ""
    for chave in ("email", "correio_eletronico", "contato_email"):
        val = dados_api.get(chave)
        if isinstance(val, str) and val.strip() and val.strip().lower() != "none":
            return val.strip()
    return ""


def _garantir_estado_clientes():
    if "clientes_subtela" not in st.session_state:
        st.session_state.clientes_subtela = "consulta"
    if "limpar_form_pendente" not in st.session_state:
        st.session_state.limpar_form_pendente = False
    if "cep_aplicar_pendente" not in st.session_state:
        st.session_state.cep_aplicar_pendente = None
    if "ultimo_cnpj_consultado" not in st.session_state:
        st.session_state.ultimo_cnpj_consultado = ""
    if "tabela_clientes_nonce" not in st.session_state:
        st.session_state.tabela_clientes_nonce = 0

    padroes = {
        "input_cnpj_api": "",
        "fld_cnpj": "",
        "fld_razao": "",
        "fld_fantasia": "",
        "fld_categoria": CATEGORIAS_CLIENTE[0],
        "fld_status": "Ativo",
        "fld_resp": "",
        "fld_tel": "",
        "fld_email": "",
        "fld_cep": "",
        "fld_log": "",
        "fld_num": "",
        "fld_comp": "",
        "fld_bairro": "",
        "fld_cidade": "",
        "fld_uf": "",
        "fld_cnae_prin": "",
        "fld_cnaes_sec": "",
        "cad_aviso_cep": "",
    }
    for chave, valor in padroes.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def _aplicar_limpeza_campos_agora():
    """Roda sempre ANTES de instanciar os widgets de cadastro."""
    for chave in CAMPOS_CADASTRO:
        if chave == "fld_categoria":
            st.session_state[chave] = CATEGORIAS_CLIENTE[0]
        elif chave == "fld_status":
            st.session_state[chave] = "Ativo"
        else:
            st.session_state[chave] = ""
    st.session_state.cad_aviso_cep = ""
    st.session_state.ultimo_cnpj_consultado = ""
    st.session_state.cep_aplicar_pendente = None
    st.session_state.limpar_form_pendente = False


def _aplicar_cep_pendente_agora():
    """Roda sempre ANTES de instanciar os widgets de endereço."""
    dados_cep = st.session_state.get("cep_aplicar_pendente")
    st.session_state.cep_aplicar_pendente = None
    if not isinstance(dados_cep, dict):
        return

    if dados_cep.get("cep"):
        st.session_state.fld_cep = dados_cep["cep"]
    if dados_cep.get("logradouro"):
        st.session_state.fld_log = dados_cep["logradouro"]
    if dados_cep.get("complemento") and not (st.session_state.get("fld_comp") or "").strip():
        st.session_state.fld_comp = dados_cep["complemento"]
    if dados_cep.get("bairro"):
        st.session_state.fld_bairro = dados_cep["bairro"]
    if dados_cep.get("cidade"):
        st.session_state.fld_cidade = dados_cep["cidade"]
    if dados_cep.get("uf"):
        st.session_state.fld_uf = dados_cep["uf"]


def _executar_consulta_cnpj(cnpj_bruto, forcar=False):
    cnpj_limpo = limpar_numeros(cnpj_bruto)
    if not cnpj_limpo:
        return

    if not forcar and cnpj_limpo == st.session_state.get("ultimo_cnpj_consultado"):
        return

    st.session_state.fld_cnpj = cnpj_limpo
    if not validar_cnpj_algoritmo(cnpj_limpo):
        st.session_state.msg_alerta_cnpj = "CNPJ inválido. Verifique os 14 dígitos informados."
        return

    with st.spinner("Consultando dados da empresa..."):
        dados_api, erro_api = consultar_cnpj_api(cnpj_limpo)

    if erro_api:
        st.session_state.msg_alerta_cnpj = erro_api
        return

    if dados_api:
        st.session_state.ultimo_cnpj_consultado = cnpj_limpo
        st.session_state.fld_cnpj = cnpj_limpo
        st.session_state.fld_razao = (dados_api.get("razao_social") or "").strip()
        st.session_state.fld_fantasia = (dados_api.get("nome_fantasia") or "").strip()

        responsaveis_qsa = _extrair_responsaveis_qsa(dados_api)
        if responsaveis_qsa:
            st.session_state.fld_resp = responsaveis_qsa

        ddd_tel = limpar_numeros(dados_api.get("ddd_telefone_1") or "")
        st.session_state.fld_tel = ddd_tel if ddd_tel else ""

        email_api = _extrair_email_api(dados_api)
        st.session_state.fld_email = email_api

        st.session_state.fld_cep = formatar_cep(dados_api.get("cep") or "")
        tipo_log = (dados_api.get("descricao_tipo_de_logradouro") or "").strip()
        log_api = (dados_api.get("logradouro") or "").strip()
        st.session_state.fld_log = f"{tipo_log} {log_api}".strip()
        st.session_state.fld_num = (str(dados_api.get("numero") or "")).strip()
        st.session_state.fld_comp = (dados_api.get("complemento") or "").strip()
        st.session_state.fld_bairro = (dados_api.get("bairro") or "").strip()
        st.session_state.fld_cidade = (dados_api.get("municipio") or "").strip()
        st.session_state.fld_uf = (dados_api.get("uf") or "").strip().upper()
        cnae_p, cnae_s = formatar_cnaes_api(dados_api)
        st.session_state.fld_cnae_prin = cnae_p
        st.session_state.fld_cnaes_sec = cnae_s
        st.session_state.cad_aviso_cep = ""

        if email_api:
            st.session_state.msg_sucesso_cadastro = "Dados carregados pelo CNPJ (incluindo e-mail e quadro societário). Confira e salve."
        else:
            st.session_state.msg_sucesso_cadastro = (
                "Dados carregados pelo CNPJ. Observação: a API pública não retornou e-mail para este CNPJ; "
                "se necessário, preencha manualmente."
            )


def _ao_pressionar_enter_cnpj():
    _executar_consulta_cnpj(st.session_state.get("input_cnpj_api", ""), forcar=False)


def _preparar_busca_cep(cep_texto):
    cep_fmt = formatar_cep(cep_texto)
    cep_limpo = limpar_numeros(cep_fmt)

    if len(cep_limpo) != 8:
        st.session_state.cep_aplicar_pendente = {"cep": cep_fmt}
        st.session_state.cad_aviso_cep = "Informe um CEP com 8 dígitos ou preencha o endereço manualmente."
        return

    with st.spinner("Buscando endereço pelo CEP..."):
        dados_cep, erro_cep = consultar_cep_api(cep_limpo)

    if dados_cep:
        st.session_state.cad_aviso_cep = ""
        st.session_state.cep_aplicar_pendente = dados_cep
        st.session_state.msg_sucesso_cadastro = "📍 Endereço carregado pelo CEP."
    else:
        st.session_state.cep_aplicar_pendente = {"cep": cep_fmt}
        st.session_state.cad_aviso_cep = erro_cep or "CEP não localizado. Preencha o endereço manualmente."


def _renderizar_consulta_clientes():
    col_topo_esq, col_topo_dir = st.columns([3.2, 1.3])
    with col_topo_esq:
        st.subheader("📋 Clientes Cadastrados")
    with col_topo_dir:
        st.write("")
        if st.button("➕ Novo Cadastro", type="primary", use_container_width=True, key="btn_ir_novo_cadastro"):
            st.session_state.limpar_form_pendente = True
            st.session_state.clientes_subtela = "novo"
            st.rerun()

    conn = conectar_db()
    df_clientes = pd.read_sql_query("""
        SELECT id, cnpj, razao_social, nome_fantasia, categoria, status_cliente,
               responsavel_pf, telefone, email, cep, logradouro, numero,
               complemento, bairro, cidade, uf, cnae_principal, cnaes_secundarios
        FROM clientes
        ORDER BY razao_social ASC
    """, conn)
    conn.close()

    total_geral_base = len(df_clientes)

    if total_geral_base == 0:
        st.info("Nenhuma empresa cadastrada até o momento. Clique em 'Novo Cadastro' para incluir.")
        return

    f1, f2, f3, f4 = st.columns([2.2, 1.2, 1.1, 1.3])
    with f1:
        termo_busca = st.text_input(
            "Buscar por Razão Social, Nome Fantasia, CNPJ ou Responsável",
            placeholder="Digite para filtrar...",
            key="busca_cliente_lista"
        ).strip().lower()
    with f2:
        cat_filtro = st.selectbox("Categoria", ["Todas"] + list(CATEGORIAS_CLIENTE), key="filtro_cat_cliente")
    with f3:
        status_filtro = st.selectbox("Status", ["Todos"] + list(STATUS_CLIENTE), key="filtro_status_cliente")
    with f4:
        cidades_disp = sorted([
            c for c in df_clientes["cidade"].dropna().astype(str).str.strip().unique() if c
        ])
        cid_filtro = st.selectbox("Cidade", ["Todas"] + cidades_disp, key="filtro_cid_cliente")

    df_view = df_clientes.copy()
    df_view["categoria"] = df_view["categoria"].fillna(CATEGORIAS_CLIENTE[0])
    df_view["status_cliente"] = df_view["status_cliente"].fillna("Ativo")

    if termo_busca:
        termo_num = limpar_numeros(termo_busca)
        mascara = (
            df_view["razao_social"].fillna("").str.lower().str.contains(termo_busca, regex=False)
            | df_view["nome_fantasia"].fillna("").str.lower().str.contains(termo_busca, regex=False)
            | df_view["responsavel_pf"].fillna("").str.lower().str.contains(termo_busca, regex=False)
            | df_view["cnpj"].fillna("").apply(limpar_numeros).str.contains(termo_num if termo_num else "___", regex=False)
        )
        df_view = df_view[mascara]

    if cat_filtro != "Todas":
        df_view = df_view[df_view["categoria"] == cat_filtro]

    if status_filtro != "Todos":
        df_view = df_view[df_view["status_cliente"] == status_filtro]

    if cid_filtro != "Todas":
        df_view = df_view[df_view["cidade"].fillna("").str.strip() == cid_filtro]

    total_filtrado = len(df_view)

    p_col1, p_col2, p_col3 = st.columns([1.2, 1.3, 2.5])
    with p_col1:
        itens_por_pagina = st.selectbox(
            "Registros por página",
            [10, 20, 50, 100],
            index=1,
            key="qtd_por_pagina_clientes"
        )
    total_paginas = max(1, math.ceil(total_filtrado / itens_por_pagina)) if total_filtrado > 0 else 1
    if "pagina_atual_clientes" not in st.session_state:
        st.session_state.pagina_atual_clientes = 1
    if st.session_state.pagina_atual_clientes > total_paginas:
        st.session_state.pagina_atual_clientes = total_paginas

    with p_col2:
        pagina_sel = st.number_input(
            f"Página (1 a {total_paginas})",
            min_value=1,
            max_value=total_paginas,
            value=int(st.session_state.pagina_atual_clientes),
            step=1,
            key="num_pagina_clientes"
        )
        st.session_state.pagina_atual_clientes = int(pagina_sel)

    inicio_idx = (st.session_state.pagina_atual_clientes - 1) * itens_por_pagina
    fim_idx = inicio_idx + itens_por_pagina
    df_pagina = df_view.iloc[inicio_idx:fim_idx].copy()
    qtd_exibida = len(df_pagina)

    with p_col3:
        st.write("")
        st.markdown(
            f"**Exibindo {qtd_exibida} de {total_filtrado} filtrados** "
            f"*(Total geral na base: {total_geral_base} clientes)*"
        )

    st.caption("Clique em uma linha da tabela para alterar ou excluir o cadastro.")

    df_tabela = pd.DataFrame({
        "ID": df_pagina["id"],
        "CNPJ": df_pagina["cnpj"],
        "Razão Social": df_pagina["razao_social"],
        "Nome Fantasia": df_pagina["nome_fantasia"].fillna(""),
        "Categoria": df_pagina["categoria"],
        "Status": df_pagina["status_cliente"],
        "Responsável": df_pagina["responsavel_pf"],
        "Telefone": df_pagina["telefone"].fillna(""),
        "E-mail": df_pagina["email"].fillna(""),
        "CEP": df_pagina["cep"].fillna("").apply(formatar_cep),
        "Cidade": df_pagina["cidade"].fillna(""),
        "UF": df_pagina["uf"].fillna(""),
        "CNAE Principal": df_pagina["cnae_principal"].fillna(""),
    }).reset_index(drop=True)

    nonce = int(st.session_state.get("tabela_clientes_nonce", 0))
    evento = st.dataframe(
        df_tabela,
        use_container_width=True,
        hide_index=True,
        height=520,
        on_select="rerun",
        selection_mode="single-row",
        key=f"tabela_relacao_clientes_{nonce}"
    )

    linhas_sel = evento.selection.rows if (evento and evento.selection) else []
    if linhas_sel and len(df_tabela) > 0:
        idx_linha = int(linhas_sel[0])
        if 0 <= idx_linha < len(df_tabela):
            id_selecionado = int(df_tabela.iloc[idx_linha]["ID"])
            modal_editar_cliente(id_selecionado)


def _renderizar_novo_cadastro_cliente():
    col_esq, col_dir = st.columns([3.2, 1.3])
    with col_esq:
        st.subheader("➕ Cadastro de Novo Cliente")
    with col_dir:
        st.write("")
        if st.button("⬅️ Voltar para Consulta", use_container_width=True, key="btn_voltar_consulta_cli"):
            st.session_state.limpar_form_pendente = True
            st.session_state.clientes_subtela = "consulta"
            st.rerun()

    if "msg_alerta_cnpj" in st.session_state:
        st.warning(st.session_state.msg_alerta_cnpj)
        del st.session_state.msg_alerta_cnpj

    with st.container(border=True):
        st.markdown("##### Consulta Automática por CNPJ")
        col_cnpj_in, col_cnpj_btn = st.columns([2.5, 1.3])
        with col_cnpj_in:
            st.text_input(
                "CNPJ para Consulta (pressione Enter ou clique em Buscar)",
                placeholder="00.000.000/0001-00",
                key="input_cnpj_api",
                on_change=_ao_pressionar_enter_cnpj
            )
        with col_cnpj_btn:
            st.write("")
            st.write("")
            if st.button("🔍 Buscar CNPJ", type="primary", use_container_width=True, key="btn_buscar_cnpj"):
                _executar_consulta_cnpj(st.session_state.get("input_cnpj_api", ""), forcar=True)
                st.rerun()

    with st.container(border=True):
        st.markdown("##### Dados da Empresa")
        c1, c2, c3, c4 = st.columns([1.4, 2.1, 1.2, 1.0])
        with c1:
            cnpj_val = st.text_input("CNPJ *", key="fld_cnpj")
        with c2:
            razao_val = st.text_input("Razão Social *", key="fld_razao")
        with c3:
            cat_val = st.selectbox("Categoria *", CATEGORIAS_CLIENTE, key="fld_categoria")
        with c4:
            status_val = st.selectbox("Status *", STATUS_CLIENTE, key="fld_status")

        f1, r1, r2, r3 = st.columns([1.5, 1.8, 1.4, 1.6])
        with f1:
            fantasia_val = st.text_input("Nome Fantasia", key="fld_fantasia")
        with r1:
            resp_val = st.text_input("Responsável *", key="fld_resp")
        with r2:
            tel_val = st.text_input("Telefone / WhatsApp", key="fld_tel")
        with r3:
            email_val = st.text_input("E-mail", key="fld_email")

        st.markdown("##### CNAEs")
        cnae_p_val = st.text_input("CNAE Principal", key="fld_cnae_prin")
        cnae_s_val = st.text_area("CNAEs Secundários", height=75, key="fld_cnaes_sec")

        st.markdown("##### Endereço")
        col_cep_campo, col_cep_acao = st.columns([1.5, 1.5])
        with col_cep_campo:
            cep_input_bruto = st.text_input("CEP", placeholder="00000-000", key="fld_cep")
        with col_cep_acao:
            st.write("")
            st.write("")
            if st.button("🔎 Buscar CEP", key="btn_buscar_cep", use_container_width=True):
                _preparar_busca_cep(cep_input_bruto)
                st.rerun()

        if st.session_state.get("cad_aviso_cep"):
            st.info(st.session_state.cad_aviso_cep)

        e1, e2, e3 = st.columns([2.8, 1.0, 1.4])
        with e1:
            log_val = st.text_input("Logradouro", key="fld_log")
        with e2:
            num_val = st.text_input("Número", key="fld_num")
        with e3:
            comp_val = st.text_input("Complemento", key="fld_comp")

        e4, e5, e6 = st.columns([2.2, 2.2, 0.9])
        with e4:
            bairro_val = st.text_input("Bairro", key="fld_bairro")
        with e5:
            cidade_val = st.text_input("Cidade", key="fld_cidade")
        with e6:
            uf_val = st.text_input("UF", max_chars=2, key="fld_uf")

        b1, b2 = st.columns([1.6, 1.0])
        with b1:
            if st.button("💾 Salvar Cadastro da Empresa", type="primary", use_container_width=True, key="btn_salvar_cliente"):
                cnpj_limpo = limpar_numeros(cnpj_val)
                if not validar_cnpj_algoritmo(cnpj_limpo):
                    st.error("CNPJ inválido. Informe um CNPJ válido com 14 dígitos.")
                elif not razao_val.strip() or not resp_val.strip():
                    st.error("Os campos 'Razão Social' e 'Responsável' são obrigatórios.")
                else:
                    try:
                        conn = conectar_db()
                        conn.execute("""
                            INSERT INTO clientes (
                                cnpj, razao_social, nome_fantasia, responsavel_pf,
                                telefone, email, cep, logradouro, numero, complemento,
                                bairro, cidade, uf, categoria, status_cliente,
                                cnae_principal, cnaes_secundarios
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cnpj_limpo,
                            razao_val.strip(),
                            fantasia_val.strip(),
                            resp_val.strip(),
                            tel_val.strip(),
                            email_val.strip(),
                            formatar_cep(cep_input_bruto),
                            log_val.strip(),
                            num_val.strip(),
                            comp_val.strip(),
                            bairro_val.strip(),
                            cidade_val.strip(),
                            uf_val.strip().upper(),
                            cat_val,
                            status_val,
                            cnae_p_val.strip(),
                            cnae_s_val.strip(),
                        ))
                        conn.commit()
                        conn.close()
                        st.session_state.limpar_form_pendente = True
                        st.session_state.clientes_subtela = "consulta"
                        st.session_state.msg_sucesso_cadastro = f"✅ Empresa '{razao_val.strip()}' cadastrada com sucesso!"
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Já existe uma empresa cadastrada com este CNPJ.")
        with b2:
            if st.button("🧹 Limpar Campos", use_container_width=True, key="btn_limpar_cliente"):
                st.session_state.limpar_form_pendente = True
                st.rerun()


def renderizar_tela_clientes():
    st.title("👥 Gestão de Clientes")
    _garantir_estado_clientes()

    if st.session_state.get("limpar_form_pendente"):
        _aplicar_limpeza_campos_agora()

    if st.session_state.get("cep_aplicar_pendente"):
        _aplicar_cep_pendente_agora()

    if "msg_sucesso_cadastro" in st.session_state:
        msg_txt = st.session_state.msg_sucesso_cadastro
        st.toast(msg_txt)
        st.success(msg_txt)
        del st.session_state.msg_sucesso_cadastro

    if st.session_state.clientes_subtela == "novo":
        _renderizar_novo_cadastro_cliente()
    else:
        _renderizar_consulta_clientes()