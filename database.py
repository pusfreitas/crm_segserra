import sqlite3
import hashlib

ETAPAS_FUNIL = [
    "1. Prospecção / Lead",
    "2. Diagnóstico / Visita Técnica",
    "3. Proposta / Tabela Enviada",
    "4. Em Negociação",
    "5. Fechado (Cliente Ativo)",
    "Perdido / Inativo"
]

OPCOES_SERVICOS = [
    "Contrato Mensal (PGR + PCMSO + LTCAT + eSocial)",
    "Laudos Avulsos (PGR / PCMSO / LTCAT / AEP)",
    "Avaliação Psicossocial (COPSOQ II / NR-01)",
    "Exames Ocupacionais (Clínico + Complementares)",
    "Credenciamento (Clínica Parceira)",
    "Parceria Estratégica (Escritório Contábil)",
    "Treinamentos de NRs (NR-10, NR-12, NR-18, NR-35, CIPA)",
    "Outros"
]


def gerar_hash_senha(senha):
    return hashlib.sha256(str(senha).encode("utf-8")).hexdigest()


def conectar_db():
    conn = sqlite3.connect("crm_sistema.db")
    conn.execute("PRAGMA foreign_keys = 1")
    return conn


def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()

    # 1. Tabela de Usuários (Múltiplos Acessos e Perfis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            nome_completo TEXT NOT NULL,
            senha_hash TEXT NOT NULL,
            perfil TEXT DEFAULT 'Comercial / Atendimento',
            ativo INTEGER DEFAULT 1
        )
    """)

    # Garante que exista pelo menos o usuário admin padrão (admin / 1234)
    qtd_usuarios = cursor.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if qtd_usuarios == 0:
        cursor.execute("""
            INSERT INTO usuarios (usuario, nome_completo, senha_hash, perfil, ativo)
            VALUES (?, ?, ?, ?, 1)
        """, ("admin", "Administrador Geral", gerar_hash_senha("1234"), "Administrador"))

    # 2. Tabela de Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT UNIQUE NOT NULL,
            razao_social TEXT NOT NULL,
            nome_fantasia TEXT,
            responsavel_pf TEXT NOT NULL,
            cpf_responsavel TEXT DEFAULT '',
            telefone TEXT,
            email TEXT,
            cep TEXT,
            logradouro TEXT,
            numero TEXT,
            complemento TEXT,
            bairro TEXT,
            cidade TEXT,
            uf TEXT,
            etapa_funil TEXT DEFAULT '1. Prospecção / Lead',
            valor_estimado REAL DEFAULT 0.0,
            servico_interesse TEXT DEFAULT '',
            proximo_contato TEXT DEFAULT ''
        )
    """)

    colunas_clientes = [col[1] for col in cursor.execute("PRAGMA table_info(clientes)").fetchall()]
    for col in ["cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf"]:
        if col not in colunas_clientes:
            cursor.execute(f"ALTER TABLE clientes ADD COLUMN {col} TEXT DEFAULT ''")

    if "etapa_funil" not in colunas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN etapa_funil TEXT DEFAULT '1. Prospecção / Lead'")
    if "valor_estimado" not in colunas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN valor_estimado REAL DEFAULT 0.0")
    if "servico_interesse" not in colunas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN servico_interesse TEXT DEFAULT ''")
    if "proximo_contato" not in colunas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN proximo_contato TEXT DEFAULT ''")

    # 3. Tabela de Atividades (Movimentações)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            hora_inicio TEXT DEFAULT '',
            hora_fim TEXT DEFAULT '',
            tempo_total TEXT DEFAULT '',
            modalidade TEXT NOT NULL,
            descricao TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """)

    colunas_ativ = [col[1] for col in cursor.execute("PRAGMA table_info(atividades)").fetchall()]
    for col in ["hora_inicio", "hora_fim", "tempo_total", "atendente"]:
        if col not in colunas_ativ:
            cursor.execute(f"ALTER TABLE atividades ADD COLUMN {col} TEXT DEFAULT 'Administrador'")

    conn.commit()
    conn.close()