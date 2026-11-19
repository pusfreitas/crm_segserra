import sqlite3
import pandas as pd
from utils import (
)

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

def _aplicar_cep_pendente_agora():
    """Roda sempre ANTES de instanciar os widgets de endereço."""
    dados_cep = st.session_state.get("cep_aplicar_pendente")
    st.session_state.cep_aplicar_pendente = None
    if not isinstance(dados_cep, dict):
        return


        return

    st.session_state.fld_cnpj = cnpj_limpo
    if not validar_cnpj_algoritmo(cnpj_limpo):
        return



        else:




def renderizar_tela_clientes():
    inicializar_estado_clientes()






    conn = conectar_db()
    """, conn)
    conn.close()


        )


        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )


                col_sel, col_btn_edit, col_atalho = st.columns([2.6, 1.2, 1.2])
                with col_sel:
                    cliente_hist_label = st.selectbox("Selecione a empresa listada acima:", list(opcoes_hist.keys()))
                cliente_hist_row = opcoes_hist[cliente_hist_label]

        st.write("")


            st.text_input(
                placeholder="00.000.000/0001-00",
            )
            st.write("")
            st.write("")

        with c1:
        with c2:

        with f1:

        with e1:
        with e2:
        with e3:
        with e4:
        with e5:
        with e6:

        b1, b2 = st.columns([1.6, 1.0])
        with b1:
            if st.button("💾 Salvar Cadastro da Empresa", type="primary", use_container_width=True, key="btn_salvar_cliente"):
                cnpj_limpo = limpar_numeros(cnpj_val)
                if not validar_cnpj_algoritmo(cnpj_limpo):
                else:
                    try:
                        str_prox = st.session_state.cad_prox_contato.strftime(
                            "%d/%m/%Y") if st.session_state.cad_prox_contato else ""
                        conn = conectar_db()
                            INSERT INTO clientes (
                                cnpj, razao_social, nome_fantasia, responsavel_pf,
                                telefone, email, cep, logradouro, numero, complemento,
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cnpj_limpo,
                        ))
                        conn.commit()
                        conn.close()
                        st.rerun()
                    except sqlite3.IntegrityError:
                st.rerun()

    else: