import os
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

class ColbertNativo:
    def __init__(self):
        print("\n🔧 [BOOT] Inicializando ColBERT (PyTorch Nativo)...")
        
        # Nome oficial do modelo no HuggingFace
        modelo_nome = "colbert-ir/colbertv2.0"
        
        # Tenta achar pasta local 'modelo_colbert' para não baixar toda vez
        # Se não achar, baixa do HuggingFace automaticamente
        caminho_local = os.path.join(os.getcwd(), "modelo_colbert")
        
        try:
            if os.path.exists(caminho_local) and os.path.exists(os.path.join(caminho_local, "config.json")):
                print(f"   📂 Carregando modelo local: {caminho_local}")
                path_final = caminho_local
            else:
                print(f"   🌐 Baixando/Carregando modelo da nuvem: {modelo_nome}")
                path_final = modelo_nome

            # Carrega Tokenizer e Modelo
            self.tokenizer = AutoTokenizer.from_pretrained(path_final)
            self.model = AutoModel.from_pretrained(path_final)
            print("   ✅ Motor ColBERT pronto na memória!")
            
        except Exception as e:
            print(f"   ❌ Erro Crítico ao carregar modelo: {e}")
            raise e
            
        # Camada de projeção linear (Reduz de 768 para 128 dimensões - Padrão ColBERT)
        self.linear = torch.nn.Linear(768, 128, bias=False)
        self.model.eval()

    def _codificar(self, textos, max_length=512):
        if isinstance(textos, str): textos = [textos]
        
        with torch.no_grad():
            inputs = self.tokenizer(textos, return_tensors='pt', padding=True, truncation=True, max_length=max_length)
            outputs = self.model(**inputs)
            
            # Projeção e Normalização
            embeddings = self.linear(outputs.last_hidden_state)
            embeddings = F.normalize(embeddings, p=2, dim=2)
            
            # Remove padding (máscara)
            mask = inputs['attention_mask'].unsqueeze(-1)
            return embeddings * mask

    def buscar(self, query, lista_docs, k=5):
        if not lista_docs: return []
        print(f"   🧠 Comparando '{query}' contra {len(lista_docs)} trechos...")
        
        # 1. Vetoriza Pergunta
        Q = self._codificar([query], max_length=128)
        
        textos = []
        ids = []
        for item in lista_docs:
            textos.append(item['conteudo'])
            ids.append(item['id'])

        try:
            # 2. Vetoriza Documentos (Batch)
            # Dica: Se tiver mil docs, isso é rápido. Se tiver 1 milhão, precisaríamos de indexação FAISS.
            D = self._codificar(textos, max_length=512)
            
            # 3. MaxSim (A Mágica do ColBERT)
            # Q x D_transposto
            interacao = torch.matmul(Q, D.transpose(1, 2))
            max_scores = torch.max(interacao, dim=2).values
            total_scores = torch.sum(max_scores, dim=1)
            
            resultados = []
            for i in range(len(textos)):
                resultados.append({
                    "id": ids[i], 
                    "score": total_scores[i].item(), 
                    "conteudo": textos[i]
                })
            
            resultados.sort(key=lambda x: x['score'], reverse=True)
            return resultados[:k]
            
        except Exception as e:
            print(f"❌ Erro matemático na busca: {e}")
            return []