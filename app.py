import streamlit as st
import sqlite3
import hashlib
import re
from datetime import datetime
from streamlit.components.v1 import html

# ------------------------------
# CONFIGURAÇÕES INICIAIS
# ------------------------------
st.set_page_config(page_title="Meu Personal Trainer", layout="wide", initial_sidebar_state="expanded")

# Esconder menu padrão do streamlit
st.html("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display:none;}
</style>
""")

# ------------------------------
# BANCO DE DADOS
# ------------------------------
def criar_banco():
    conn = sqlite3.connect('personal.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  usuario TEXT UNIQUE,
                  senha TEXT,
                  nome TEXT,
                  tipo TEXT CHECK(tipo IN ('professor', 'aluno')))''')

    c.execute('''CREATE TABLE IF NOT EXISTS treinos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  aluno_id INTEGER,
                  nome_exercicio TEXT,
                  series INTEGER,
                  repeticoes TEXT,
                  carga TEXT,
                  observacao TEXT,
                  link_youtube TEXT,
                  data_cadastro DATE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS mensagens
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  remetente_id INTEGER,
                  destinatario_id INTEGER,
                  mensagem TEXT,
                  lida BOOLEAN DEFAULT 0,
                  data_hora DATETIME)''')

    # Cria usuario padrão do professor
    c.execute("SELECT * FROM usuarios WHERE usuario = 'professor'")
    if not c.fetchone():
        senha_hash = hash_senha("123456")
        c.execute("INSERT INTO usuarios (usuario, senha, nome, tipo) VALUES (?, ?, ?, ?)",
                  ('professor', senha_hash, 'Professor', 'professor'))

    # Cria aluno de teste
    c.execute("SELECT * FROM usuarios WHERE usuario = 'aluno'")
    if not c.fetchone():
        senha_hash = hash_senha("123")
        c.execute("INSERT INTO usuarios (usuario, senha, nome, tipo) VALUES (?, ?, ?, ?)",
                  ('aluno', senha_hash, 'João Aluno', 'aluno'))

    conn.commit()
    conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


def obter_embed_youtube(url):
    if not url:
        return None

    match = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|v/|shorts/))([A-Za-z0-9_-]{11})", url)
    if match:
        return f"https://www.youtube.com/embed/{match.group(1)}"
    return None


def exibir_video_responsivo(url):
    if not url:
        return

    embed_url = obter_embed_youtube(url)
    if embed_url:
        html(
            f"""
            <div style=\"position:relative;padding-bottom:56.25%;height:0;overflow:hidden;max-width:100%;\">
              <iframe src=\"{embed_url}\" style=\"position:absolute;top:0;left:0;width:100%;height:100%;border:0;\" allowfullscreen allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture\"></iframe>
            </div>
            """,
            height=360,
        )
    else:
        st.video(url)

def login(usuario, senha):
    conn = sqlite3.connect('personal.db')
    c = conn.cursor()
    c.execute("SELECT id, nome, tipo FROM usuarios WHERE usuario = ? AND senha = ?",
              (usuario, hash_senha(senha)))
    resultado = c.fetchone()
    conn.close()
    return resultado

# ------------------------------
# SISTEMA DE LOGIN
# ------------------------------
criar_banco()

if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario_id = None
    st.session_state.nome = None
    st.session_state.tipo = None
    st.session_state.aluno_selecionado = None

if not st.session_state.logado:
    st.title("🔐 Login")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("✅ Acessos de teste: \n\n Professor: usuario `professor` senha `123456` \n\n Aluno: usuario `aluno` senha `123`")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar", type="primary", use_container_width=True):
            dados = login(usuario, senha)
            if dados:
                st.session_state.logado = True
                st.session_state.usuario_id, st.session_state.nome, st.session_state.tipo = dados
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

    st.stop()

# ------------------------------
# MENU LATERAL
# ------------------------------
st.sidebar.title(f"Olá {st.session_state.nome} 👋")

if st.sidebar.button("Sair", use_container_width=True):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

st.sidebar.divider()

# ------------------------------
# DASHBOARD DO PROFESSOR
# ------------------------------
if st.session_state.tipo == 'professor':
    menu = st.sidebar.radio("Menu", ["🏠 Inicio", "👥 Meus Alunos", "✏️ Montar Treino", "💬 Mensagens"])

    if menu == "🏠 Inicio":
        st.title("Dashboard do Professor")
        conn = sqlite3.connect('personal.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'aluno'")
        total_alunos = c.fetchone()[0]
        conn.close()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Alunos", total_alunos)

    if menu == "👥 Meus Alunos":
        st.title("Meus Alunos")

        with st.expander("➕ Cadastrar Novo Aluno", expanded=False):
            with st.form("cadastrar_aluno", clear_on_submit=True):
                col1, col2 = st.columns(2)
                nome = col1.text_input("Nome completo do aluno")
                usuario = col2.text_input("Usuário para login")
                senha = st.text_input("Senha temporária", type="password")

                if st.form_submit_button("Cadastrar Aluno", type="primary"):
                    conn = sqlite3.connect('personal.db')
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO usuarios (usuario, senha, nome, tipo) VALUES (?, ?, ?, ?)",
                                  (usuario, hash_senha(senha), nome, 'aluno'))
                        conn.commit()
                        st.success("Aluno cadastrado com sucesso!")
                    except:
                        st.error("Esse nome de usuário já existe")
                    conn.close()

        st.divider()

        conn = sqlite3.connect('personal.db')
        c = conn.cursor()
        c.execute("SELECT id, nome, usuario FROM usuarios WHERE tipo = 'aluno' ORDER BY nome")
        alunos = c.fetchall()
        conn.close()

        for aluno in alunos:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3,1,1])
                col1.subheader(f"🧑 {aluno[1]}")
                if col2.button("✏️ Montar Treino", key=f"treino_{aluno[0]}", use_container_width=True):
                    st.session_state.aluno_selecionado = aluno[0]
                    st.switch_page(st.Page(lambda: None))
                if col3.button("💬 Chat", key=f"chat_{aluno[0]}", use_container_width=True):
                    st.session_state.aluno_selecionado = aluno[0]
                    st.session_state.menu = "💬 Mensagens"

    if menu == "✏️ Montar Treino":
        if not st.session_state.aluno_selecionado:
            st.warning("Selecione um aluno primeiro na página Meus Alunos")
            st.stop()

        conn = sqlite3.connect('personal.db')
        c = conn.cursor()
        c.execute("SELECT nome FROM usuarios WHERE id = ?", (st.session_state.aluno_selecionado,))
        nome_aluno = c.fetchone()[0]
        conn.close()

        st.title(f"Treino de {nome_aluno}")

        with st.expander("➕ Adicionar novo exercício", expanded=True):
            with st.form("novo_exercicio", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                nome_exercicio = col1.text_input("Exercício")
                series = col2.number_input("Séries", min_value=1, value=3)
                repeticoes = col3.text_input("Repetições", value="12")
                carga = st.text_input("Carga")
                observacao = st.text_input("Observações")
                link_youtube = st.text_input("Link do Youtube")

                if st.form_submit_button("Adicionar ao treino", type="primary"):
                    conn = sqlite3.connect('personal.db')
                    c = conn.cursor()
                    c.execute("""INSERT INTO treinos 
                                (aluno_id, nome_exercicio, series, repeticoes, carga, observacao, link_youtube, data_cadastro)
                                VALUES (?, ?, ?, ?, ?, ?, ?, DATE('now'))""",
                              (st.session_state.aluno_selecionado, nome_exercicio, series, repeticoes, carga, observacao, link_youtube))
                    conn.commit()
                    conn.close()
                    st.rerun()

        st.divider()

        conn = sqlite3.connect('personal.db')
        c = conn.cursor()
        c.execute("SELECT id, nome_exercicio, series, repeticoes, carga, observacao, link_youtube FROM treinos WHERE aluno_id = ?", (st.session_state.aluno_selecionado,))
        exercicios = c.fetchall()
        conn.close()

        if not exercicios:
            st.info("Nenhum exercício cadastrado para este aluno ainda.")

        for ex in exercicios:
            with st.container(border=True):
                col1, col2 = st.columns([5,1])
                with col1:
                    st.subheader(ex[1], divider=True)
                    st.write(f"🔢 {ex[2]} x {ex[3]}")
                    st.write(f"⚖️ Carga: {ex[4]}")
                    if ex[5]:
                        st.info(f"📝 {ex[5]}")
                    if ex[6]:
                        exibir_video_responsivo(ex[6])

                if col2.button("🗑️ Excluir", key=f"del_{ex[0]}", type="secondary", use_container_width=True):
                    conn = sqlite3.connect('personal.db')
                    c = conn.cursor()
                    c.execute("DELETE FROM treinos WHERE id = ?", (ex[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()

    if menu == "💬 Mensagens":
        st.title("Chat")
        st.info("Chat completo será adicionado nas próximas 24 horas!")


# ------------------------------
# DASHBOARD DO ALUNO
# ------------------------------
if st.session_state.tipo == 'aluno':
    menu = st.sidebar.radio("Menu", ["🏋️ Meu Treino", "💬 Mensagens"])

    if menu == "🏋️ Meu Treino":
        st.title("Meu Treino")

        conn = sqlite3.connect('personal.db')
        c = conn.cursor()
        c.execute("SELECT id, nome_exercicio, series, repeticoes, carga, observacao, link_youtube FROM treinos WHERE aluno_id = ?", (st.session_state.usuario_id,))
        exercicios = c.fetchall()
        conn.close()

        if not exercicios:
            st.info("Seu professor ainda não montou o seu treino.")
            st.stop()

        for ex in exercicios:
            with st.container(border=True):
                st.subheader(ex[1], divider=True)
                st.write(f"🔢 {ex[2]} séries de {ex[3]} repetições")
                st.write(f"⚖️ Carga: {ex[4]}")
                if ex[5]:
                    st.info(f"📝 Observação: {ex[5]}")
                if ex[6]:
                    exibir_video_responsivo(ex[6])

    if menu == "💬 Mensagens":
        st.title("Conversar com o Professor")
        st.info("Chat completo será adicionado em breve!")