import os
import sys
import json
import sqlite3
import py_compile
from datetime import date, timedelta
import pandas as pd

# Garante que o diretório atual esteja no sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

ARQUIVOS_PROJETO = [
    "app.py",
    "database.py",
    "utils.py",
    "componentes.py",
    "tela_login.py",
    "tela_clientes.py",
    "tela_funil.py",
    "tela_atividades.py",
    "tela_agenda.py",
    "tela_propostas.py",
    "tela_checklist.py",
]


def testar_sintaxe_arquivos():
    print("1. Verificando sintaxe de todos os módulos .py...")
    for arq in ARQUIVOS_PROJETO:
        caminho = os.path.join(BASE_DIR, arq)
        assert os.path.exists(caminho), f"Arquivo não encontrado: {arq}"
        py_compile.compile(caminho, doraise=True)
    print("   [OK] Todos os módulos compilaram sem erros de sintaxe.")


def testar_utils():
    print("2. Verificando funções de utils.py...")
    import utils

    assert utils.limpar_numeros("12.345.678/0001-99") == "12345678000199"
    assert utils.formatar_moeda(1250.5) == "R$ 1.250,50"
    assert utils.validar_cnpj_algoritmo("11222333000181") is True
    assert utils.validar_cnpj_algoritmo("11111111111111") is False

    dados_fake = {
        "cnae_fiscal": 8630503,
        "cnae_fiscal_descricao": "Atividade médica ambulatorial restrita a consultas",
        "cnaes_secundarios": [
            {"codigo": 8640202, "descricao": "Laboratórios clínicos"}
        ],
    }
    prin, sec = utils.formatar_cnaes_api(dados_fake)
    assert "8630-5/03" in prin
    assert "8640-2/02" in sec

    serie_tempos = pd.Series(["01h 30m", "00h 45m"])
    assert utils.somar_tempos_formatados(serie_tempos) == "02h 15m"

    hoje_str = date.today().strftime("%d/%m/%Y")
    ontem_str = (date.today() - timedelta(days=2)).strftime("%d/%m/%Y")
    amanha_str = (date.today() + timedelta(days=5)).strftime("%d/%m/%Y")

    assert utils.avaliar_status_followup(hoje_str)[0] == "HOJE"
    assert utils.avaliar_status_followup(ontem_str)[0] == "ATRASADO"
    assert utils.avaliar_status_followup(amanha_str)[0] == "FUTURO"
    assert utils.avaliar_status_followup("")[0] == "SEM_DATA"

    print("   [OK] Funções utilitárias, CNAEs, tempos e follow-ups validados.")


def testar_banco_em_memoria():
    print("3. Verificando estrutura do banco, migrações e operações CRUD em memória...")
    import database

    # Redireciona temporariamente conectar_db para banco em memória (:memory:)
    conn_mem = sqlite3.connect(":memory:")
    conn_mem.execute("PRAGMA foreign_keys = 1")

    class ConexaoNaoFechavel:
        def __init__(self, inner):
            self._inner = inner

        def close(self):
            # Mantém :memory: vivo durante os testes da suíte
            pass

        def __getattr__(self, name):
            return getattr(self._inner, name)

    conectar_original = database.conectar_db
    database.conectar_db = lambda: ConexaoNaoFechavel(conn_mem)

    try:
        database.inicializar_db()

        cur = conn_mem.cursor()
        tabelas = {
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        esperadas = {
            "usuarios",
            "clientes",
            "atividades",
            "propostas",
            "checklists_visita",
        }
        assert esperadas.issubset(tabelas), f"Tabelas ausentes: {esperadas - tabelas}"

        # Confere usuário admin padrão
        admin_row = cur.execute(
            "SELECT usuario, perfil, ativo FROM usuarios WHERE usuario = 'admin'"
        ).fetchone()
        assert admin_row is not None and admin_row[0] == "admin" and admin_row[2] == 1

        # Insere cliente de teste
        cur.execute(
            """
            INSERT INTO clientes (
                cnpj, razao_social, nome_fantasia, responsavel_pf,
                telefone, email, cidade, uf, categoria, cnae_principal,
                etapa_funil, valor_estimado, servico_interesse, proximo_contato
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "11222333000181",
                "Empresa Teste SST Ltda",
                "Teste SST",
                "Carlos Silva",
                "(54) 99999-0000",
                "contato@testesst.com.br",
                "Bento Gonçalves",
                "RS",
                "Prospecto",
                "8630-5/03 - Atividade médica",
                "1. Prospecção / Lead",
                1200.0,
                database.OPCOES_SERVICOS[0],
                date.today().strftime("%d/%m/%Y"),
            ),
        )
        cliente_id = cur.lastrowid

        # Insere atividade vinculada
        cur.execute(
            """
            INSERT INTO atividades (
                cliente_id, data, horario, hora_inicio, hora_fim,
                tempo_total, modalidade, descricao, atendente
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente_id,
                date.today().strftime("%d/%m/%Y"),
                "09:00 às 10:30",
                "09:00",
                "10:30",
                "01h 30m",
                "Reunião Online",
                "Apresentação inicial do CRM e NR-01.",
                "Administrador Geral",
            ),
        )

        # Insere proposta vinculada
        cur.execute(
            """
            INSERT INTO propostas (
                cliente_id, data_emissao, solicitante, contatos,
                servicos, valor_investimento, condicoes_pagamento,
                observacoes_art, responsavel_emissao, texto_proposta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente_id,
                date.today().strftime("%d/%m/%Y"),
                "Carlos Silva",
                "(54) 99999-0000",
                "PGR + PCMSO",
                1200.0,
                "À vista",
                "ART por conta do contratante.",
                "Administrador Geral",
                "PROPOSTA COMERCIAL - TESTE",
            ),
        )

        # Insere checklist vinculado
        respostas_teste = {"1.1": "Sim", "1.2": "Não", "1.3": "Não aplicável"}
        cur.execute(
            """
            INSERT INTO checklists_visita (
                cliente_id, data_visita, responsavel_tecnico,
                respostas_json, qtd_sim, qtd_nao, qtd_na, observacoes_gerais
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente_id,
                date.today().strftime("%d/%m/%Y"),
                "Eng. Responsável",
                json.dumps(respostas_teste, ensure_ascii=False),
                1,
                1,
                1,
                "Sem observações adicionais.",
            ),
        )
        conn_mem.commit()

        qtd_ativ = cur.execute("SELECT COUNT(*) FROM atividades").fetchone()[0]
        qtd_prop = cur.execute("SELECT COUNT(*) FROM propostas").fetchone()[0]
        qtd_chk = cur.execute("SELECT COUNT(*) FROM checklists_visita").fetchone()[0]
        assert qtd_ativ == 1 and qtd_prop == 1 and qtd_chk == 1

    finally:
        database.conectar_db = conectar_original
        conn_mem.close()

    print("   [OK] Banco em memória, tabelas, chaves estrangeiras e registros testados com sucesso.")


def testar_propostas_e_checklist():
    print("4. Verificando formatação de proposta e itens de checklist...")
    import tela_propostas
    import database

    cnpj_fmt = tela_propostas.formatar_cnpj_exibicao("11222333000181")
    assert cnpj_fmt == "11.222.333/0001-81"

    texto_prop = tela_propostas.montar_texto_proposta(
        data_emissao_str="18/11/2026",
        razao_social="SegSerra Teste Ltda",
        cnpj_fmt=cnpj_fmt,
        solicitante="Pedro",
        contatos="(54) 3055-3009",
        servicos_texto="- PGR e PCMSO",
        valor_investimento=900.0,
        condicoes_pag="À vista",
        obs_art="ART estimada em R$ 150,00.",
    )
    assert "PROPOSTA COMERCIAL" in texto_prop
    assert "Bento Gonçalves/RS, 18/11/2026" in texto_prop
    assert "R$ 900,00" in texto_prop

    assert len(database.ITENS_CHECKLIST_SST) > 40
    print("   [OK] Geração de proposta e catálogo de itens do checklist validados.")


def executar_todos_os_testes():
    print("=" * 60)
    print("INICIANDO ROTINA DE TESTES AUTOMATIZADOS - CRM SEGSERRA")
    print("=" * 60)
    testar_sintaxe_arquivos()
    testar_utils()
    testar_banco_em_memoria()
    testar_propostas_e_checklist()
    print("=" * 60)
    print("RESULTADO FINAL: TODOS OS TESTES PASSARAM COM SUCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    executar_todos_os_testes()