import streamlit as st
from llama_cpp import Llama
import fitz  # PyMuPDF
import chromadb
from chromadb.utils import embedding_functions
import uuid
import os
import socket
import re
from rank_bm25 import BM25Okapi
import spacy

# --- 1. CONFIGURAÇÃO ---
hostname = socket.gethostname()
try:
    ip_interno = socket.gethostbyname(hostname)
except:
    ip_interno = "localhost"

st.set_page_config(page_title="IA Federal Pro", layout="wide", page_icon="👮‍♂️")
st.title(f"👮‍♂️ IA Assistente de Legislação (Server: {ip_interno})")

# --- 2. CARREGAMENTO DE MODELOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
DB_PATH = os.path.join(BASE_DIR, "banco_vetorial")

# A. Cérebro Llama (Cacheado)
@st.cache_resource
def carregar_cerebro():
    if not os.path.exists(MODEL_PATH):
        st.error(f"Modelo não encontrado: {MODEL_PATH}")
        return None
    return Llama(model_path=MODEL_PATH, n_ctx=8192, n_threads=4, verbose=False)

# B. NER Spacy (Modelo Large - Rápido e Preciso)
@st.cache_resource
def carregar_ner():
    try:
        print("A carregar modelo spaCy Large...")
        # Carrega o modelo que você acabou de instalar com sucesso
        nlp = spacy.load("pt_core_news_lg")
        return nlp
    except Exception as e:
        st.error(f"Erro ao carregar spaCy: {e}")
        return None

# C. Banco Vetorial (Sem Cache para evitar erros de conexão)
def carregar_memoria():
    os.makedirs(DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=DB_PATH)
    embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return client.get_or_create_collection(name="leis_federais", embedding_function=embed)

llm = carregar_cerebro()
nlp = carregar_ner()
collection = carregar_memoria()

# --- 3. FUNÇÕES DE LEITURA E PROCESSAMENTO ---
def ler_pdf_visual(uploaded_file):
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    texto = ""
    for pagina in doc:
        # sort=True organiza a leitura visualmente (Crucial para Tabelas)
        texto += pagina.get_text("text", sort=True) + "\n"
    return texto

def tokenizar_texto(texto):
    # Prepara o texto para o BM25 (remove pontuação simples)
    return re.findall(r'\b\w+\b', texto.lower())

# --- 4. BUSCA TRI-HÍBRIDA (VETOR + BM25 + NER) ---
def buscar_hibrido(pergunta):
    docs_finais = []
    
    # 1. ANÁLISE DA PERGUNTA COM NER (A Inteligência)
    entidades_pergunta = []
    if nlp:
        doc_pergunta = nlp(pergunta)
        for ent in doc_pergunta.ents:
            entidades_pergunta.append(ent.text)
            print(f"🤖 NER detectou na pergunta: {ent.text} ({ent.label_})")

    # A. Busca Vetorial (Contexto Semântico)
    try:
        res_vetor = collection.query(query_texts=[pergunta], n_results=10)
        docs_vetor = res_vetor['documents'][0] if res_vetor['documents'] else []
        docs_finais.extend(docs_vetor)
    except:
        pass

    # B. Busca BM25 (Raridade / Palavra-Chave)
    if "bm25_objeto" in st.session_state and "corpus_textos" in st.session_state:
        tokens_pergunta = tokenizar_texto(pergunta)
        # Pede os 5 melhores trechos baseados na estatística das palavras
        docs_bm25 = st.session_state.bm25_objeto.get_top_n(tokens_pergunta, st.session_state.corpus_textos, n=5)
        docs_finais.extend(docs_bm25)

    # C. Busca por Entidade (NER Reverso)
    # Se a pergunta tem uma entidade (ex: Chuí), procura onde ela aparece nos metadados
    if "entidades_indexadas" in st.session_state and entidades_pergunta:
        for ent_p in entidades_pergunta:
            for i, lista_ents_chunk in enumerate(st.session_state.entidades_indexadas):
                # Verifica se a entidade da pergunta está na lista de entidades do bloco
                if any(ent_p.lower() in e.lower() for e in lista_ents_chunk):
                    docs_finais.append(st.session_state.corpus_textos[i])
    
    # Remove duplicados e junta tudo
    return "\n---\n".join(list(set(docs_finais)))

def responder(pergunta):
    contexto = buscar_hibrido(pergunta)
    
    if not contexto:
        return "ERRO: Não encontrei nada relevante.", ""
    
    # Prompt Refinado para Resolver o Conflito de Regras
    prompt = f"""<|start_header_id|>system<|end_header_id|>
Você é um Auditor Sênior da Polícia Federal.
Sua missão é interpretar o regulamento com precisão jurídica.

⚠️ HIERARQUIA DAS REGRAS (IMPORTANTE):
1. O **Artigo 34** (Disposições Finais) é uma EXCEÇÃO SUPREMA. Ele diz explicitamente: "Fica afastada a exigência da estabilidade".
2. Se o texto citar o Art. 34, ele ANULA qualquer regra anterior (como Art. 4, 16 ou 20) que exija estabilidade.
3. Se o usuário for "recém-empossado", "novo" ou "estágio probatório", a resposta é **SIM**, ele pode participar (baseado no Art. 34).

PARA TABELAS:
- Responda apenas o valor exato encontrado ao lado da cidade.

CONTEXTO ENCONTRADO:
{contexto}
<|eot_id|><|start_header_id|>user<|end_header_id|>
{pergunta}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    
    output = llm(prompt, max_tokens=1024, temperature=0.0, stop=["<|eot_id|>"])
    return output['choices'][0]['text'], contexto

# --- 5. INTERFACE ---
with st.sidebar:
    st.header("🗂️ Gestão Inteligente")
    
    if st.button("🗑️ Limpar Memória"):
        try:
            # Limpa sessão
            for key in ["bm25_objeto", "corpus_textos", "entidades_indexadas"]:
                if key in st.session_state: del st.session_state[key]
            # Limpa banco vetorial
            client = chromadb.PersistentClient(path=DB_PATH)
            client.delete_collection("leis_federais")
            st.success("Memória limpa. O sistema está pronto.")
            st.rerun()
        except:
            pass

    files = st.file_uploader("Normativos (PDF)", type="pdf", accept_multiple_files=True)
    if files and st.button("Processar (Vetor + BM25 + Transformer)"):
        # Listas temporárias
        corpus_para_bm25 = []
        tokenized_corpus = []
        lista_entidades_chunks = [] 
        
        with st.spinner("A ler PDF e a aplicar Rede Neural (Transformer)... Isto pode demorar um pouco."):
            for f in files:
                txt = ler_pdf_visual(f)
                # Chunk de 500 caracteres
                chunks = [txt[i:i+500] for i in range(0, len(txt), 250)]
                
                # 1. Indexação Vetorial
                collection.add(documents=chunks, ids=[str(uuid.uuid4()) for _ in chunks])
                
                for chunk in chunks:
                    # 2. Indexação BM25
                    corpus_para_bm25.append(chunk)
                    tokenized_corpus.append(tokenizar_texto(chunk))
                    
                    # 3. Indexação NER (Transformer)
                    if nlp:
                        doc = nlp(chunk)
                        # Guarda apenas o texto das entidades encontradas (LOC, PER, ORG, etc.)
                        ents = [e.text for e in doc.ents]
                        lista_entidades_chunks.append(ents)
                    else:
                        lista_entidades_chunks.append([])

            # Guarda tudo na memória RAM (Session State)
            st.session_state.bm25_objeto = BM25Okapi(tokenized_corpus)
            st.session_state.corpus_textos = corpus_para_bm25
            st.session_state.entidades_indexadas = lista_entidades_chunks
            
            st.success(f"Sucesso! {len(corpus_para_bm25)} blocos processados com Inteligência Máxima.")

st.subheader("Chat Jurídico Pro (Neural)")

if "msg" not in st.session_state: st.session_state.msg = []

for m in st.session_state.msg:
    st.chat_message(m["role"]).write(m["content"])

if p := st.chat_input("Ex: Índice de Chuí, Barreiras ou regras de posse..."):
    st.chat_message("user").write(p)
    st.session_state.msg.append({"role": "user", "content": p})
    
    with st.spinner("A investigar com múltiplas camadas de IA..."):
        resp, ctx_debug = responder(p)
    
    st.chat_message("assistant").write(resp)
    st.session_state.msg.append({"role": "assistant", "content": resp})
    
    with st.expander("Ver Contexto (Debug)"):
        st.text(ctx_debug)