import json
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

CATEGORIAS_CLIENTE = [
    "Prospecto",
    "Mensalista",
    "Credenciada"
]

STATUS_CLIENTE = [
    "Ativo",
    "Inativo"
]

PERFIS_PADRAO = [
    "Administrador",
    "Comercial / Atendimento",
    "Técnico SST"
]

PERMISSOES_PADRAO_POR_PERFIL = {
    "Administrador": {
        "telas": [
            "Dashboard",
            "Clientes (Consulta e Cadastro)",
            "Funil de Vendas (Pipeline)",
            "Lançar Atividades",
            "Agenda & Follow-ups",
            "Emissão de Propostas",
            "Checklist Visita Técnica",
            "Usuários e Senhas"
        ],
        "pode_editar": True,
        "pode_excluir": True
    },
    "Comercial / Atendimento": {
        "telas": [
            "Dashboard",
            "Clientes (Consulta e Cadastro)",
            "Funil de Vendas (Pipeline)",
            "Lançar Atividades",
            "Agenda & Follow-ups",
            "Emissão de Propostas"
        ],
        "pode_editar": True,
        "pode_excluir": False
    },
    "Técnico SST": {
        "telas": [
            "Dashboard",
            "Clientes (Consulta e Cadastro)",
            "Lançar Atividades",
            "Agenda & Follow-ups",
            "Checklist Visita Técnica"
        ],
        "pode_editar": True,
        "pode_excluir": False
    }
}

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

ITENS_CHECKLIST_SST = [
    ("1.1", "PGR atualizado e disponível?"),
    ("1.2", "Inventário de riscos disponível?"),
    ("1.3", "Plano de ação do PGR atualizado?"),
    ("2.1", "Possui CIPA/representação aplicável constituída?"),
    ("3.1", "EPIs adequados aos riscos da atividade?"),
    ("3.2", "EPIs possuem CA quando aplicável?"),
    ("3.3", "Existe controle de entrega de EPI?"),
    ("4.1", "PCMSO vigente?"),
    ("4.2", "Exames ocupacionais estão dentro da validade?"),
    ("4.3", "ASOs estão disponíveis?"),
    ("5.1", "Avaliações ocupacionais necessárias estão sendo realizadas?"),
    ("5.2", "Medidas de controle estão implementadas?"),
    ("5.3", "Produtos químicos estão identificados?"),
    ("5.4", "FDS/FISPQ disponíveis quando aplicável?"),
    ("6.1", "Quadros elétricos identificados e fechados?"),
    ("6.2", "Instalações sem fios expostos/improvisações?"),
    ("6.3", "Tomadas e extensões em condições seguras?"),
    ("6.4", "Equipamentos possuem aterramento quando aplicável?"),
    ("6.5", "Serviços elétricos realizados por pessoal autorizado?"),
    ("6.6", "Há sinalização de risco elétrico?"),
    ("7.1", "Empilhadeiras em condições seguras?"),
    ("7.2", "Operadores de empilhadeira estão autorizados/capacitados?"),
    ("7.3", "Inspeção da empilhadeira realizada?"),
    ("7.4", "Capacidade de carga identificada?"),
    ("7.5", "Cargas armazenadas de forma estável?"),
    ("7.6", "Corredores de circulação livres?"),
    ("7.7", "Pedestres estão protegidos da circulação de empilhadeiras?"),
    ("8.1", "Máquinas possuem proteções nas partes móveis?"),
    ("8.2", "Proteções estão instaladas e funcionando?"),
    ("8.3", "Paradas de emergência estão disponíveis quando aplicável?"),
    ("8.4", "Sistemas de segurança estão funcionando?"),
    ("8.5", "Zonas de perigo estão protegidas?"),
    ("8.6", "Máquinas estão identificadas?"),
    ("8.7", "Manutenções são realizadas com segurança?"),
    ("8.8", "Há bloqueio de energias perigosas durante as intervenções?"),
    ("8.9", "Operadores são capacitados conforme NR-12?"),
    ("8.10", "Não existem adaptações e/ou improvisações inseguras?"),
    ("8.11", "Quadro elétrico dos equipamentos está inacessível ao operador?"),
    ("9.1", "Vasos de pressão/compressores possuem documentação/registro disponível quando aplicável?"),
    ("9.2", "Vasos de pressão/compressores: é realizada inspeção de segurança dentro do prazo?"),
    ("10.1", "Possui LTIP (Laudo Técnico de Insalubridade e Periculosidade)?"),
    ("11.1", "Inflamáveis e combustíveis estão identificados?"),
    ("11.2", "Tintas e solventes armazenados adequadamente?"),
    ("11.3", "Produtos inflamáveis estão em local adequado e ventilado?"),
    ("11.4", "Áreas de armazenamento estão sinalizadas?"),
    ("11.5", "Recipientes estão identificados e fechados?"),
    ("11.6", "Trabalhadores possuem capacitação aplicável?")
]


def gerar_hash_senha(senha):
    return hashlib.sha256(str(senha).encode("utf-8")).hexdigest()


def conectar_db():
    conn = sqlite3.connect("crm_sistema.db")
    conn.execute("PRAGMA foreign_keys = 1")
    return conn


def _popular_permissoes_padrao(cursor):
    for perfil, cfg in PERMISSOES_PADRAO_POR_PERFIL.items():
        telas_json = json.dumps(cfg["telas"], ensure_ascii=False)
        cursor.execute("""
            INSERT OR IGNORE INTO permissoes_perfil (perfil, telas_json, pode_editar, pode_excluir)
            VALUES (?, ?, ?, ?)
        """, (
            perfil,
            telas_json,
            1 if cfg["pode_editar"] else 0,
            1 if cfg["pode_excluir"] else 0
        ))


def obter_permissoes_perfil(perfil):
    perfil_nome = (perfil or "Comercial / Atendimento").strip()
    if perfil_nome == "Administrador":
        padrao = PERMISSOES_PADRAO_POR_PERFIL["Administrador"]
        return {
            "telas": list(padrao["telas"]),
            "pode_editar": True,
            "pode_excluir": True
        }

    conn = conectar_db()
    row = conn.execute("""
        SELECT telas_json, pode_editar, pode_excluir
        FROM permissoes_perfil
        WHERE perfil = ?
    """, (perfil_nome,)).fetchone()
    conn.close()

    if row:
        try:
            telas = json.loads(row[0] or "[]")
        except Exception:
            telas = []
        return {
            "telas": telas,
            "pode_editar": bool(row[1]),
            "pode_excluir": bool(row[2])
        }

    padrao = PERMISSOES_PADRAO_POR_PERFIL.get(
        perfil_nome,
        PERMISSOES_PADRAO_POR_PERFIL["Comercial / Atendimento"]
    )
    return {
        "telas": list(padrao["telas"]),
        "pode_editar": bool(padrao["pode_editar"]),
        "pode_excluir": bool(padrao["pode_excluir"])
    }


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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissoes_perfil (
            perfil TEXT PRIMARY KEY,
            telas_json TEXT NOT NULL,
            pode_editar INTEGER DEFAULT 1,
            pode_excluir INTEGER DEFAULT 0
        )
    """)
    _popular_permissoes_padrao(cursor)

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
            categoria TEXT DEFAULT 'Prospecto',
            status_cliente TEXT DEFAULT 'Ativo',
            cnae_principal TEXT DEFAULT '',
            cnaes_secundarios TEXT DEFAULT '',
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

    if "categoria" not in colunas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN categoria TEXT DEFAULT 'Prospecto'")
    if "status_cliente" not in colunas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN status_cliente TEXT DEFAULT 'Ativo'")
    if "cnae_principal" not in colunas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN cnae_principal TEXT DEFAULT ''")
    if "cnaes_secundarios" not in colunas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN cnaes_secundarios TEXT DEFAULT ''")
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
            atendente TEXT DEFAULT 'Administrador',
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """)

    colunas_ativ = [col[1] for col in cursor.execute("PRAGMA table_info(atividades)").fetchall()]
    for col in ["hora_inicio", "hora_fim", "tempo_total", "atendente"]:
        if col not in colunas_ativ:
            cursor.execute(f"ALTER TABLE atividades ADD COLUMN {col} TEXT DEFAULT 'Administrador'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS propostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            data_emissao TEXT NOT NULL,
            solicitante TEXT NOT NULL,
            contatos TEXT DEFAULT '',
            servicos TEXT NOT NULL,
            itens_json TEXT DEFAULT '[]',
            valor_investimento REAL DEFAULT 0.0,
            condicoes_pagamento TEXT DEFAULT '',
            observacoes_art TEXT DEFAULT '',
            responsavel_emissao TEXT DEFAULT 'Administrador',
            status_proposta TEXT DEFAULT 'Aguardando Aceite',
            token_aceite TEXT DEFAULT '',
            data_aceite TEXT DEFAULT '',
            texto_proposta TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """)

    colunas_prop = [col[1] for col in cursor.execute("PRAGMA table_info(propostas)").fetchall()]
    if "itens_json" not in colunas_prop:
        cursor.execute("ALTER TABLE propostas ADD COLUMN itens_json TEXT DEFAULT '[]'")
    if "status_proposta" not in colunas_prop:
        cursor.execute("ALTER TABLE propostas ADD COLUMN status_proposta TEXT DEFAULT 'Aguardando Aceite'")
    if "token_aceite" not in colunas_prop:
        cursor.execute("ALTER TABLE propostas ADD COLUMN token_aceite TEXT DEFAULT ''")
    if "data_aceite" not in colunas_prop:
        cursor.execute("ALTER TABLE propostas ADD COLUMN data_aceite TEXT DEFAULT ''")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checklists_visita (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            data_visita TEXT NOT NULL,
            hora_inicio TEXT DEFAULT '',
            hora_fim TEXT DEFAULT '',
            responsavel_tecnico TEXT NOT NULL,
            pessoas_acompanhamento TEXT DEFAULT '',
            respostas_json TEXT NOT NULL,
            obs_grupos_json TEXT DEFAULT '{}',
            qtd_sim INTEGER DEFAULT 0,
            qtd_nao INTEGER DEFAULT 0,
            qtd_na INTEGER DEFAULT 0,
            observacoes_gerais TEXT DEFAULT '',
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """)

    colunas_chk = [col[1] for col in cursor.execute("PRAGMA table_info(checklists_visita)").fetchall()]
    if "hora_inicio" not in colunas_chk:
        cursor.execute("ALTER TABLE checklists_visita ADD COLUMN hora_inicio TEXT DEFAULT ''")
    if "hora_fim" not in colunas_chk:
        cursor.execute("ALTER TABLE checklists_visita ADD COLUMN hora_fim TEXT DEFAULT ''")
    if "pessoas_acompanhamento" not in colunas_chk:
        cursor.execute("ALTER TABLE checklists_visita ADD COLUMN pessoas_acompanhamento TEXT DEFAULT ''")
    if "obs_grupos_json" not in colunas_chk:
        cursor.execute("ALTER TABLE checklists_visita ADD COLUMN obs_grupos_json TEXT DEFAULT '{}'")

    conn.commit()
    conn.close()