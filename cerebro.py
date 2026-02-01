import os
import sys
# Tenta importar o Llama, se falhar avisa o usuário
try:
    from llama_cpp import Llama
except ImportError:
    print("❌ Erro: Biblioteca llama-cpp-python não instalada.")
    sys.exit()

class CerebroDigital:
    def __init__(self):
        print("\n🧠 [BOOT] Inicializando Qwen 7B (GGUF)...")
        
        # Caminho exato do novo arquivo
        nome_arquivo = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
        caminho_modelo = os.path.join("modelo_llm_7b_gguf", nome_arquivo)
        
        if not os.path.exists(caminho_modelo):
            print(f"❌ ERRO CRÍTICO: Não achei o arquivo {nome_arquivo}")
            print(f"   Esperava em: {caminho_modelo}")
            print("   Rode o 'baixar_llm.py' novamente.")
            self.model = None
            return

        try:
            # Carrega o modelo
            # n_gpu_layers=0 garante que vai rodar só na CPU e RAM
            self.model = Llama(
                model_path=caminho_modelo,
                n_ctx=4096,      # Contexto (leitura) de 4096 tokens
                n_threads=6,     # Usa mais núcleos do seu processador
                n_gpu_layers=0,  # Força CPU
                verbose=False
            )
            print("   ✅ Cérebro 7B Carregado na Memória!")
            
        except Exception as e:
            print(f"   ❌ Erro ao carregar LlamaCPP: {e}")
            self.model = None

    def pensar(self, pergunta, contextos):
        if not self.model: return "Erro: Cérebro não iniciou."

        texto_contexto = "\n\n".join(contextos)
        
        prompt_sistema = (
            "Você é um Auditor Federal Sênior. "
            "Analise o contexto jurídico abaixo e responda à pergunta com precisão. "
            "Cite a fonte (Instrução Normativa, Lei, etc) sempre que possível."
        )
        
        messages = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Contexto:\n{texto_contexto}\n\nPergunta: {pergunta}"}
        ]
        
        print("   🤔 O Auditor 7B está pensando...")
        
        output = self.model.create_chat_completion(
            messages=messages,
            max_tokens=1024,
            temperature=0.1
        )
        
        return output['choices'][0]['message']['content']