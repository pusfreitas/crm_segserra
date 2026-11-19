import os
import sys
import json
import types
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def criar_mock_streamlit():
    """Cria um mock funcional mínimo do módulo streamlit para testar funções de tela sem abrir navegador."""
    st_mock = types.ModuleType("streamlit")

    class SessionStateDict(dict):
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError as exc:
                raise AttributeError(key) from exc

        def __setattr__(self, key, value):
            self[key] = value

    st_mock.session_state = SessionStateDict()
    st_mock.toast_mensagens = []

    def toast(msg):
        st_mock.toast_mensagens.append(msg)

    def noop(*args, **kwargs):
        return None

    def decorator_noop(*args, **kwargs):
        def wrapper(fn):
            return fn
        return wrapper

    st_mock.toast = toast
    st_mock.rerun = noop
    st_mock.cache_data = decorator_noop
    st_mock.cache_resource = decorator_noop
    st_mock.dialog = decorator_noop
    st_mock.markdown = noop
    st_mock.write = noop
    st_mock.error = noop
    st_mock.warning = noop
    st_mock.success = noop
    st_mock.info = noop
    return st_mock


class BancoTemporarioIsolado:
    """Cria um arquivo SQLite temporário isolado por teste, sem tocar no banco real do CRM."""

    def __init__(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db", prefix="teste_crm_")
        os.close(fd)

    def conectar(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = 1")
        return conn

    def limpar(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass


class TesteFuncionalCRM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.st_mock = criar_mock_streamlit()
        sys.modules["streamlit"] = cls.st_mock

        import database
        import utils
        import componentes
        import tela_login
        import tela_propostas
        import tela_agenda

        cls.database = database
        cls.utils = utils
        cls.componentes = componentes
        cls.tela_login = tela_login
        cls.tela_propostas = tela_propostas
        cls.tela_agenda = tela_agenda

    def setUp(self):
        self.banco = BancoTemporarioIsolado()
        self._conectar_original = self.database.conectar_db
        self.database.conectar_db = self.banco.conectar

        self.componentes.conectar_db = self.banco.conectar
        self.tela_login.conectar_db = self.banco.conectar
        self.tela_propostas.conectar_db = self.banco.conectar
        self.tela_agenda.conectar_db = self.banco.conectar

        self.st_mock.session_state.clear()
        self.st_mock.toast_mensagens.clear()
        self.database.inicializar_db()

    def tearDown(self):
        self.database.conectar_db = self._conectar_original
        self.banco.limpar()

    def _autenticar_sql(self, login_digitado, senha_digitada):
        """Executa a mesma lógica de verificação de credenciais da tela de login."""
        conn = self.database.conectar_db()
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT id, usuario, nome_completo, senha_hash, perfil, ativo
            FROM usuarios
            WHERE LOWER(usuario) = ?
            """,
            (login_digitado.strip().lower(),),
        ).fetchone()
        conn.close()

        if not row:
            return False, "Usuário ou senha incorretos!"
        uid, u_login, u_nome, u_hash, u_perfil, u_ativo = row
        if u_ativo == 0:
            return False, "Usuário inativo"
        if self.database.gerar_hash_senha(senha_digitada) != u_hash:
            return False, "Usuário ou senha incorretos!"

        self.st_mock.session_state.logado = True
        self.st_mock.session_state.usuario_id = uid
        self.st_mock.session_state.usuario_atual = u_login
        self.st_mock.session_state.nome_usuario = u_nome
        self.st_mock.session_state.perfil_usuario = u_perfil
        return True, "OK"

    def test_01_login_multiplos_usuarios_e_logout(self):
        ok, _ = self._autenticar_sql("admin", "1234")
        self.assertTrue(ok)
        self.assertEqual(self.st_mock.session_state.perfil_usuario, "Administrador")

        ok_err, _ = self._autenticar_sql("admin", "senha_errada")
        self.assertFalse(ok_err)

        conn = self.database.conectar_db()
        conn.execute(
            """
            INSERT INTO usuarios (usuario, nome_completo, senha_hash, perfil, ativo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "comercial.bg",
                "Ana Comercial",
                self.database.gerar_hash_senha("abc123"),
                "Comercial / Atendimento",
                1,
            ),
        )
        conn.execute(
            """
            INSERT INTO usuarios (usuario, nome_completo, senha_hash, perfil, ativo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "ex.colaborador",
                "Inativo Teste",
                self.database.gerar_hash_senha("9999"),
                "Comercial / Atendimento",
                0,
            ),
        )
        conn.commit()
        conn.close()

        ok_ana, _ = self._autenticar_sql("comercial.bg", "abc123")
        self.assertTrue(ok_ana)
        self.assertEqual(self.st_mock.session_state.nome_usuario, "Ana Comercial")

        ok_inativo, msg_inativo = self._autenticar_sql("ex.colaborador", "9999")
        self.assertFalse(ok_inativo)
        self.assertIn("inativo", msg_inativo.lower())

        self.st_mock.session_state.menu_pagina = "Emissão de Propostas"
        self.tela_login.realizar_logout()
        self.assertFalse(self.st_mock.session_state.logado)
        self.assertIsNone(self.st_mock.session_state.usuario_atual)
        self.assertEqual(
            self.st_mock.session_state.menu_pagina,
            "Clientes (Consulta e Cadastro)",
        )

    def test_02_cadastro_cliente_cnaes_categoria_e_regra_exclusao(self):
        retorno_api = {
            "cnae_fiscal": 8630503,
            "cnae_fiscal_descricao": "Atividade médica ambulatorial restrita a consultas",
            "cnaes_secundarios": [
                {"codigo": 8640202, "descricao": "Laboratórios clínicos"},
                {"codigo": 8599604, "descricao": "Treinamento em desenvolvimento profissional e gerencial"},
            ],
        }
        cnae_prin, cnaes_sec = self.utils.formatar_cnaes_api(retorno_api)
        self.assertIn("8630-5/03", cnae_prin)
        self.assertIn("8640-2/02", cnaes_sec)

        conn = self.database.conectar_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO clientes (
                cnpj, razao_social, nome_fantasia, responsavel_pf,
                telefone, email, cidade, uf, categoria, cnae_principal,
                cnaes_secundarios, etapa_funil, valor_estimado, servico_interesse, proximo_contato
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "11222333000181",
                "Moveis Serra Gaucha Ltda",
                "Moveis Serra",
                "Ricardo Pereira",
                "(54) 3451-1000",
                "rh@moveisserra.com.br",
                "Bento Gonçalves",
                "RS",
                "Mensalista",
                cnae_prin,
                cnaes_sec,
                "2. Diagnóstico / Visita Técnica",
                2400.0,
                self.database.OPCOES_SERVICOS[0],
                date.today().strftime("%d/%m/%Y"),
            ),
        )
        cliente_id = cur.lastrowid

        with self.assertRaises(sqlite3.IntegrityError):
            cur.execute(
                """
                INSERT INTO clientes (cnpj, razao_social, responsavel_pf)
                VALUES (?, ?, ?)
                """,
                ("11222333000181", "Duplicada Ltda", "Fulano"),
            )

        conn.commit()
        conn.close()

        self.componentes.ir_para_lancamento_cliente(cliente_id)
        self.assertEqual(self.st_mock.session_state.cliente_pre_selecionado_id, cliente_id)
        self.assertEqual(self.st_mock.session_state.menu_pagina, "Lançar Atividades")

        self.componentes.alterar_etapa_funil_rapido(
            cliente_id, "3. Proposta / Tabela Enviada"
        )

        conn = self.database.conectar_db()
        etapa_salva = conn.execute(
            "SELECT etapa_funil, categoria FROM clientes WHERE id = ?",
            (cliente_id,),
        ).fetchone()
        self.assertEqual(etapa_salva[0], "3. Proposta / Tabela Enviada")
        self.assertEqual(etapa_salva[1], "Mensalista")

        conn.execute(
            """
            INSERT INTO atividades (
                cliente_id, data, horario, hora_inicio, hora_fim,
                tempo_total, modalidade, descricao, atendente
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente_id,
                date.today().strftime("%d/%m/%Y"),
                "08:30 às 10:00",
                "08:30",
                "10:00",
                "01h 30m",
                "Presencial / Visita Técnica",
                "Levantamento de postos de trabalho e riscos.",
                "Ana Comercial",
            ),
        )
        conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.close()

    def test_03_agenda_followups_propostas_e_checklist(self):
        hoje = date.today()
        ontem = (hoje - timedelta(days=3)).strftime("%d/%m/%Y")
        hoje_str = hoje.strftime("%d/%m/%Y")
        futuro = (hoje + timedelta(days=4)).strftime("%d/%m/%Y")

        self.assertEqual(self.utils.avaliar_status_followup(ontem)[0], "ATRASADO")
        self.assertEqual(self.utils.avaliar_status_followup(hoje_str)[0], "HOJE")
        self.assertEqual(self.utils.avaliar_status_followup(futuro)[0], "FUTURO")
        self.assertEqual(self.utils.avaliar_status_followup("")[0], "SEM_DATA")

        conn = self.database.conectar_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO clientes (cnpj, razao_social, responsavel_pf, telefone, email, proximo_contato)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "22333444000192",
                "Metalurgica Vale dos Vinhedos Ltda",
                "Marcos Souza",
                "(54) 3055-8000",
                "marcos@metalurgicavale.com.br",
                ontem,
            ),
        )
        cid = cur.lastrowid
        conn.commit()
        conn.close()

        self.tela_agenda.reagendar_followup_rapido(cid, hoje)

        conn = self.database.conectar_db()
        nova_data = conn.execute(
            "SELECT proximo_contato FROM clientes WHERE id = ?", (cid,)
        ).fetchone()[0]
        self.assertEqual(nova_data, hoje_str)

        cnpj_fmt = self.tela_propostas.formatar_cnpj_exibicao("22333444000192")
        texto_prop = self.tela_propostas.montar_texto_proposta(
            data_emissao_str=hoje_str,
            razao_social="Metalurgica Vale dos Vinhedos Ltda",
            cnpj_fmt=cnpj_fmt,
            solicitante="Marcos Souza",
            contatos="marcos@metalurgicavale.com.br / (54) 3055-8000",
            servicos_texto="- PGR, PCMSO e LTCAT (validade 12 meses)",
            valor_investimento=1500.0,
            condicoes_pag="Entrada 50% + 30 dias",
            obs_art="ART por conta do contratante.",
        )
        conn.execute(
            """
            INSERT INTO propostas (
                cliente_id, data_emissao, solicitante, contatos,
                servicos, valor_investimento, condicoes_pagamento,
                observacoes_art, responsavel_emissao, texto_proposta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                hoje_str,
                "Marcos Souza",
                "marcos@metalurgicavale.com.br",
                "- PGR, PCMSO e LTCAT",
                1500.0,
                "Entrada 50% + 30 dias",
                "ART por conta do contratante.",
                "Administrador Geral",
                texto_prop,
            ),
        )

        respostas = {
            cod: ("Não" if idx in (0, 2) else "Sim")
            for idx, (cod, _) in enumerate(self.database.ITENS_CHECKLIST_SST)
        }
        qtd_sim = sum(1 for v in respostas.values() if v == "Sim")
        qtd_nao = sum(1 for v in respostas.values() if v == "Não")
        self.assertEqual(qtd_nao, 2)
        self.assertEqual(qtd_sim, len(self.database.ITENS_CHECKLIST_SST) - 2)

        conn.execute(
            """
            INSERT INTO checklists_visita (
                cliente_id, data_visita, responsavel_tecnico,
                respostas_json, qtd_sim, qtd_nao, qtd_na, observacoes_gerais
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                hoje_str,
                "Engenheiro SST",
                json.dumps(respostas, ensure_ascii=False),
                qtd_sim,
                qtd_nao,
                0,
                "Inspeção inicial em planta fabril.",
            ),
        )
        conn.commit()

        df_p = pd.read_sql_query("SELECT * FROM propostas WHERE cliente_id = ?", conn, params=(cid,))
        df_c = pd.read_sql_query("SELECT * FROM checklists_visita WHERE cliente_id = ?", conn, params=(cid,))
        conn.close()

        self.assertEqual(len(df_p), 1)
        self.assertIn("PROPOSTA COMERCIAL", df_p.iloc[0]["texto_proposta"])
        self.assertEqual(len(df_c), 1)
        self.assertEqual(int(df_c.iloc[0]["qtd_nao"]), 2)

    @unittest.skipUnless(
        os.environ.get("RODARDADOS_REAIS_API") == "1",
        "Teste externo opcional desligado por padrão (use RODARDADOS_REAIS_API=1 para testar rede).",
    )
    def test_04_consulta_cnpj_api_real(self):
        dados, erro = self.utils.consultar_cnpj_api("00000000000191")
        self.assertIsNone(erro)
        self.assertIsInstance(dados, dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)