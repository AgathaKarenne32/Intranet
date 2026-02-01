import uvicorn
import os
import sqlite3
import traceback
from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager

from colbert_nativo import ColbertNativo
from ingestao_docling import processar_e_salvar
from cerebro import CerebroDigital

# Globais
motor = None
cerebro = None
log_erros = []
ARQUIVO_DB = "auditor.db"

def carregar_dados_do_sql():
    """Lê os dados do SQLite e formata para o ColBERT"""
    if not os.path.exists(ARQUIVO_DB):
        return []
    
    try:
        conn = sqlite3.connect(ARQUIVO_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT id, origem, conteudo FROM trechos")
        rows = cursor.fetchall()
        conn.close()
        
        # Converte para lista de dicionários (formato que o ColBERT gosta)
        dados = [{"id": r[0], "origem": r[1], "conteudo": r[2]} for r in rows]
        return dados
    except Exception as e:
        print(f"Erro ao ler SQL: {e}")
        return []

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n🚀 INICIANDO SERVIDOR SQLITE...")
    global motor, cerebro, log_erros
    
    # 1. ColBERT
    try: 
        print("   ⚙️ Carregando ColBERT...")
        motor = ColbertNativo()
        print("   ✅ ColBERT OK.")
    except Exception as e:
        log_erros.append(f"ColBERT Error: {e}")

    # 2. LLM (Qwen 7B GGUF)
    try: 
        print("   ⚙️ Carregando Cérebro...")
        cerebro = CerebroDigital()
        print("   ✅ Cérebro OK.")
    except Exception as e:
        log_erros.append(f"LLM Error: {e}")
    
    yield

app = FastAPI(lifespan=lifespan)

class Pergunta(BaseModel): texto: str
class Upload(BaseModel): nome_arquivo: str; conteudo_base64: str

@app.post("/perguntar")
def perguntar(req: Pergunta):
    global motor, cerebro, log_erros
    print(f"\n🔎 Pergunta: {req.texto}")
    
    if log_erros: return {"resposta": "Erro na inicialização", "detalhes": log_erros}
    
    # AGORA: Lemos o banco na hora da pergunta (garante dados frescos)
    # Se o banco ficar gigante (1 milhão de linhas), otimizaremos isso depois.
    banco_atual = carregar_dados_do_sql()
    
    if not banco_atual:
        return {"resposta": "Banco de dados vazio. Envie PDFs."}

    try:
        # Busca
        resultados = motor.buscar(req.texto, banco_atual, k=5)
        
        # IA
        lista_trechos = [f"Fonte: {r['id']}\nTexto: {r['conteudo']}" for r in resultados]
        fontes = [r['id'] for r in resultados]
        
        if cerebro and cerebro.model:
            resposta = cerebro.pensar(req.texto, lista_trechos)
        else:
            resposta = "IA indisponível. Veja fontes."

        return {"resposta": resposta, "fontes": fontes}
    except Exception as e:
        traceback.print_exc()
        return {"resposta": f"Erro: {e}"}

@app.post("/aprender")
def aprender(req: Upload):
    import base64
    try:
        if not os.path.exists("data"): os.makedirs("data")
        with open(f"data/{req.nome_arquivo}", "wb") as f:
            f.write(base64.b64decode(req.conteudo_base64))
        
        # Processa e grava no SQL
        processar_e_salvar()
        
        # Verifica quantos tem agora
        conn = sqlite3.connect(ARQUIVO_DB)
        qtd = conn.cursor().execute("SELECT COUNT(*) FROM trechos").fetchone()[0]
        conn.close()
        
        return {"status": "OK", "total_trechos_db": qtd}
    except Exception as e: return {"status": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)