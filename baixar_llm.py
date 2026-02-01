import os
from huggingface_hub import hf_hub_download

# Usando o repositório do Bartowski (padrão ouro para GGUF)
REPO_ID = "bartowski/Qwen2.5-7B-Instruct-GGUF"
# Nome exato do arquivo (Q4_K_M é o balanço perfeito entre velocidade e inteligência)
FILENAME = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
PASTA_DESTINO = "modelo_llm_7b_gguf"

print(f"⬇️ BAIXANDO O CÉREBRO 7B (Versão Bartowski)...")
print(f"📦 Arquivo: {FILENAME} (~4.5 GB)")

os.makedirs(PASTA_DESTINO, exist_ok=True)

try:
    caminho_arquivo = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=PASTA_DESTINO,
        local_dir_use_symlinks=False
    )
    print(f"\n✅ Download concluído com sucesso!")
    print(f"   Salvo em: {caminho_arquivo}")
except Exception as e:
    print(f"\n❌ Erro: {e}")