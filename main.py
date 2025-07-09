import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# --- Conexão com Supabase ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="OpenBet - Hamburguinhos", layout="wide")
st.title("🏆 OpenBet - Apostas em Hamburguinhos")

# --- Login (seleção de usuário) ---
usuarios_data = supabase.table("usuarios").select("id, nome, saldo").execute()
usuarios_df = pd.DataFrame(usuarios_data.data)

usuario_nome = st.selectbox("Escolha seu nome", usuarios_df["nome"])
usuario_row = usuarios_df[usuarios_df["nome"] == usuario_nome].iloc[0]
usuario_id = usuario_row["id"]
saldo_usuario = usuario_row["saldo"]
st.markdown(f"**Saldo atual:** {saldo_usuario:.2f} hamburguinhos")

# --- Criar aposta ---
st.subheader("Criar Aposta")
with st.form("form_aposta"):
    esporte = st.selectbox("Esporte", ["Futebol", "Tênis"])
    descricao = st.text_input("Descrição da Partida", "Djokovic x Alcaraz")
    odd = st.number_input("Odd para seu lado", min_value=1.01, value=2.00)
    valor = st.number_input("Valor (hamburguinhos)", min_value=1.0, value=10.0)
    escolha = st.text_input("Seu palpite (ex: 3x1, Djokovic vence)")
    sub = st.form_submit_button("Criar")

    if sub:
        if valor > saldo_usuario:
            st.error("Saldo insuficiente.")
        else:
            supabase.table("apostas").insert({
                "id_usuario": usuario_id,
                "esporte": esporte,
                "descricao": descricao,
                "odd": odd,
                "valor": valor,
                "escolha": escolha,
                "status": "aberta",
                "criado_em": datetime.now().isoformat()
            }).execute()
            supabase.table("usuarios").update({"saldo": saldo_usuario - valor}).eq("id", usuario_id).execute()
            st.success("Aposta criada!")

# --- Apostas abertas ---
st.subheader("Apostas Abertas")
apostas_abertas = supabase.table("apostas").select("*, usuarios(nome)").eq("status", "aberta").neq("id_usuario", usuario_id).execute()
df_apostas = pd.DataFrame(apostas_abertas.data)

if len(df_apostas):
    for i, row in df_apostas.iterrows():
        with st.expander(f"{row['descricao']} - {row['usuarios']['nome']} apostou {row['valor']}"):
            if st.button(f"Aceitar aposta {i}"):
                if row["valor"] > saldo_usuario:
                    st.error("Saldo insuficiente.")
                else:
                    supabase.table("apostas").update({
                        "status": "pendente",
                        "id_oponente": usuario_id
                    }).eq("id", row["id"]).execute()
                    supabase.table("usuarios").update({"saldo": saldo_usuario - row["valor"]}).eq("id", usuario_id).execute()
                    st.success("Aposta aceita!")

# --- Finalização admin ---
st.subheader("Finalizar Aposta (admin)")
apostas_pendentes = supabase.table("apostas").select("*, usuarios(nome)").eq("status", "pendente").execute()
df_pendentes = pd.DataFrame(apostas_pendentes.data)

for i, row in df_pendentes.iterrows():
    with st.expander(f"{row['descricao']} - pendente"):
        vencedor = st.selectbox("Vencedor", ["criador", "oponente"], key=f"win_{i}")
        if st.button(f"Finalizar aposta {i}"):
            ganhador_id = row["id_usuario"] if vencedor == "criador" else row["id_oponente"]
            premio = 2 * row["valor"]
            saldo_antigo = supabase.table("usuarios").select("saldo").eq("id", ganhador_id).execute().data[0]["saldo"]
            supabase.table("usuarios").update({"saldo": saldo_antigo + premio}).eq("id", ganhador_id).execute()
            supabase.table("apostas").update({
                "status": "finalizada",
                "resultado": vencedor
            }).eq("id", row["id"]).execute()
            st.success("Aposta finalizada!")

# --- Histórico ---
st.subheader("Histórico de Apostas Finalizadas")
historico = supabase.table("apostas").select("*, usuarios(nome)").eq("status", "finalizada").execute()
df_hist = pd.DataFrame(historico.data)
if len(df_hist):
    st.dataframe(df_hist[["descricao", "valor", "odd", "escolha", "resultado", "usuarios"]["nome"]])
else:
    st.info("Nenhum resultado ainda.")
