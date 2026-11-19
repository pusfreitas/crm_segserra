import os
import re
import requests
from datetime import datetime, time, date
import streamlit as st


def limpar_numeros(texto):


def formatar_moeda(valor):
    try:
        val = float(valor or 0.0)
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def validar_cnpj_algoritmo(cnpj):
    cnpj = limpar_numeros(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    digito1 = 0 if (soma1 % 11) < 2 else 11 - (soma1 % 11)

    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    digito2 = 0 if (soma2 % 11) < 2 else 11 - (soma2 % 11)

    return cnpj[-2:] == f"{digito1}{digito2}"


def consultar_cep_api(cep):
    """Consulta endereço pelo CEP (8 dígitos). Retorna (dict_endereco, erro_str)."""
    cep_limpo = limpar_numeros(cep)
    if len(cep_limpo) != 8:
        return None, "Informe um CEP válido com 8 dígitos."

    headers = {
        "User-Agent": "Mozilla/5.0 SegSerra-CRM/1.0",
        "Accept": "application/json"
    }

    # 1. ViaCEP
    try:
        resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and not data.get("erro"):
                return {
                    "cep": formatar_cep(cep_limpo),
                    "logradouro": (data.get("logradouro") or "").strip(),
                    "complemento": (data.get("complemento") or "").strip(),
                    "bairro": (data.get("bairro") or "").strip(),
                    "cidade": (data.get("localidade") or "").strip(),
                    "uf": (data.get("uf") or "").strip().upper(),
                }, None
    except Exception:
        pass

    # 2. BrasilAPI CEP (fallback)
    try:
        resp_b = requests.get(f"https://brasilapi.com.br/api/cep/v1/{cep_limpo}", headers=headers, timeout=6)
        if resp_b.status_code == 200:
            d = resp_b.json()
            if isinstance(d, dict) and d.get("cep"):
                return {
                    "cep": formatar_cep(cep_limpo),
                    "logradouro": (d.get("street") or "").strip(),
                    "complemento": "",
                    "bairro": (d.get("neighborhood") or "").strip(),
                    "cidade": (d.get("city") or "").strip(),
                    "uf": (d.get("state") or "").strip().upper(),
                }, None
    except Exception:
        pass

    return None, "CEP não localizado automaticamente. Preencha o endereço manualmente."


def consultar_cnpj_api(cnpj):
    cnpj_limpo = limpar_numeros(cnpj)
    try:
        if response.status_code == 200:
            return response.json(), None
        elif response.status_code == 404:
            return None, "CNPJ não encontrado na base da Receita Federal."
            return None, f"Erro na consulta (Status {response.status_code})."
    except Exception:
        pass

    url_minha_receita = f"https://minhareceita.org/{cnpj_limpo}"
    try:
        resp_alt = requests.get(url_minha_receita, headers=headers_padrao, timeout=10)
        if resp_alt.status_code == 200:
            d = resp_alt.json()
            cnae_sec_formatados = []
            for item in (d.get("cnaes_secundarios") or []):
                if isinstance(item, dict):
                    cnae_sec_formatados.append({
                        "codigo": item.get("codigo"),
                        "descricao": item.get("descricao")
                    })

            return {
                "razao_social": d.get("razao_social", ""),
                "nome_fantasia": d.get("nome_fantasia", ""),
                "ddd_telefone_1": d.get("ddd_telefone_1", ""),
                "email": d.get("email", ""),
                "cep": d.get("cep", ""),
                "descricao_tipo_de_logradouro": "",
                "logradouro": d.get("logradouro", ""),
                "numero": d.get("numero", ""),
                "complemento": d.get("complemento", ""),
                "bairro": d.get("bairro", ""),
                "municipio": d.get("municipio", ""),
                "uf": d.get("uf", ""),
                "cnae_fiscal": d.get("cnae_fiscal"),
                "cnae_fiscal_descricao": d.get("cnae_fiscal_descricao", ""),
                "cnaes_secundarios": cnae_sec_formatados
            }, None
        elif resp_alt.status_code == 429:
            return None, "Limite de consultas atingido (Status 429). Aguarde cerca de 1 minuto e tente novamente."
        elif resp_alt.status_code == 404:
            return None, "CNPJ não encontrado na base da Receita Federal."
        else:
            return None, f"Erro na consulta (Status {resp_alt.status_code})."
    except Exception as e:


def somar_tempos_formatados(serie_tempos):
    total_minutos = 0
    for t in serie_tempos.dropna():
        match = re.search(r'(\d+)h\s*(\d+)m', str(t))
        if match:
            total_minutos += int(match.group(1)) * 60 + int(match.group(2))
    horas = total_minutos // 60
    minutos = total_minutos % 60
    return f"{horas:02d}h {minutos:02d}m"


def converter_str_data(data_str):
    try:
        return datetime.strptime(str(data_str).strip(), "%d/%m/%Y").date()
    except Exception:
        return None


def converter_str_hora(hora_str, padrao=time(10, 0)):
    try:
        return datetime.strptime(str(hora_str).strip()[:5], "%H:%M").time()
    except Exception:
        return padrao


def avaliar_status_followup(data_str):
    dt = converter_str_data(data_str)
    if not dt:
        return "SEM_DATA", "⚪ Sem retorno agendado"
    hoje = date.today()
    dias = (dt - hoje).days
    if dias < 0:
        return "ATRASADO", f"🔴 Atrasado: {data_str} ({abs(dias)}d)"
    elif dias == 0:
        return "HOJE", f"🟡 Retornar HOJE ({data_str})"
    else:
        return "FUTURO", f"🟢 Próx. Contato: {data_str} (em {dias}d)"


    """Injeta o CSS oficial da SegSerra (Bree Serif + Paleta #2dd2cd) em todo o sistema."""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Bree+Serif&family=Inter:wght@400;500;600;700&display=swap');

            font-family: 'Bree Serif', serif !important;
            color: #0f5257 !important;
            letter-spacing: 0.3px;

            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;

            background-color: #ffffff;
            border: 1px solid #e2e8f0 !important;
            border-left: 4px solid #2dd2cd !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 12px rgba(15, 82, 87, 0.05);
            padding: 0.2rem;

            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-top: 3px solid #2dd2cd;
            border-radius: 10px;
            padding: 12px 16px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);

            background: linear-gradient(135deg, #2dd2cd 0%, #17b8b3 100%) !important;
            color: #06373a !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 6px rgba(45, 210, 205, 0.35);
            transition: all 0.2s ease-in-out;
            background: linear-gradient(135deg, #22bfb9 0%, #0f9692 100%) !important;
            color: #ffffff !important;
            transform: translateY(-1px);

            background-color: #0d2b30 !important;
            border-right: 3px solid #2dd2cd;
            color: #f1f5f9 !important;
            border-color: rgba(45, 210, 205, 0.25) !important;
            background-color: rgba(255, 255, 255, 0.08) !important;
            border: 1px solid rgba(45, 210, 205, 0.4) !important;
            color: #ffffff !important;
            border-radius: 8px !important;
            background-color: #2dd2cd !important;
            color: #06373a !important;
            font-weight: 700 !important;
        </style>
    """, unsafe_allow_html=True)


def renderizar_logo_segserra(centralizado=True, tema_escuro=False):
    """Exibe o arquivo logo.png (se existir na pasta) ou renderiza a logo oficial da SegSerra em SVG."""
    if os.path.exists("logo.png"):
        if centralizado:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                st.image("logo.png", use_container_width=True)
        else:
            st.image("logo.png", use_container_width=True)
        return

    cor_titulo = "#ffffff" if tema_escuro else "#1e293b"
    cor_sub = "#94a3b8" if tema_escuro else "#64748b"
    alinhamento = "center" if centralizado else "flex-start"

    st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: {alinhamento}; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <svg width="38" height="38" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="15" y="3" width="10" height="34" rx="3.5" fill="#2dd2cd"/>
                    <rect x="3" y="15" width="34" height="10" rx="3.5" fill="#2dd2cd"/>
                    <path d="M25 15L15 25" stroke="#0d9488" stroke-width="2" stroke-opacity="0.35"/>
                </svg>
                <span style="font-family: 'Bree Serif', serif; font-size: 32px; color: {cor_titulo}; line-height: 1; font-weight: normal;">
                    SegSerra
                </span>
            </div>
            <span style="font-family: 'Inter', sans-serif; font-size: 10.5px; color: {cor_sub}; letter-spacing: 1.4px; text-transform: uppercase; margin-top: 4px; font-weight: 600;">
                saúde e segurança do trabalho
            </span>
        </div>
    """, unsafe_allow_html=True)