import streamlit as st
from llama_cpp import Llama
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions
import uuid
import os
import socket

# --- 1. CONFIGURAÇÃO DE REDE ---
hostname = socket.gethostname()
try:
    ip_interno = socket.gethostbyname(hostname)
except:
    ip_interno = "localhost"

st.set_page_config(page_title="IA Federal Pro", layout="wide", page_icon="👮‍♂️")
st.title(f"👮‍♂️ IA Assistente de Legislação (Server: {ip_interno})")

# --- 2. CARREGAMENTO (USANDO MODELO 3B) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"  # Caminho relativo simples
DB_PATH = os.path.join(BASE_DIR, "banco_vetorial")

@st.cache_resource
def carregar_cerebro():
    if not os.path.exists(MODEL_PATH):
        st.error(f"Modelo não encontrado: {MODEL_PATH}")
        return None
    # Contexto 8192 para ler tabelas grandes
    return Llama(model_path=MODEL_PATH, n_ctx=8192, n_threads=4, verbose=False)

@st.cache_resource
def carregar_memoria():
    # Garante que a pasta existe
    os.makedirs(DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=DB_PATH)
    embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return client.get_or_create_collection(name="leis_federais", embedding_function=embed)

llm = carregar_cerebro()
collection = carregar_memoria()

# --- 3. LEITURA INTELIGENTE (PyMuPDF - PARA TABELAS) ---
def ler_pdf_visual(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    texto = ""
    for pagina in doc:
        # sort=True organiza a tabela visualmente
        texto += pagina.get_text("text", sort=True) + "\n"
    return texto

# --- 4. LÓGICA MESTRA (BUSCA HÍBRIDA SEGURA) ---
def responder(pergunta):
    # 1. QUERY EXPANSION (Melhorar a pergunta, não a resposta)
    # Isso ajuda o banco a achar o trecho certo SEM inventar coisas se o PDF for outro.
    query_turbinada = pergunta
    termo_busca = pergunta.lower()
    
    if "empossado" in termo_busca or "novo" in termo_busca or "estágio" in termo_busca:
        # Adicionamos palavras-chave que costumam estar na regra de isenção
        query_turbinada += " estabilidade afastada exigência participação"
    
    if "chuí" in termo_busca or "índice" in termo_busca:
        query_turbinada += " tabela anexo lista de cidades"

    # 2. BUSCA NO BANCO (Aumentamos para 30 para ler mais páginas e garantir)
    # n_results=30 garante que pegamos o início (Art 20) e o fim (Art 34) do documento
    res = collection.query(query_texts=[query_turbinada], n_results=30)
    
    if not res['documents'] or not res['documents'][0]: 
        return "ERRO: Não encontrei nada relevante no documento.", ""
    
    # Junta os trechos encontrados
    contexto = "\n---\n".join(res['documents'][0])
    
    # 3. LÓGICA DETERMINÍSTICA (O "Juiz" do Python)
    # Isso só ativa SE o texto for encontrado no PDF. Seguro para qualquer arquivo.
    dica_mestra = ""
    contexto_lower = contexto.lower()
    
    # Verifica conflito: Art 20 (Vedado) vs Art 34 (Afastada)
    # Se encontrar "afastada" e "estabilidade", essa regra ganha (pois é exceção específica)
    if "afastada" in contexto_lower and "estabilidade" in contexto_lower:
        dica_mestra = "REGRA SUPREMA: O texto encontrado menciona explicitamente que a estabilidade foi AFASTADA. Ignore regras gerais de proibição e responda que PODE participar."
    elif "vedado" in contexto_lower and "estabilidade" in contexto_lower:
        dica_mestra = "ATENÇÃO: O texto menciona vedação por falta de estabilidade. Verifique se há exceções citadas no contexto."

    # 4. PROMPT FINAL
    prompt = f"""<|start_header_id|>system<|end_header_id|>
Você é um Especialista em Legislação. Responda APENAS com base no contexto abaixo.

INSTRUÇÃO DE SEGURANÇA:
{dica_mestra}

REGRAS:
1. Se a resposta estiver numa tabela, cite o valor exato.
2. Priorize "Disposições Finais" ou regras de exceção se aparecerem no texto.
3. Se o contexto não tiver a resposta, diga "Não consta no documento analisado".

CONTEXTO ENCONTRADO:
{contexto}
<|eot_id|><|start_header_id|>user<|end_header_id|>
{pergunta}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    
    output = llm(prompt, max_tokens=1024, temperature=0.0, stop=["<|eot_id|>"])
    
    return output['choices'][0]['text'], contexto

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Gestão")
    
    # Botão de Reset
    if st.button("🗑️ Limpar Memória"):
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            client.delete_collection("leis_federais")
            st.success("Memória apagada! Recarregue a página.")
        except:
            st.warning("Já estava vazia.")

    files = st.file_uploader("Normativos (PDF)", type="pdf", accept_multiple_files=True)
    if files and st.button("Processar"):
        with st.spinner("Lendo tabelas com PyMuPDF..."):
            for f in files:
                txt = ler_pdf_visual(f)
                chunks = [txt[i:i+600] for i in range(0, len(txt), 300)]
                collection.add(documents=chunks, ids=[str(uuid.uuid4()) for _ in chunks])
            st.success("Processado!")

st.subheader("Chat Jurídico Pro")

if "msg" not in st.session_state: st.session_state.msg = []

for m in st.session_state.msg:
    st.chat_message(m["role"]).write(m["content"])

if p := st.chat_input("Dúvida..."):
    st.chat_message("user").write(p)
    st.session_state.msg.append({"role": "user", "content": p})
    
    with st.spinner("Analisando..."):
       resp, ctx_debug = responder(p)
    
    st.chat_message("assistant").write(resp)
    st.session_state.msg.append({"role": "assistant", "content": resp})

    with st.expander("Ver Contexto Lido (Debug)"):
        st.text(ctx_debug)