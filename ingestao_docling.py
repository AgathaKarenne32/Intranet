import os
import re
import sqlite3
import traceback
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

PASTA_DATA = "data"
ARQUIVO_DB = "auditor.db"

# CONFIGURAÇÃO DE CORTE
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
    # Timeout de 30s para evitar travamentos
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
    print("🚀 INICIANDO INGESTÃO TURBO (SEM OCR)...")
    
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

    # --- AQUI ESTÁ A MUDANÇA ---
    try:
        pipeline = PdfPipelineOptions()
        pipeline.do_ocr = False  # <--- DESLIGADO PARA VELOCIDADE MÁXIMA
        pipeline.do_table_structure = True # Mantém inteligência de tabelas
        
        converter = DocumentConverter(format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)
        })
    except Exception as e:
        print(f"❌ Erro config Docling: {e}")
        return

    for arq in arquivos:
        print(f"   📖 Lendo RÁPIDO: {arq}...")
        try:
            caminho_completo = os.path.join(PASTA_DATA, arq)
            
            # Converte
            res = converter.convert(caminho_completo)
            texto_limpo = limpar_texto(res.document.export_to_markdown())
            
            # Verifica se leu algo (se vier vazio, o PDF precisava de OCR)
            if len(texto_limpo) < 50:
                print(f"      ⚠️ ALERTA: O texto veio vazio! Esse PDF parece ser uma imagem escaneada.")
                print(f"      ⚠️ Você precisará ativar o OCR novamente e esperar.")
                continue

            print(f"      💾 Salvando trechos...")
            
            novos = 0
            for i, pedaco in enumerate(criar_chunks_deslizantes(texto_limpo)):
                uid = f"{arq}_part_{i}"
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO trechos (id, origem, conteudo) 
                        VALUES (?, ?, ?)
                    ''', (uid, arq, pedaco))
                    novos += 1
                except sqlite3.OperationalError:
                    pass # Ignora erros de lock momentâneos

                if novos % 100 == 0:
                    conn.commit()

            conn.commit()
            print(f"      ✅ {novos} trechos gravados em segundos.")
            
        except Exception as e:
            print(f"      ❌ Erro em {arq}: {e}")
            traceback.print_exc()

    conn.close()
    print("✨ Processo Finalizado!")

if __name__ == "__main__":
    processar_e_salvar()