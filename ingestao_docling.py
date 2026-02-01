import os
import re
import sqlite3
import time
import traceback
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat

# --- CONFIGURAÇÕES DE VELOCIDADE (MEXA AQUI) ---
# Se o PDF for texto digital (selecionável), coloque USAR_OCR = False (Fica instantâneo)
# Se o PDF for escaneado (imagem), coloque USAR_OCR = True (Demora, mas funciona)
USAR_OCR = True 

# Se estiver MUITO lento, coloque False. A IA de tabelas é pesada na CPU.
# Nossa "Janela Deslizante" já ajuda a pegar tabelas, então podemos desligar isso para ganhar velocidade.
USAR_IA_TABELAS = False 
# -----------------------------------------------

PASTA_DATA = "data"
ARQUIVO_DB = "auditor.db"

# Configuração de Corte
TAMANHO_CHUNK = 1000  
OVERLAP = 200         

def limpar_texto(texto):
    return re.sub(r'\n+', '\n', texto).strip()

def criar_chunks_deslizantes(texto, tamanho=TAMANHO_CHUNK, overlap=OVERLAP):
    inicio = 0
    total = len(texto)
    while inicio < total:
        fim = min(inicio + tamanho, total)
        pedaco = texto[inicio:fim]
        if fim < total:
            ultimo_espaco = pedaco.rfind(' ')
            if ultimo_espaco != -1:
                fim = inicio + ultimo_espaco
                pedaco = texto[inicio:fim]
        yield pedaco
        inicio += (len(pedaco) - overlap)
        if len(pedaco) < overlap: break

def inicializar_banco():
    conn = sqlite3.connect(ARQUIVO_DB, timeout=30)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trechos (
            id TEXT PRIMARY KEY,
            origem TEXT,
            conteudo TEXT,
            data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def processar_e_salvar():
    print("="*50)
    print("🚀 INICIANDO INGESTÃO CONFIGURÁVEL")
    print(f"   ⚙️  MODO OCR: {'[LIGADO]' if USAR_OCR else '[DESLIGADO] (Modo Turbo)'}")
    print(f"   ⚙️  IA DE TABELAS: {'[LIGADA]' if USAR_IA_TABELAS else '[DESLIGADA] (Ganho de Velocidade)'}")
    print("="*50)
    
    if not os.path.exists(PASTA_DATA):
        print("   ⚠️ Pasta data não existe.")
        return

    arquivos = [f for f in os.listdir(PASTA_DATA) if f.lower().endswith(".pdf")]
    if not arquivos:
        print("   ⚠️ Nenhum PDF encontrado.")
        return

    try:
        conn = inicializar_banco()
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ Erro ao abrir banco: {e}")
        return

    try:
        pipeline = PdfPipelineOptions()
        pipeline.do_ocr = USAR_OCR
        pipeline.do_table_structure = USAR_IA_TABELAS
        
        # Otimização extra: Se desligar tabelas, usa modo rápido
        if not USAR_IA_TABELAS:
            pipeline.table_structure_options.mode = TableFormerMode.FAST

        converter = DocumentConverter(format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)
        })
    except Exception as e:
        print(f"❌ Erro config Docling: {e}")
        return

    for arq in arquivos:
        print(f"   📖 Lendo: {arq}...")
        inicio_tempo = time.time()
        
        try:
            caminho_completo = os.path.join(PASTA_DATA, arq)
            
            # Conversão
            print("      ...Processando IA (Isso consome CPU)...")
            res = converter.convert(caminho_completo)
            texto_limpo = limpar_texto(res.document.export_to_markdown())
            
            # Validação simples
            if len(texto_limpo) < 100 and not USAR_OCR:
                print("      ⚠️ AVISO: O texto saiu vazio. Esse PDF parece ser uma imagem.")
                print("      ⚠️ Mude USAR_OCR = True no código e tente de novo.")
                continue

            print(f"      💾 Gravando no Banco de Dados...")
            novos = 0
            for i, pedaco in enumerate(criar_chunks_deslizantes(texto_limpo)):
                uid = f"{arq}_part_{i}"
                try:
                    cursor.execute('INSERT OR REPLACE INTO trechos (id, origem, conteudo) VALUES (?, ?, ?)', (uid, arq, pedaco))
                    novos += 1
                except sqlite3.OperationalError: pass
                
                if novos % 50 == 0: conn.commit()

            conn.commit()
            tempo_total = time.time() - inicio_tempo
            print(f"      ✅ Finalizado em {tempo_total:.1f} segundos. ({novos} trechos)")
            
        except Exception as e:
            print(f"      ❌ Erro em {arq}: {e}")
            traceback.print_exc()

    conn.close()
    print("\n✨ Processo Finalizado!")

if __name__ == "__main__":
    processar_e_salvar()