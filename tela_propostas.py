import os
import json
import uuid
import base64
import html
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime
from database import conectar_db, obter_permissoes_perfil
from utils import formatar_moeda, converter_str_data


def formatar_cnpj_exibicao(cnpj_str):
    numeros = "".join([c for c in str(cnpj_str or "") if c.isdigit()])
    if len(numeros) == 14:
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
    return cnpj_str or ""


def _perms_usuario():
    perfil = st.session_state.get("perfil_usuario", "Comercial / Atendimento")
    return obter_permissoes_perfil(perfil)


def _resetar_selecao_tabela_propostas():
    st.session_state.tabela_propostas_nonce = int(st.session_state.get("tabela_propostas_nonce", 0)) + 1
    st.session_state.proposta_selecionada_id = None


def _focar_primeiro_campo_nova_proposta():
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const anchor = doc.getElementById("ancora_editor_proposta");
            if (anchor) {
                anchor.scrollIntoView({ behavior: "smooth", block: "start" });
            }
            setTimeout(() => {
                const inputs = doc.querySelectorAll('input, textarea, div[data-baseweb="select"] input');
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


def _obter_logo_html():
    caminho_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
    if os.path.exists(caminho_logo):
        with open(caminho_logo, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"""
            <div style="display:flex;align-items:center;gap:14px;">
                <img src="data:image/png;base64,{b64}" alt="SegSerra"
                     style="max-height:54px;width:auto;border-radius:6px;background:#ffffff;padding:4px 8px;" />
                <div>
                    <div class="prop-marca-sub">Saúde e Segurança do Trabalho</div>
                </div>
            </div>
        """
    return """
        <div style="display:flex;align-items:center;gap:12px;">
            <svg width="36" height="36" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="15" y="3" width="10" height="34" rx="3.5" fill="#2dd2cd"/>
                <rect x="3" y="15" width="34" height="10" rx="3.5" fill="#2dd2cd"/>
            </svg>
            <div>
                <div class="prop-marca-nome">SegSerra</div>
                <div class="prop-marca-sub">Saúde e Segurança do Trabalho</div>
            </div>
        </div>
    """


def _normalizar_itens(itens_servico):
    normalizados = []
    for item in (itens_servico or []):
        desc = str(item.get("servico") or "").strip()
        try:
            v_unit = float(item.get("valor_unitario") or 0.0)
        except Exception:
            v_unit = 0.0
        try:
            qtd = float(item.get("quantidade") or 1.0)
        except Exception:
            qtd = 1.0
        total_item = round(max(0.0, v_unit) * max(0.0, qtd), 2)
        if desc or v_unit > 0 or qtd > 0:
            normalizados.append({
                "servico": desc or "Serviço SST",
                "valor_unitario": round(max(0.0, v_unit), 2),
                "quantidade": max(0.0, qtd),
                "valor_total": total_item,
            })
    return normalizados


def calcular_total_itens(itens_servico):
    return round(sum(i["valor_total"] for i in _normalizar_itens(itens_servico)), 2)


def _extrair_itens_de_linha_db(row_dict):
    try:
        itens = json.loads(row_dict.get("itens_json") or "[]")
    except Exception:
        itens = []
    if itens:
        return _normalizar_itens(itens)
    return _normalizar_itens([{
        "servico": row_dict.get("servicos") or "Serviços SST",
        "valor_unitario": float(row_dict.get("valor_investimento") or 0.0),
        "quantidade": 1.0,
    }])


def _montar_contatos_cliente(cli_row):
    partes = []
    resp = (cli_row.get("responsavel_pf") or "").strip()
    tel = (cli_row.get("telefone") or "").strip()
    email = (cli_row.get("email") or "").strip()
    if resp:
        partes.append(resp)
    if tel:
        partes.append(tel)
    if email:
        partes.append(email)
    return " | ".join(partes)


def montar_texto_proposta(
    data_emissao_str,
    razao_social,
    cnpj_fmt,
    solicitante,
    contatos,
    itens_servico,
    condicoes_pag,
    obs_art,
    status_proposta="Aguardando Aceite",
):
    itens = _normalizar_itens(itens_servico)
    valor_total = calcular_total_itens(itens)
    valor_fmt = formatar_moeda(valor_total)

    linhas = [
        "PROPOSTA COMERCIAL",
        "",
        f"{data_emissao_str} - Proposta Comercial | Status: {status_proposta}",
        "",
        f"Cliente: {razao_social}",
        f"CNPJ: {cnpj_fmt}",
        f"Solicitante: {solicitante}",
        f"Contatos: {contatos}",
        "",
        "Serviços",
    ]
    for it in itens:
        qtd_str = f"{it['quantidade']:g}"
        linhas.append(
            f"- {it['servico']} | Unit: {formatar_moeda(it['valor_unitario'])} | "
            f"Qtd: {qtd_str} | Total: {formatar_moeda(it['valor_total'])}"
        )

    linhas.extend([
        "",
        "Investimento",
        valor_fmt,
        "",
        "Condições de pagamento",
        condicoes_pag.strip(),
    ])
    if obs_art.strip():
        linhas.extend(["", "Observações", obs_art.strip()])
    linhas.extend([
        "",
        "Aceite da proposta comercial",
        "O aceite desta Proposta Comercial implica na concordância com todos os seus termos. "
        "Havendo necessidade de alteração em qualquer item após a formalização, este instrumento "
        "será substituído por um novo, ficando as revisões anteriores integralmente revogadas.",
        "",
        f"Bento Gonçalves/RS, {data_emissao_str}.",
        "",
        "________________________________________",
        razao_social,
        "",
        "SEGSERRA GESTAO EM SAUDE MEDICINA E SEGURANCA DO TRABALHO LTDA",
        "Rua Dr José Mário Mônaco, 195 – Centro - Bento Gonçalves – RS",
        "(54) 3055-3009 | www.segserra.com.br | comercial@segserra.com.br",
    ])
    return "\n".join(linhas)


def montar_html_proposta(
    data_emissao_str,
    razao_social,
    cnpj_fmt,
    solicitante,
    contatos,
    itens_servico,
    condicoes_pag,
    obs_art,
    status_proposta="Aguardando Aceite",
    data_aceite="",
    para_impressao_tela=False,
    exibir_botao_imprimir=False,
):
    itens = _normalizar_itens(itens_servico)
    valor_total = calcular_total_itens(itens)
    valor_fmt = html.escape(formatar_moeda(valor_total))

    e_razao = html.escape(razao_social or "")
    e_cnpj = html.escape(cnpj_fmt or "")
    e_solicitante = html.escape(solicitante or "")
    e_contatos = html.escape(contatos or "—")
    e_data = html.escape(data_emissao_str or "")
    e_cond = html.escape(condicoes_pag or "—")
    e_status = html.escape(status_proposta or "Aguardando Aceite")
    e_obs = html.escape(obs_art.strip()) if obs_art and obs_art.strip() else ""
    logo_html = _obter_logo_html()

    linhas_tabela = []
    for it in itens:
        e_srv = html.escape(it["servico"])
        e_unit = html.escape(formatar_moeda(it["valor_unitario"]))
        e_qtd = html.escape(f"{it['quantidade']:g}")
        e_tot = html.escape(formatar_moeda(it["valor_total"]))
        linhas_tabela.append(
            f"<tr>"
            f"<td>{e_srv}</td>"
            f"<td class='col-num'>{e_unit}</td>"
            f"<td class='col-qtd'>{e_qtd}</td>"
            f"<td class='col-num prop-td-total'>{e_tot}</td>"
            f"</tr>"
        )

    if not linhas_tabela:
        linhas_tabela.append(
            "<tr><td colspan='4' style='color:#64748b;text-align:center;'>Nenhum item adicionado.</td></tr>"
        )

    bloco_obs_html = ""
    if e_obs:
        bloco_obs_html = f"""
        <div class="prop-secao">
            <div class="prop-rotulo">Observações Técnicas e Legais</div>
            <div class="prop-texto-suave">{e_obs.replace(chr(10), "<br>")}</div>
        </div>
        """

    if status_proposta == "Aprovada":
        badge_cor_bg, badge_cor_txt = "#dcfce7", "#166534"
    elif status_proposta in ("Recusada", "Cancelada"):
        badge_cor_bg, badge_cor_txt = "#fee2e2", "#991b1b"
    else:
        badge_cor_bg, badge_cor_txt = "#fef9c3", "#854d0e"

    info_aceite = f" em {html.escape(data_aceite)}" if data_aceite else ""

    botao_pdf_html = ""
    if exibir_botao_imprimir:
        botao_pdf_html = """
        <div class="prop-barra-pdf no-print">
            <button type="button" class="prop-btn-pdf" onclick="window.print()">
                📄 Baixar / Imprimir em PDF
            </button>
        </div>
        """

    css_tela_extra = "" if para_impressao_tela else """
        .prop-folha {
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
            border: 1px solid #e2e8f0;
        }
    """

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Proposta Comercial - {e_razao}</title>
<style>
    @page {{
        size: A4 portrait;
        margin: 14mm;
    }}
    * {{
        box-sizing: border-box;
    }}
    body {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #1e293b;
        background: #f8fafc;
        margin: 0;
        padding: { "0" if para_impressao_tela else "12px" };
        line-height: 1.55;
    }}
    .prop-barra-pdf {{
        max-width: 820px;
        margin: 0 auto 12px auto;
        display: flex;
        justify-content: flex-end;
    }}
    .prop-btn-pdf {{
        background: #0f2f34;
        color: #ffffff;
        border: 1px solid #0f5257;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
    }}
    .prop-btn-pdf:hover {{
        background: #0f5257;
    }}
    .prop-folha {{
        background: #ffffff;
        max-width: 820px;
        margin: 0 auto;
        border-radius: 10px;
        overflow: hidden;
        {css_tela_extra}
    }}
    .prop-topo {{
        background: #0f2f34;
        color: #ffffff;
        padding: 24px 32px;
        border-bottom: 4px solid #2dd2cd;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
    }}
    .prop-marca-nome {{
        font-size: 24px;
        font-weight: 700;
        letter-spacing: 0.4px;
        color: #ffffff;
        line-height: 1.1;
    }}
    .prop-marca-sub {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        color: #99f6e4;
        font-weight: 600;
    }}
    .prop-doc-meta {{
        text-align: right;
    }}
    .prop-doc-tag {{
        display: inline-block;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #2dd2cd;
        margin-bottom: 4px;
    }}
    .prop-doc-data {{
        font-size: 13px;
        color: #e2e8f0;
    }}
    .prop-status-badge {{
        display: inline-block;
        margin-top: 6px;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        background: {badge_cor_bg};
        color: {badge_cor_txt};
    }}
    .prop-corpo {{
        padding: 26px 32px;
    }}
    .prop-grade-cliente {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px 24px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #0f5257;
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 22px;
    }}
    .prop-campo-label {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 2px;
    }}
    .prop-campo-valor {{
        font-size: 14px;
        color: #0f172a;
        font-weight: 600;
    }}
    .prop-secao {{
        margin-bottom: 22px;
    }}
    .prop-rotulo {{
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #0f5257;
        font-weight: 700;
        padding-bottom: 6px;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 12px;
    }}
    .prop-tabela-servicos {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13.5px;
    }}
    .prop-tabela-servicos th {{
        background: #f1f5f9;
        color: #0f2f34;
        font-weight: 700;
        text-align: left;
        padding: 10px 12px;
        border-bottom: 2px solid #cbd5e1;
    }}
    .prop-tabela-servicos th.col-num,
    .prop-tabela-servicos td.col-num {{
        text-align: right;
        white-space: nowrap;
    }}
    .prop-tabela-servicos th.col-qtd,
    .prop-tabela-servicos td.col-qtd {{
        text-align: center;
        white-space: nowrap;
    }}
    .prop-tabela-servicos td {{
        padding: 10px 12px;
        border-bottom: 1px solid #e2e8f0;
        color: #1e293b;
        vertical-align: top;
    }}
    .prop-td-total {{
        font-weight: 700;
        color: #0f5257;
    }}
    .prop-destaque-comercial {{
        display: grid;
        grid-template-columns: 1fr 2fr;
        gap: 16px;
        background: #f4fbfb;
        border: 1px solid #cceeee;
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 22px;
        align-items: center;
    }}
    .prop-valor-numero {{
        font-size: 24px;
        font-weight: 700;
        color: #0f5257;
        margin-top: 2px;
    }}
    .prop-texto-suave {{
        font-size: 13px;
        color: #334155;
    }}
    .prop-aceite-box {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        margin-top: 20px;
        margin-bottom: 24px;
    }}
    .prop-aceite-titulo {{
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #0f5257;
        margin-bottom: 6px;
    }}
    .prop-aceite-texto {{
        font-size: 12.5px;
        color: #475569;
        margin: 0;
    }}
    .prop-assinaturas {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 32px;
        margin-top: 24px;
        padding-top: 10px;
        flex-wrap: wrap;
    }}
    .prop-local-data {{
        font-size: 13px;
        color: #334155;
        font-weight: 500;
    }}
    .prop-linha-assinatura {{
        flex: 1;
        min-width: 240px;
        max-width: 340px;
        text-align: center;
    }}
    .prop-traco {{
        border-top: 1px solid #334155;
        margin-bottom: 6px;
        margin-top: 32px;
    }}
    .prop-assinatura-nome {{
        font-size: 13px;
        font-weight: 600;
        color: #0f172a;
    }}
    .prop-rodape {{
        background: #f1f5f9;
        border-top: 1px solid #e2e8f0;
        padding: 16px 32px;
        font-size: 11.5px;
        color: #475569;
        text-align: center;
    }}
    .prop-rodape strong {{
        color: #0f2f34;
    }}
    @media print {{
        body {{
            background: #ffffff;
            padding: 0;
        }}
        .prop-folha {{
            box-shadow: none;
            border: none;
            max-width: 100%;
        }}
        .no-print {{
            display: none !important;
        }}
    }}
</style>
</head>
<body>
    {botao_pdf_html}
    <div class="prop-folha">
        <div class="prop-topo">
            {logo_html}
            <div class="prop-doc-meta">
                <div class="prop-doc-tag">Proposta Comercial</div>
                <div class="prop-doc-data">Emissão: <strong>{e_data}</strong></div>
                <div class="prop-status-badge">{e_status}{info_aceite}</div>
            </div>
        </div>

        <div class="prop-corpo">
            <div class="prop-grade-cliente">
                <div>
                    <div class="prop-campo-label">Cliente / Razão Social</div>
                    <div class="prop-campo-valor">{e_razao}</div>
                </div>
                <div>
                    <div class="prop-campo-label">CNPJ</div>
                    <div class="prop-campo-valor">{e_cnpj}</div>
                </div>
                <div>
                    <div class="prop-campo-label">Solicitante</div>
                    <div class="prop-campo-valor">{e_solicitante}</div>
                </div>
                <div>
                    <div class="prop-campo-label">Contatos</div>
                    <div class="prop-campo-valor">{e_contatos}</div>
                </div>
            </div>

            <div class="prop-secao">
                <div class="prop-rotulo">Escopo dos Serviços</div>
                <table class="prop-tabela-servicos">
                    <thead>
                        <tr>
                            <th>Serviço</th>
                            <th class="col-num">Valor unitário</th>
                            <th class="col-qtd">Quantidade</th>
                            <th class="col-num">Valor total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(linhas_tabela)}
                    </tbody>
                </table>
            </div>

            <div class="prop-destaque-comercial">
                <div>
                    <div class="prop-campo-label">Investimento</div>
                    <div class="prop-valor-numero">{valor_fmt}</div>
                </div>
                <div>
                    <div class="prop-campo-label">Condições de Pagamento</div>
                    <div class="prop-campo-valor" style="font-weight: 500;">{e_cond}</div>
                </div>
            </div>

            {bloco_obs_html}

            <div class="prop-aceite-box">
                <div class="prop-aceite-titulo">Aceite da Proposta Comercial</div>
                <p class="prop-aceite-texto">
                    O aceite desta Proposta Comercial implica na concordância com todos os seus termos.
                    Havendo necessidade de alteração em qualquer item após a formalização, este instrumento
                    será substituído por um novo, ficando as revisões anteriores integralmente revogadas.
                </p>
            </div>

            <div class="prop-assinaturas">
                <div class="prop-local-data">Bento Gonçalves/RS, {e_data}.</div>
                <div class="prop-linha-assinatura">
                    <div class="prop-traco"></div>
                    <div class="prop-assinatura-nome">{e_razao}</div>
                </div>
            </div>
        </div>

        <div class="prop-rodape">
            <strong>SEGSERRA GESTAO EM SAUDE MEDICINA E SEGURANCA DO TRABALHO LTDA</strong><br>
            Rua Dr José Mário Mônaco, 195 – Centro - Bento Gonçalves – RS<br>
            (54) 3055-3009 &nbsp;|&nbsp; www.segserra.com.br &nbsp;|&nbsp; comercial@segserra.com.br
        </div>
    </div>
</body>
</html>"""


def renderizar_aceite_cliente_por_token(token_aceite):
    """Tela de aceite comercial acessada pelo cliente via link (?proposta=<token>)."""
    conn = conectar_db()
    df_p = pd.read_sql_query("""
        SELECT p.*, c.razao_social, c.cnpj
        FROM propostas p
        JOIN clientes c ON p.cliente_id = c.id
        WHERE p.token_aceite = ?
    """, conn, params=(str(token_aceite).strip(),))
    conn.close()

    if df_p.empty:
        st.error("Link de proposta comercial inválido ou não encontrado.")
        return

    row = df_p.iloc[0]
    itens = _extrair_itens_de_linha_db(dict(row))

    status_atual = row.get("status_proposta") or "Aguardando Aceite"
    data_aceite_atual = row.get("data_aceite") or ""
    cnpj_fmt = formatar_cnpj_exibicao(row["cnpj"])

    html_cliente = montar_html_proposta(
        data_emissao_str=row["data_emissao"],
        razao_social=row["razao_social"],
        cnpj_fmt=cnpj_fmt,
        solicitante=row["solicitante"],
        contatos=row["contatos"],
        itens_servico=itens,
        condicoes_pag=row["condicoes_pagamento"],
        obs_art=row["observacoes_art"],
        status_proposta=status_atual,
        data_aceite=data_aceite_atual,
        para_impressao_tela=True,
        exibir_botao_imprimir=True,
    )

    st.components.v1.html(html_cliente, height=820, scrolling=True)

    with st.container(border=True):
        st.subheader("Confirmação de Aceite Comercial")
        if status_atual == "Aprovada":
            st.success(
                f"✅ Esta proposta comercial foi **Aprovada** em {data_aceite_atual or 'data registrada'}. "
                "A equipe da SegSerra já foi notificada e dará andamento ao atendimento."
            )
        elif status_atual in ("Recusada", "Cancelada"):
            st.warning(f"Esta proposta comercial consta atualmente como **{status_atual}**.")
        else:
            aceitou = st.checkbox(
                "Aceito os termos desta proposta comercial.",
                key="chk_aceite_termos_cliente",
            )
            if st.button("Confirmar Aceite da Proposta", type="primary", disabled=not aceitou):
                agora_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
                conn = conectar_db()
                conn.execute("""
                    UPDATE propostas
                    SET status_proposta = 'Aprovada', data_aceite = ?
                    WHERE id = ?
                """, (agora_str, int(row["id"])))
                conn.execute("""
                    UPDATE clientes
                    SET etapa_funil = '5. Fechado (Cliente Ativo)'
                    WHERE id = ?
                """, (int(row["cliente_id"]),))
                conn.commit()
                conn.close()
                st.success(
                    f"✅ Aceite registrado com sucesso em {agora_str}! "
                    "O status da proposta agora consta como **Aprovada**."
                )
                st.rerun()


def _preparar_itens_formulario(chave_sessao, itens_iniciais=None, valor_padrao=900.0):
    if chave_sessao not in st.session_state or not st.session_state[chave_sessao]:
        if itens_iniciais:
            st.session_state[chave_sessao] = [
                {
                    "servico": i["servico"],
                    "valor_unitario": float(i["valor_unitario"]),
                    "quantidade": float(i["quantidade"]),
                }
                for i in _normalizar_itens(itens_iniciais)
            ]
        else:
            st.session_state[chave_sessao] = [
                {
                    "servico": "Emissão/Renovação dos laudos de saúde e segurança do trabalho (PGR/PCMSO/LTCAT) com validade de 12 meses.",
                    "valor_unitario": float(valor_padrao or 900.0),
                    "quantidade": 1.0,
                }
            ]
    return st.session_state[chave_sessao]


def _renderizar_editor_itens(chave_sessao, prefixo_widget):
    st.markdown("#### Escopo dos Serviços (Serviço, Valor unitário, Quantidade e Valor total)")
    itens_atuais = st.session_state[chave_sessao]

    col_add, col_rem, _ = st.columns([1.2, 1.4, 2.4])
    with col_add:
        if st.button("➕ Adicionar linha", key=f"{prefixo_widget}_add"):
            itens_atuais.append({"servico": "", "valor_unitario": 0.0, "quantidade": 1.0})
            st.rerun()
    with col_rem:
        if st.button("➖ Remover última linha", key=f"{prefixo_widget}_rem", disabled=len(itens_atuais) <= 1):
            itens_atuais.pop()
            st.rerun()

    itens_editados = []
    for idx, item in enumerate(itens_atuais):
        col_s, col_u, col_q, col_t, col_del = st.columns([3.2, 1.3, 1.0, 1.3, 0.5])
        with col_s:
            srv_val = st.text_input(
                "Serviço",
                value=item.get("servico", ""),
                key=f"{prefixo_widget}_srv_{idx}",
                label_visibility="collapsed" if idx > 0 else "visible",
                placeholder="Descrição do serviço",
            )
        with col_u:
            unit_val = st.number_input(
                "Valor unitário (R$)",
                min_value=0.0,
                step=50.0,
                value=float(item.get("valor_unitario") or 0.0),
                key=f"{prefixo_widget}_unit_{idx}",
                label_visibility="collapsed" if idx > 0 else "visible",
            )
        with col_q:
            qtd_val = st.number_input(
                "Quantidade",
                min_value=0.0,
                step=1.0,
                value=float(item.get("quantidade") or 1.0),
                key=f"{prefixo_widget}_qtd_{idx}",
                label_visibility="collapsed" if idx > 0 else "visible",
            )
        tot_linha = round(float(unit_val) * float(qtd_val), 2)
        with col_t:
            if idx == 0:
                st.caption("Valor total")
            st.markdown(f"**{formatar_moeda(tot_linha)}**")
        with col_del:
            if idx == 0:
                st.caption("")
            if st.button("🗑️", key=f"{prefixo_widget}_del_{idx}", disabled=len(itens_atuais) <= 1, help="Remover linha"):
                itens_atuais.pop(idx)
                st.rerun()

        itens_editados.append({
            "servico": srv_val,
            "valor_unitario": float(unit_val),
            "quantidade": float(qtd_val),
            "valor_total": tot_linha,
        })

    st.session_state[chave_sessao] = itens_editados
    itens_validos = _normalizar_itens(itens_editados)
    return itens_validos, calcular_total_itens(itens_validos)


def _exibir_pre_visualizacao(
    data_fmt,
    razao_social,
    cnpj_fmt,
    solicitante,
    contatos,
    itens_validos,
    cond_pag,
    obs_art,
    status_proposta="Aguardando Aceite",
    data_aceite="",
    chave_expander="exp_txt_prop",
):
    texto_gerado = montar_texto_proposta(
        data_fmt,
        razao_social,
        cnpj_fmt,
        solicitante,
        contatos,
        itens_validos,
        cond_pag,
        obs_art,
        status_proposta=status_proposta,
    )
    html_preview = montar_html_proposta(
        data_fmt,
        razao_social,
        cnpj_fmt,
        solicitante,
        contatos,
        itens_validos,
        cond_pag,
        obs_art,
        status_proposta=status_proposta,
        data_aceite=data_aceite,
        para_impressao_tela=True,
    )
    st.subheader("Pré-visualização da Proposta")
    st.components.v1.html(html_preview, height=780, scrolling=True)

    with st.expander("📋 Versão em Texto Simples (para copiar e colar)", expanded=False, key=chave_expander):
        st.code(texto_gerado, language="text")


def _renderizar_tela_edicao_proposta(proposta_id, pode_editar, pode_excluir):
    conn = conectar_db()
    df_p = pd.read_sql_query("""
        SELECT p.*, c.razao_social, c.cnpj
        FROM propostas p
        JOIN clientes c ON p.cliente_id = c.id
        WHERE p.id = ?
    """, conn, params=(int(proposta_id),))
    conn.close()

    if df_p.empty:
        st.error("Proposta não localizada.")
        _resetar_selecao_tabela_propostas()
        return

    row = dict(df_p.iloc[0])
    status_atual = row.get("status_proposta") or "Aguardando Aceite"
    data_aceite_atual = row.get("data_aceite") or ""
    token_p = str(row.get("token_aceite") or "").strip()
    cnpj_fmt = formatar_cnpj_exibicao(row["cnpj"])

    st.markdown('<div id="ancora_editor_proposta"></div>', unsafe_allow_html=True)
    st.divider()
    with st.container(border=True):
        col_t, col_voltar = st.columns([3.5, 1.0])
        with col_t:
            st.subheader(f"📄 Proposta #{row['id']} — {row['razao_social']} ({status_atual})")
        with col_voltar:
            st.write("")
            if st.button("Fechar", key="btn_fechar_edicao_prop", use_container_width=True):
                st.session_state.pop(f"itens_edit_prop_{proposta_id}", None)
                _resetar_selecao_tabela_propostas()
                st.rerun()

        if token_p:
            st.markdown("**Link de Aceite Comercial:**")
            st.code(f"http://localhost:8501/?proposta={token_p}", language="text")

        if status_atual == "Aprovada":
            st.info(
                "Esta proposta está **Aprovada** e não pode ser alterada diretamente. "
                "Você pode **Cancelar** ou **Duplicar para Nova Proposta**."
            )
            c_ap1, c_ap2, _ = st.columns([1.4, 1.8, 1.4])
            with c_ap1:
                if st.button(
                    "🚫 Cancelar Proposta",
                    key="btn_cancelar_prop_aprovada",
                    use_container_width=True,
                    disabled=not (pode_editar or pode_excluir),
                ):
                    conn = conectar_db()
                    conn.execute(
                        "UPDATE propostas SET status_proposta = 'Cancelada' WHERE id = ?",
                        (int(proposta_id),)
                    )
                    conn.commit()
                    conn.close()
                    _resetar_selecao_tabela_propostas()
                    st.session_state.msg_sucesso_proposta = f"Proposta #{proposta_id} marcada como Cancelada."
                    st.rerun()
            with c_ap2:
                if st.button(
                    "📋 Duplicar p/ Nova Proposta",
                    key="btn_duplicar_prop_aprovada",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.rascunho_duplicada = {
                        "cliente_id": int(row["cliente_id"]),
                        "solicitante": row.get("solicitante") or "",
                        "contatos": row.get("contatos") or "",
                        "condicoes_pagamento": row.get("condicoes_pagamento") or "",
                        "observacoes_art": row.get("observacoes_art") or "",
                        "itens": _extrair_itens_de_linha_db(row),
                    }
                    st.session_state.exibir_form_nova_proposta = True
                    st.session_state.focar_nova_proposta = True
                    st.session_state.pop("prop_nova_itens", None)
                    _resetar_selecao_tabela_propostas()
                    st.session_state.msg_sucesso_proposta = (
                        f"Dados da proposta aprovada #{proposta_id} carregados para emitir uma nova proposta."
                    )
                    st.rerun()

            itens_aprov = _extrair_itens_de_linha_db(row)
            _exibir_pre_visualizacao(
                data_fmt=row.get("data_emissao") or "",
                razao_social=row.get("razao_social") or "",
                cnpj_fmt=cnpj_fmt,
                solicitante=row.get("solicitante") or "",
                contatos=row.get("contatos") or "",
                itens_validos=itens_aprov,
                cond_pag=row.get("condicoes_pagamento") or "",
                obs_art=row.get("observacoes_art") or "",
                status_proposta=status_atual,
                data_aceite=data_aceite_atual,
                chave_expander=f"exp_txt_aprov_{proposta_id}",
            )
            return

        if not pode_editar:
            st.error("Seu perfil não tem permissão para alterar propostas já emitidas.")
            return

        dt_obj = converter_str_data(row.get("data_emissao")) or date.today()
        col_dt, col_sol, col_cnt, col_st = st.columns([1.1, 1.6, 1.8, 1.2])
        with col_dt:
            dt_emissao = st.date_input("Data da Proposta *", value=dt_obj, key=f"ed_dt_prop_{proposta_id}")
        with col_sol:
            solicitante = st.text_input("Solicitante *", value=row.get("solicitante") or "", key=f"ed_sol_prop_{proposta_id}")
        with col_cnt:
            contatos = st.text_input("Contatos", value=row.get("contatos") or "", key=f"ed_cnt_prop_{proposta_id}")
        with col_st:
            opcoes_st = ["Aguardando Aceite", "Aprovada", "Recusada", "Cancelada"]
            idx_st = opcoes_st.index(status_atual) if status_atual in opcoes_st else 0
            novo_status = st.selectbox("Status da Proposta", opcoes_st, index=idx_st, key=f"ed_st_prop_{proposta_id}")

        chave_edit = f"itens_edit_prop_{proposta_id}"
        _preparar_itens_formulario(chave_edit, itens_iniciais=_extrair_itens_de_linha_db(row))
        itens_validos, valor_inv = _renderizar_editor_itens(chave_edit, f"ed_item_{proposta_id}")

        v1, v2 = st.columns([1.2, 2.5])
        with v1:
            st.metric("Investimento Total (R$)", formatar_moeda(valor_inv))
        with v2:
            cond_pag = st.text_input(
                "Condições de pagamento *",
                value=row.get("condicoes_pagamento") or "Entrada (50%) + 1x (30 dias) ou 10% de desconto à vista",
                key=f"ed_cond_prop_{proposta_id}"
            )

        obs_art = st.text_area(
            "Observações (Ex: ART / Responsabilidade Técnica)",
            value=row.get("observacoes_art") or "",
            height=80,
            key=f"ed_obs_prop_{proposta_id}"
        )

        data_fmt = dt_emissao.strftime("%d/%m/%Y")
        servicos_resumo_txt = "\n".join(
            [f"- {i['servico']} (Qtd: {i['quantidade']:g} x {formatar_moeda(i['valor_unitario'])})" for i in itens_validos]
        )
        data_aceite_previa = (
            data_aceite_atual or datetime.now().strftime("%d/%m/%Y às %H:%M")
            if novo_status == "Aprovada" else ""
        )
        texto_atualizado = montar_texto_proposta(
            data_fmt,
            row["razao_social"],
            cnpj_fmt,
            solicitante,
            contatos,
            itens_validos,
            cond_pag,
            obs_art,
            status_proposta=novo_status,
        )

        if st.button("💾 Salvar Alterações da Proposta", type="primary", use_container_width=True, key=f"btn_save_ed_prop_{proposta_id}"):
            if not solicitante.strip() or not itens_validos:
                st.error("Preencha o Solicitante e ao menos um serviço.")
            else:
                conn = conectar_db()
                conn.execute("""
                    UPDATE propostas
                    SET data_emissao = ?, solicitante = ?, contatos = ?,
                        servicos = ?, itens_json = ?, valor_investimento = ?,
                        condicoes_pagamento = ?, observacoes_art = ?,
                        status_proposta = ?, data_aceite = ?, texto_proposta = ?
                    WHERE id = ?
                """, (
                    data_fmt,
                    solicitante.strip(),
                    contatos.strip(),
                    servicos_resumo_txt,
                    json.dumps(itens_validos, ensure_ascii=False),
                    float(valor_inv),
                    cond_pag.strip(),
                    obs_art.strip(),
                    novo_status,
                    data_aceite_previa,
                    texto_atualizado,
                    int(proposta_id),
                ))
                conn.commit()
                conn.close()
                st.session_state.pop(chave_edit, None)
                _resetar_selecao_tabela_propostas()
                st.session_state.msg_sucesso_proposta = f"✅ Proposta #{proposta_id} atualizada com sucesso!"
                st.rerun()

        _exibir_pre_visualizacao(
            data_fmt=data_fmt,
            razao_social=row.get("razao_social") or "",
            cnpj_fmt=cnpj_fmt,
            solicitante=solicitante,
            contatos=contatos,
            itens_validos=itens_validos,
            cond_pag=cond_pag,
            obs_art=obs_art,
            status_proposta=novo_status,
            data_aceite=data_aceite_previa,
            chave_expander=f"exp_txt_edit_{proposta_id}",
        )


def renderizar_tela_propostas():
    st.markdown(
        """
        <style>
        @media print {
            section[data-testid="stSidebar"],
            header[data-testid="stHeader"],
            div[data-testid="stToolbar"],
            .no-print-crm {
                display: none !important;
            }
            .block-container {
                padding: 0 !important;
                max-width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📄 Propostas Comerciais")

    perms = _perms_usuario()
    pode_editar = perms.get("pode_editar", False)
    pode_excluir = perms.get("pode_excluir", False)

    if "msg_sucesso_proposta" in st.session_state:
        st.success(st.session_state.msg_sucesso_proposta)
        st.toast(st.session_state.msg_sucesso_proposta)
        del st.session_state.msg_sucesso_proposta

    if "exibir_form_nova_proposta" not in st.session_state:
        st.session_state.exibir_form_nova_proposta = False

    if "proposta_selecionada_id" not in st.session_state:
        st.session_state.proposta_selecionada_id = None

    if "tabela_propostas_nonce" not in st.session_state:
        st.session_state.tabela_propostas_nonce = 0

    conn = conectar_db()
    df_clientes = pd.read_sql_query("""
        SELECT id, cnpj, razao_social, responsavel_pf, telefone, email, valor_estimado
        FROM clientes
        ORDER BY razao_social
    """, conn)

    df_hist_all = pd.read_sql_query("""
        SELECT p.id as ID, p.cliente_id, p.data_emissao as 'Data', c.razao_social as 'Cliente',
               p.solicitante as 'Solicitante', p.contatos as 'Contatos',
               p.servicos as 'Serviços', p.itens_json,
               p.valor_investimento as 'Investimento (R$)',
               p.condicoes_pagamento as 'Condições',
               p.observacoes_art as 'Observações',
               p.status_proposta as 'Status', p.data_aceite as 'Data do Aceite',
               p.token_aceite as 'Token'
        FROM propostas p
        JOIN clientes c ON p.cliente_id = c.id
        ORDER BY p.id DESC
    """, conn)
    conn.close()

    with st.container(border=True):
        col_filtro, col_btn_nova = st.columns([2.8, 1.2])
        with col_filtro:
            filtro_status = st.selectbox(
                "Filtrar propostas emitidas por:",
                ["Em Aberto (Aguardando Aceite)", "Aceitas (Aprovadas)", "Recusadas", "Canceladas", "Todas"],
                index=0,
                key="filtro_status_propostas"
            )
        with col_btn_nova:
            st.write("")
            if st.button("➕ Nova Proposta", type="primary", use_container_width=True, key="btn_abrir_nova_prop"):
                st.session_state.proposta_selecionada_id = None
                st.session_state.exibir_form_nova_proposta = True
                st.session_state.focar_nova_proposta = True
                st.rerun()

        if df_hist_all.empty:
            st.info("Nenhuma proposta emitida até o momento. Clique em 'Nova Proposta' para emitir a primeira.")
        else:
            df_work = df_hist_all.copy()
            df_work["Status"] = df_work["Status"].fillna("Aguardando Aceite")

            if filtro_status == "Em Aberto (Aguardando Aceite)":
                df_filtrado = df_work[df_work["Status"] == "Aguardando Aceite"]
            elif filtro_status == "Aceitas (Aprovadas)":
                df_filtrado = df_work[df_work["Status"] == "Aprovada"]
            elif filtro_status == "Recusadas":
                df_filtrado = df_work[df_work["Status"] == "Recusada"]
            elif filtro_status == "Canceladas":
                df_filtrado = df_work[df_work["Status"] == "Cancelada"]
            else:
                df_filtrado = df_work

            if df_filtrado.empty:
                st.info(f"Nenhuma proposta encontrada para o filtro: '{filtro_status}'.")
            else:
                st.caption("Clique em uma proposta na tabela para abrir a tela de emissão/edição.")
                df_tab_prop = df_filtrado[[
                    "ID", "Data", "Cliente", "Solicitante", "Investimento (R$)", "Status", "Data do Aceite"
                ]].reset_index(drop=True)

                nonce_p = int(st.session_state.get("tabela_propostas_nonce", 0))
                evento_p = st.dataframe(
                    df_tab_prop,
                    use_container_width=True,
                    hide_index=True,
                    height=380,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"tabela_propostas_emitidas_{nonce_p}"
                )

                linhas_p = evento_p.selection.rows if (evento_p and evento_p.selection) else []
                if linhas_p and len(df_tab_prop) > 0:
                    idx_p = int(linhas_p[0])
                    if 0 <= idx_p < len(df_tab_prop):
                        id_tab = int(df_tab_prop.iloc[idx_p]["ID"])
                        if st.session_state.get("proposta_selecionada_id") != id_tab:
                            st.session_state.proposta_selecionada_id = id_tab
                            st.session_state.exibir_form_nova_proposta = False
                            st.session_state.focar_nova_proposta = True

    if st.session_state.get("proposta_selecionada_id"):
        _renderizar_tela_edicao_proposta(st.session_state.proposta_selecionada_id, pode_editar, pode_excluir)
        if st.session_state.get("focar_nova_proposta"):
            st.session_state.focar_nova_proposta = False
            _focar_primeiro_campo_nova_proposta()
        return

    if not st.session_state.exibir_form_nova_proposta:
        return

    if df_clientes.empty:
        st.warning("Cadastre pelo menos uma empresa na aba de Clientes antes de emitir propostas.")
        return

    rascunho_dup = st.session_state.get("rascunho_duplicada")
    lista_clientes = list(df_clientes.iterrows())
    idx_cli_padrao = 0
    if rascunho_dup:
        for i_pos, (_, r_cli) in enumerate(lista_clientes):
            if int(r_cli["id"]) == int(rascunho_dup.get("cliente_id", -1)):
                idx_cli_padrao = i_pos
                break

    opcoes_cli = {
        f"{r['razao_social']} | CNPJ: {formatar_cnpj_exibicao(r['cnpj'])}": dict(r)
        for _, r in df_clientes.iterrows()
    }
    chaves_cli = list(opcoes_cli.keys())

    st.markdown('<div id="ancora_editor_proposta"></div>', unsafe_allow_html=True)
    st.divider()
    with st.container(border=True):
        col_top_n, col_fechar_n = st.columns([3.5, 1.0])
        with col_top_n:
            st.subheader("Nova Proposta Comercial")
        with col_fechar_n:
            st.write("")
            if st.button("Fechar", key="btn_fechar_nova_prop_form", use_container_width=True):
                st.session_state.exibir_form_nova_proposta = False
                st.session_state.focar_nova_proposta = False
                st.rerun()

        if rascunho_dup:
            st.info("Iniciando nova proposta com base em proposta aprovada anterior. Revise os dados e clique em **Salvar Proposta**.")

        col_cli, col_dt = st.columns([2.6, 1.2])
        with col_cli:
            cli_lbl = st.selectbox("Selecione o Cliente *", chaves_cli, index=idx_cli_padrao, key="nova_prop_cli")
        cli_row = opcoes_cli[cli_lbl]
        cid = int(cli_row["id"])

        with col_dt:
            dt_emissao = st.date_input("Data da Proposta *", value=date.today(), key="nova_prop_dt")

        resp_cliente = (cli_row.get("responsavel_pf") or "").strip()
        contatos_cliente = _montar_contatos_cliente(cli_row)

        if rascunho_dup and st.session_state.get("nova_prop_cliente_sync") != cid:
            st.session_state.nova_prop_cliente_sync = cid
            st.session_state.nova_prop_sol = rascunho_dup.get("solicitante") or resp_cliente
            st.session_state.nova_prop_cnt = rascunho_dup.get("contatos") or contatos_cliente
        elif st.session_state.get("nova_prop_cliente_sync") != cid:
            st.session_state.nova_prop_cliente_sync = cid
            st.session_state.nova_prop_sol = resp_cliente
            st.session_state.nova_prop_cnt = contatos_cliente

        if "nova_prop_sol" not in st.session_state:
            st.session_state.nova_prop_sol = resp_cliente
        if "nova_prop_cnt" not in st.session_state:
            st.session_state.nova_prop_cnt = contatos_cliente

        cond_ini = (
            rascunho_dup["condicoes_pagamento"]
            if (rascunho_dup and rascunho_dup.get("condicoes_pagamento"))
            else "Entrada (50%) + 1x (30 dias) ou 10% de desconto à vista"
        )
        obs_ini = (
            rascunho_dup["observacoes_art"]
            if (rascunho_dup and "observacoes_art" in rascunho_dup)
            else (
                "O pagamento da ART (Anotação de Responsabilidade Técnica) será por conta "
                "do contratante. Estimativa de valor: R$ 150,00 (cento e cinquenta reais)."
            )
        )

        c1, c2 = st.columns(2)
        with c1:
            solicitante = st.text_input("Solicitante (Responsável do Cliente) *", key="nova_prop_sol")
        with c2:
            contatos = st.text_input("Contatos (Responsável / Telefone / E-mail)", key="nova_prop_cnt")

        chave_nova = "prop_nova_itens"
        if st.session_state.get("prop_nova_ultimo_cliente") != cid and not rascunho_dup:
            st.session_state.prop_nova_ultimo_cliente = cid
            st.session_state.pop(chave_nova, None)
        elif rascunho_dup and chave_nova not in st.session_state:
            st.session_state.prop_nova_ultimo_cliente = cid
            _preparar_itens_formulario(chave_nova, itens_iniciais=rascunho_dup.get("itens"))
        else:
            st.session_state.prop_nova_ultimo_cliente = cid

        _preparar_itens_formulario(
            chave_nova,
            itens_iniciais=rascunho_dup.get("itens") if rascunho_dup else None,
            valor_padrao=cli_row.get("valor_estimado"),
        )
        itens_validos, valor_inv = _renderizar_editor_itens(chave_nova, f"nova_item_{cid}")

        v1, v2 = st.columns([1.2, 2.5])
        with v1:
            st.metric("Investimento Total (R$)", formatar_moeda(valor_inv))
        with v2:
            cond_pag = st.text_input("Condições de pagamento *", value=cond_ini, key="nova_prop_cond")

        obs_art = st.text_area("Observações (Ex: ART / Responsabilidade Técnica)", value=obs_ini, height=80, key="nova_prop_obs")

        atualizar_funil = st.checkbox(
            "Atualizar cliente para '3. Proposta / Tabela Enviada' e salvar valor total no cadastro",
            value=True,
            key="nova_prop_funil"
        )

        emitente = (
            st.session_state.get("nome_usuario")
            or st.session_state.get("usuario_atual")
            or "Administrador"
        )
        data_fmt = dt_emissao.strftime("%d/%m/%Y")
        cnpj_fmt = formatar_cnpj_exibicao(cli_row["cnpj"])
        servicos_resumo_txt = "\n".join(
            [f"- {i['servico']} (Qtd: {i['quantidade']:g} x {formatar_moeda(i['valor_unitario'])})" for i in itens_validos]
        )

        texto_gerado = montar_texto_proposta(
            data_fmt,
            cli_row["razao_social"],
            cnpj_fmt,
            solicitante,
            contatos,
            itens_validos,
            cond_pag,
            obs_art,
        )

        base_nome = "".join(
            [ch if ch.isalnum() else "_" for ch in str(cli_row["razao_social"])]
        ).strip("_")
        sucesso_data = dt_emissao.strftime("%Y%m%d")

        html_arquivo = montar_html_proposta(
            data_fmt,
            cli_row["razao_social"],
            cnpj_fmt,
            solicitante,
            contatos,
            itens_validos,
            cond_pag,
            obs_art,
            para_impressao_tela=False,
            exibir_botao_imprimir=True,
        )

        col_btn_save, col_btn_html, col_btn_txt = st.columns([1.4, 1.3, 1.1])
        with col_btn_save:
            if st.button("💾 Salvar Proposta", type="primary", use_container_width=True, key="btn_salvar_nova_prop"):
                if not solicitante.strip() or not itens_validos:
                    st.error("Preencha o Solicitante e ao menos um serviço no escopo.")
                else:
                    token_novo = uuid.uuid4().hex[:16]
                    conn = conectar_db()
                    conn.execute("""
                        INSERT INTO propostas (
                            cliente_id, data_emissao, solicitante, contatos,
                            servicos, itens_json, valor_investimento, condicoes_pagamento,
                            observacoes_art, responsavel_emissao, status_proposta,
                            token_aceite, texto_proposta
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        cid,
                        data_fmt,
                        solicitante.strip(),
                        contatos.strip(),
                        servicos_resumo_txt,
                        json.dumps(itens_validos, ensure_ascii=False),
                        float(valor_inv),
                        cond_pag.strip(),
                        obs_art.strip(),
                        emitente,
                        "Aguardando Aceite",
                        token_novo,
                        texto_gerado,
                    ))
                    if atualizar_funil:
                        conn.execute("""
                            UPDATE clientes
                            SET etapa_funil = '3. Proposta / Tabela Enviada', valor_estimado = ?
                            WHERE id = ?
                        """, (float(valor_inv), cid))
                    conn.commit()
                    conn.close()
                    st.session_state.exibir_form_nova_proposta = False
                    st.session_state.focar_nova_proposta = False
                    st.session_state.pop("rascunho_duplicada", None)
                    st.session_state.pop(chave_nova, None)
                    _resetar_selecao_tabela_propostas()
                    st.session_state.msg_sucesso_proposta = (
                        f"✅ Proposta emitida e salva para '{cli_row['razao_social']}'! Link de aceite gerado."
                    )
                    st.rerun()

        with col_btn_html:
            st.download_button(
                "🖨️ Baixar p/ Imprimir (HTML/PDF)",
                data=html_arquivo.encode("utf-8"),
                file_name=f"Proposta_{base_nome}_{sucesso_data}.html",
                mime="text/html",
                use_container_width=True,
                key="dl_nova_prop_html"
            )

        with col_btn_txt:
            st.download_button(
                "⬇️ Baixar (.txt)",
                data=texto_gerado.encode("utf-8"),
                file_name=f"Proposta_{base_nome}_{sucesso_data}.txt",
                mime="text/plain",
                use_container_width=True,
                key="dl_nova_prop_txt"
            )

    _exibir_pre_visualizacao(
        data_fmt=data_fmt,
        razao_social=cli_row["razao_social"],
        cnpj_fmt=cnpj_fmt,
        solicitante=solicitante,
        contatos=contatos,
        itens_validos=itens_validos,
        cond_pag=cond_pag,
        obs_art=obs_art,
        status_proposta="Aguardando Aceite",
        chave_expander="exp_txt_nova_prop",
    )

    if st.session_state.get("focar_nova_proposta"):
        st.session_state.focar_nova_proposta = False
        _focar_primeiro_campo_nova_proposta()