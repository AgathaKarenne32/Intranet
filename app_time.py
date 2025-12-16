import streamlit as st
from llama_cpp import Llama
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions
import uuid
import os
import socket

# --- 1. CONFIGURAÇÃO ---
hostname = socket.gethostname()
try:
    ip_interno = socket.gethostbyname(hostname)
except:
    ip_interno = "localhost"

st.set_page_config(page_title="IA Federal Pro", layout="wide", page_icon="👮‍♂️")
st.title(f"👮‍♂️ IA Assistente de Legislação (Server: {ip_interno})")

# --- 2. CARREGAMENTO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
DB_PATH = os.path.join(BASE_DIR, "banco_vetorial")

# O MODELO (Cérebro) deve ter cache para não recarregar toda hora 
@st.cache_resource
def carregar_cerebro():
    if not os.path.exists(MODEL_PATH):
        st.error(f"Modelo não encontrado: {MODEL_PATH}")
        return None
    return Llama(model_path=MODEL_PATH, n_ctx=8192, n_threads=4, verbose=False)

# O BANCO (Memória) NÃO deve ter cache para evitar o erro "Collection does not exist"
def carregar_memoria():
    os.makedirs(DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=DB_PATH)
    embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    # get_or_create garante que sempre pegamos uma coleção válida
    return client.get_or_create_collection(name="leis_federais", embedding_function=embed)

llm = carregar_cerebro()
# Agora o 'collection' é sempre renovado a cada clique, evitando o erro
collection = carregar_memoria()

# --- 3. LEITURA & INDEXAÇÃO ---
def ler_pdf_visual(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    texto = ""
    for pagina in doc:
        # sort=True garante que "Chuí .... 3.75" seja lido na mesma linha
        texto += pagina.get_text("text", sort=True) + "\n"
    return texto

# --- 4. BUSCA HÍBRIDA (Resolve o problema do Chuí) ---
def buscar_hibrido(pergunta):
    # A. Busca Vetorial (Conceitos e Regras - Art 34)
    query_limpa = pergunta.lower().replace("tabela", "").replace("anexo", "")
    if "empossado" in query_limpa or "novo" in query_limpa:
        query_limpa += " artigo 34 estabilidade afastada"

    try:
        res_vetor = collection.query(query_texts=[query_limpa], n_results=20)
        docs_vetor = res_vetor['documents'][0] if res_vetor['documents'] else []
    except:
        docs_vetor = []

    # B. Busca Exata (Palavra-Chave - Chuí/Tabelas)
    docs_exatos = []
    
    if "cache_texto_completo" in st.session_state:
        termo_chave = ""
        pergunta_lower = pergunta.lower()
        
        # Identifica se é uma busca de tabela ou nome específico
        if "chuí" in pergunta_lower: termo_chave = "Chuí"
        elif "índice" in pergunta_lower: termo_chave = "ÍNDICE"
        elif "barreiras" in pergunta_lower: termo_chave = "Barreiras"
        
        if termo_chave:
            # Varre todos os pedaços procurando a palavra exata
            for pedaco in st.session_state.cache_texto_completo:
                if termo_chave in pedaco:
                    docs_exatos.append(pedaco)
    
    # Junta tudo e remove duplicatas
    todos_docs = list(set(docs_vetor + docs_exatos))
    return "\n---\n".join(todos_docs)

def responder(pergunta):
    contexto = buscar_hibrido(pergunta)
    
    if not contexto:
        return "ERRO: Não encontrei nada relevante.", ""
    
    # Lógica Determinística (Juiz)
    dica_mestra = ""
    ctx_lower = contexto.lower()
    
    # Regra do Recém-Empossado (Art 34)
    if "afastada" in ctx_lower and "estabilidade" in ctx_lower:
        dica_mestra = "REGRA SUPREMA: O texto confirma que a estabilidade foi AFASTADA (Art. 34). Responda que PODE participar."
    elif "vedado" in ctx_lower and "estabilidade" in ctx_lower:
        dica_mestra = "ATENÇÃO: O texto menciona vedação. Verifique se há exceções no contexto."

    prompt = f"""<|start_header_id|>system<|end_header_id|>
Você é um Auditor da PF. Analise o CONTEXTO abaixo.
Se a pergunta for sobre um índice (cidade), responda apenas o valor numérico.

DICA:
{dica_mestra}

CONTEXTO:
{contexto}
<|eot_id|><|start_header_id|>user<|end_header_id|>
{pergunta}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    
    output = llm(prompt, max_tokens=1024, temperature=0.0, stop=["<|eot_id|>"])
    return output['choices'][0]['text'], contexto

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Gestão")
    
    if st.button("🗑️ Limpar Memória"):
        try:
            # Limpa sessão e banco
            if "cache_texto_completo" in st.session_state:
                del st.session_state.cache_texto_completo
            
            # Força a exclusão e recriação limpa
            client = chromadb.PersistentClient(path=DB_PATH)
            client.delete_collection("leis_federais")
            st.success("Memória Limpa! O sistema está pronto para novos PDFs.")
            # Força recarregamento da página para limpar variáveis globais
            st.rerun()
        except Exception as e:
            st.warning(f"Aviso: {e}")

    files = st.file_uploader("Normativos (PDF)", type="pdf", accept_multiple_files=True)
    if files and st.button("Processar"):
        st.session_state.cache_texto_completo = [] # Reseta o cache da RAM
        with st.spinner("Indexando Híbrido..."):
            for f in files:
                txt = ler_pdf_visual(f)
                
                # Chunk de 400 com overlap de 200 (Ideal para tabelas)
                chunks = [txt[i:i+400] for i in range(0, len(txt), 200)]
                
                # 1. Salva no Disco (Vetor)
                collection.add(documents=chunks, ids=[str(uuid.uuid4()) for _ in chunks])
                
                # 2. Salva na RAM (Busca Exata)
                st.session_state.cache_texto_completo.extend(chunks)
                
            st.success("Processado! (Modo Híbrido Ativo)")

st.subheader("Chat Jurídico Pro")

if "msg" not in st.session_state: st.session_state.msg = []

for m in st.session_state.msg:
    st.chat_message(m["role"]).write(m["content"])

if p := st.chat_input("Ex: Índice de Chuí ou regras para recém-empossados..."):
    st.chat_message("user").write(p)
    st.session_state.msg.append({"role": "user", "content": p})
    
    with st.spinner("Consultando..."):
        resp, ctx_debug = responder(p)
    
    st.chat_message("assistant").write(resp)
    st.session_state.msg.append({"role": "assistant", "content": resp})
    
    with st.expander("Ver Contexto (Debug)"):
        st.text(ctx_debug)