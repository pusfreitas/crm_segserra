import json
import streamlit as st
import sqlite3
import pandas as pd
from utils import renderizar_logo_segserra

TODAS_TELAS_SISTEMA = [
    "Dashboard",
    "Clientes (Consulta e Cadastro)",
    "Funil de Vendas (Pipeline)",
    "Lançar Atividades",
    "Agenda & Follow-ups",
    "Emissão de Propostas",
    "Checklist Visita Técnica",
    "Usuários e Senhas"
]


def _salvar_permissoes_no_banco(perfil_alvo, telas_escolhidas, perm_editar, perm_excluir):
    conn = conectar_db()
    conn.execute("""
        INSERT INTO permissoes_perfil (perfil, telas_json, pode_editar, pode_excluir)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(perfil) DO UPDATE SET
            telas_json = excluded.telas_json,
            pode_editar = excluded.pode_editar,
            pode_excluir = excluded.pode_excluir
    """, (
        perfil_alvo,
        json.dumps(telas_escolhidas, ensure_ascii=False),
        1 if perm_editar else 0,
        1 if perm_excluir else 0
    ))
    conn.commit()
    conn.close()


def renderizar_tela_login():
    col1, col2, col3 = st.columns([1, 1.15, 1])
    with col2:
        st.write("")
        st.write("")
        with st.container(border=True):
            renderizar_logo_segserra(centralizado=True, tema_escuro=False)
            st.markdown(
                "<h4 style='text-align: center; margin-top: 0; color: #334155;'>🔒 Portal CRM & Gestão Comercial</h4>",
                unsafe_allow_html=True
            )
            st.caption("Informe suas credenciais individuais para acessar o sistema.")

            with st.form("form_login"):
                usuario_input = st.text_input("Usuário (Login)").strip().lower()
                senha_input = st.text_input("Senha", type="password")
                entrar = st.form_submit_button("Acessar Sistema", use_container_width=True, type="primary")

                if entrar:
                    if not usuario_input or not senha_input:
                        st.warning("Preencha o usuário e a senha.")
                    else:
                        conn = conectar_db()
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT id, usuario, nome_completo, senha_hash, perfil, ativo 
                            FROM usuarios 
                            WHERE LOWER(usuario) = ?
                        """, (usuario_input,))
                        user_row = cursor.fetchone()
                        conn.close()

                        if not user_row:
                            st.error("Usuário ou senha incorretos!")
                        else:
                            uid, u_login, u_nome, u_hash, u_perfil, u_ativo = user_row
                            if u_ativo == 0:
                                st.error("🚫 Este usuário está inativo. Contate o Administrador.")
                            elif gerar_hash_senha(senha_input) == u_hash:
                                perms = obter_permissoes_perfil(u_perfil)
                                telas_permitidas = perms.get("telas") or ["Dashboard"]
                                st.session_state.logado = True
                                st.session_state.usuario_id = uid
                                st.session_state.usuario_atual = u_login
                                st.session_state.nome_usuario = u_nome
                                st.session_state.perfil_usuario = u_perfil
                                st.session_state.menu_pagina = (
                                    "Dashboard" if "Dashboard" in telas_permitidas else telas_permitidas[0]
                                )
                                st.rerun()
                            else:
                                st.error("Usuário ou senha incorretos!")


def realizar_logout():
    for chave in ["logado", "usuario_id", "usuario_atual", "nome_usuario", "perfil_usuario"]:
        st.session_state[chave] = False if chave == "logado" else None


def renderizar_gestao_usuarios():

    perfil_logado = st.session_state.get("perfil_usuario", "Comercial / Atendimento")
    perms_logado = obter_permissoes_perfil(perfil_logado)
    pode_editar = perms_logado.get("pode_editar", False)

    if perfil_logado == "Administrador":
            "👥 Cadastrar e Gerenciar Equipe",
            "🛡️ Permissões por Perfil",
            "🔑 Alterar Minha Senha"
        ])
    else:
        aba_equipe = None
        aba_permissoes = None
        aba_minha_senha = st.container()
        aba_equipe = None

    # --- ABA EXCLUSIVA PARA ADMINISTRADORES ---
    if aba_equipe is not None:
        with aba_equipe:
            c_novo, c_editar = st.columns([1.1, 1.3])

            with c_novo:
                st.subheader("➕ Cadastrar Novo Usuário")
                with st.form("form_novo_usuario", clear_on_submit=True):
                    novo_nome = st.text_input("Nome Completo do Colaborador *", placeholder="Ex: João Silva")
                    novo_login = st.text_input("Login de Acesso (sem espaços) *", placeholder="Ex: joao.silva")
                    nova_senha = st.text_input("Senha Inicial *", type="password")

                    btn_criar = st.form_submit_button("💾 Criar Usuário", use_container_width=True, type="primary")
                    if btn_criar:
                        login_limpo = novo_login.strip().lower().replace(" ", "")
                        if not novo_nome.strip() or not login_limpo or len(nova_senha) < 4:
                            st.error("Preencha o Nome, o Login e uma senha de pelo menos 4 caracteres.")
                        else:
                            try:
                                conn = conectar_db()
                                conn.execute("""
                                    INSERT INTO usuarios (usuario, nome_completo, senha_hash, perfil, ativo)
                                    VALUES (?, ?, ?, ?, 1)
                                """, (login_limpo, novo_nome.strip(), gerar_hash_senha(nova_senha), novo_perfil))
                                conn.commit()
                                conn.close()
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Este login de usuário já existe no sistema!")

            with c_editar:
                st.subheader("⚙️ Editar / Redefinir Senha / Bloquear")
                conn = conectar_db()
                df_users = pd.read_sql_query("""
                    SELECT id, usuario, nome_completo, perfil, ativo 
                    FROM usuarios 
                    ORDER BY id ASC
                """, conn)
                conn.close()

                opcoes_u = {
                    f"{r['nome_completo']} ({r['usuario']}) - {'🟢 Ativo' if r['ativo'] else '🔴 Inativo'}": r
                    for _, r in df_users.iterrows()
                }
                user_sel_lbl = st.selectbox("Selecione o usuário:", list(opcoes_u.keys()))
                u_sel = opcoes_u[user_sel_lbl]
                uid_sel = int(u_sel["id"])

                with st.form(f"form_edit_user_{uid_sel}"):
                    ed_nome = st.text_input("Nome Completo", value=u_sel["nome_completo"])
                    ed_perfil = st.selectbox("Perfil", perfis_lista, index=idx_p)
                    ed_ativo = st.checkbox("Usuário Ativo (Permitir Login)", value=bool(u_sel["ativo"]))

                    c_b1, c_b2 = st.columns(2)
                    with c_b1:
                    with c_b2:
                        btn_del = st.form_submit_button("🗑️ Excluir Usuário", use_container_width=True)

                    if btn_upd:
                        if uid_sel == st.session_state.get("usuario_id") and not ed_ativo:
                            st.error("Você não pode desativar o seu próprio usuário logado!")
                        else:
                            conn = conectar_db()
                            if ed_nova_senha.strip():
                                conn.execute("""
                                    UPDATE usuarios SET nome_completo=?, perfil=?, ativo=?, senha_hash=? WHERE id=?
                            else:
                                conn.execute("""
                                    UPDATE usuarios SET nome_completo=?, perfil=?, ativo=? WHERE id=?
                                """, (ed_nome.strip(), ed_perfil, int(ed_ativo), uid_sel))
                            conn.commit()
                            conn.close()
                            st.rerun()

                    if btn_del:
                        if uid_sel == st.session_state.get("usuario_id"):
                            st.error("Você não pode excluir o seu próprio usuário enquanto estiver logado!")
                        elif u_sel["usuario"] == "admin":
                            st.error("O usuário 'admin' principal não pode ser excluído.")
                        else:
                            conn = conectar_db()
                            conn.execute("DELETE FROM usuarios WHERE id=?", (uid_sel,))
                            conn.commit()
                            conn.close()
                            st.rerun()

            st.divider()
            st.subheader("📋 Lista de Usuários Cadastrados")
            df_exib = df_users.copy()
            df_exib["Status"] = df_exib["ativo"].apply(lambda x: "🟢 Ativo" if x == 1 else "🔴 Inativo")
            df_exib = df_exib.rename(columns={
                "id": "ID", "usuario": "Login", "nome_completo": "Nome Completo", "perfil": "Perfil de Acesso"
            })[["ID", "Nome Completo", "Login", "Perfil de Acesso", "Status"]]
            st.dataframe(df_exib, use_container_width=True, hide_index=True)

    with aba_minha_senha:
        st.subheader("🔑 Alterar Minha Senha de Acesso")
        if not pode_editar and perfil_logado != "Administrador":
            st.caption("A alteração da própria senha permanece disponível para a sua conta.")
        with st.form("form_trocar_propria_senha", clear_on_submit=True):
            senha_atual = st.text_input("Senha Atual *", type="password")
            senha_nova = st.text_input("Nova Senha *", type="password")
            senha_conf = st.text_input("Confirmar Nova Senha *", type="password")
            btn_trocar = st.form_submit_button("💾 Atualizar Minha Senha", type="primary")

            if btn_trocar:
                if len(senha_nova) < 4:
                    st.error("A nova senha deve ter pelo menos 4 caracteres.")
                elif senha_nova != senha_conf:
                    st.error("A confirmação de senha não confere com a nova senha.")
                else:
                    conn = conectar_db()
                    hash_atual_db = conn.execute(
                        "SELECT senha_hash FROM usuarios WHERE id=?",
                        (int(st.session_state.usuario_id),)
                    ).fetchone()[0]

                    if gerar_hash_senha(senha_atual) != hash_atual_db:
                        conn.close()
                        st.error("A Senha Atual informada está incorreta!")
                    else:
                        conn.execute(
                            "UPDATE usuarios SET senha_hash=? WHERE id=?",
                            (gerar_hash_senha(senha_nova), int(st.session_state.usuario_id))
                        )
                        conn.commit()
                        conn.close()
                        st.success("✅ Sua senha foi alterada com sucesso!")