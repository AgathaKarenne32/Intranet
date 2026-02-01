import requests
import base64
import os

# --- CONFIGURAÇÃO ---
ARQUIVO_PDF = "IN 276_2024.pdf" # <-- Mude para o nome do seu arquivo
URL_API = "http://localhost:8000/aprender"

def enviar():
    if not os.path.exists(ARQUIVO_PDF):
        print(f"❌ Arquivo '{ARQUIVO_PDF}' não encontrado na pasta atual.")
        return

    print(f"📦 Preparando envio de: {ARQUIVO_PDF}...")
    with open(ARQUIVO_PDF, "rb") as f:
        pdf_bytes = f.read()
        b64 = base64.b64encode(pdf_bytes).decode('utf-8')

    payload = {
        "nome_arquivo": ARQUIVO_PDF,
        "conteudo_base64": b64
    }

    print("📡 Enviando para o Auditor...")
    try:
        resp = requests.post(URL_API, json=payload)
        print("✅ Resposta do Servidor:")
        print(resp.json())
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        print("   (Verifique se api_auditor.py está rodando)")

if __name__ == "__main__":
    enviar()