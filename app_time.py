import streamlit as st
from llama_cpp import Llama
from pypdf import PdfReader
import chromadb
from chromadb.utils import embedding_functions
import uuid
import os
import socket

# --- CONFIGURAÇÃO DE REDE ---
hostname = socket.gethostname()
ip_interno = socket.gethostbyname(hostname)

st.set_page_config(page_title="IA Segura (Intranet)", layout="wide")
st.title(f"🔒 IA Corporativa - Rodando em {ip_interno}")
st.info(f"Para seu time acessar, peça para digitarem: http://{ip_interno}:8501")

# --- CARREGAR MODELO LOCAL ---
@st.cache_resource
def carregar_ia_segura():
    # Caminho ajustado para a pasta C:\Lab
    caminho = "./Llama-3.2-1B-Instruct-Q4_K_M.gguf"
        
    if not os.path.exists(caminho):
        st.error(f"❌ Modelo não encontrado em {caminho}")
        return None

    # n_ctx=2048 limita a memória para não travar o PC
    return Llama(model_path=caminho, n_ctx=2048, verbose=False)

# --- BANCO DE DADOS ---
@st.cache_resource
def iniciar_banco():
    client = chromadb.PersistentClient(path="./memoria_segura")
    embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return client.get_or_create_collection(name="docs_rh", embedding_function=embed)

try:
    llm = carregar_ia_segura()
    collection = iniciar_banco()
except Exception as e:
    st.error(f"Erro inicialização: {e}")

# --- LÓGICA DE NEGÓCIO ---
def ler_pdf(arquivo):
    pdf = PdfReader(arquivo)
    return "".join([p.extract_text() + "\n" for p in pdf.pages])

# --- AQUI ESTÁ A MUDANÇA MÁGICA (PROMPT ENGENHARIA) ---
def responder(pergunta):
    # 1. Busca os trechos no PDF
    res = collection.query(query_texts=[pergunta], n_results=3)
    
    if not res['documents'] or not res['documents'][0]: 
        return "Não encontrei informações no documento sobre isso."
    
    # Pega o texto do PDF
    ctx = "\n".join(res['documents'][0])
    
    # 2. O Prompt "Professor Bravo"
    # O modelo 1B precisa de instrução EXPLICITA e REPETITIVA
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Você é um Assistente Jurídico Estrito. Responda baseando-se APENAS no contexto abaixo.

TABELA DE REGRAS (Siga estritamente):
1. Se o texto diz "Fica afastada a exigência de estabilidade" -> A RESPOSTA É: "SIM, é permitido participar."
2. Se o texto diz "Vedado" -> A RESPOSTA É: "NÃO é permitido."
3. Se não souber, diga "Não consta no texto".

CONTEXTO DO PDF:
{ctx}
<|eot_id|><|start_header_id|>user<|end_header_id|>
Com base na Tabela de Regras acima, responda: {pergunta}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    
    # Temperature 0.1 = Criatividade quase Zero (Para ele não inventar moda)
    output = llm(prompt, max_tokens=256, temperature=0.1, stop=["<|eot_id|>"])
    return output['choices'][0]['text']

# --- INTERFACE ---
with st.sidebar:
    st.write("📂 **Upload Seguro**")
    up = st.file_uploader("PDF", type="pdf")
    if up and st.button("Gravar na Memória"):
        if up is not None:
            with st.spinner("Lendo e aprendendo..."):
                txt = ler_pdf(up)
                # Corta o texto em pedaços menores para caber na memória
                chunks = [txt[i:i+800] for i in range(0, len(txt), 700)]
                collection.add(documents=chunks, ids=[str(uuid.uuid4()) for _ in chunks], metadatas=[{"fonte": up.name} for _ in chunks])
            st.success("Documento aprendido!")

# Chat
if "historico" not in st.session_state: st.session_state.historico = []

for msg in st.session_state.historico:
    st.chat_message(msg["role"]).write(msg["content"])

if p := st.chat_input("Dúvida interna..."):
    st.chat_message("user").write(p)
    st.session_state.historico.append({"role": "user", "content": p})
    
    with st.spinner("Consultando normas..."):
        resp = responder(p)
    
    st.chat_message("assistant").write(resp)
    st.session_state.historico.append({"role": "assistant", "content": resp})