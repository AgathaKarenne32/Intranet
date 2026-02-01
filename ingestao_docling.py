import os
import re
import sqlite3
import traceback 
import time
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

USAR_OCR = False

PASTA_DATA = "data"
ARQUIVO_DB = "auditor.db"
TAMANHO_CHUNK = 1000
OVERLAP = 50


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

        if len(pedaco) < overlap:
            break


def conectar_banco():
    conn = sqlite3.connect(ARQUIVO_DB, timeout=60)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trechos (
            id TEXT PRIMARY KEY,
            origem TEXT,
            conteudo TEXT,
            data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    return conn


def processar():
    print("🐧 INICIANDO INGESTÃO COM DOCLING (OTIMIZADA)")
    print(f"   ⚙️ OCR: {'LIGADO' if USAR_OCR else 'DESLIGADO'}")

    if not os.path.exists(PASTA_DATA):
        print("❌ Pasta 'data' não existe.")
        return

    arquivos = [f for f in os.listdir(PASTA_DATA) if f.lower().endswith(".pdf")]
    if not arquivos:
        print("⚠️ Nenhum PDF encontrado.")
        return

    try:
        pipeline = PdfPipelineOptions(
        do_ocr=False,
        do_table_structure=False,
        generate_page_images=False,
        extract_images=False,
    )

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)
            }
        )
    except Exception as e:
        print(f"❌ Erro ao configurar Docling: {e}")
        return

    conn = conectar_banco()
    cursor = conn.cursor()

    for idx, arq in enumerate(arquivos, 1):
        caminho = os.path.join(PASTA_DATA, arq)
        print(f"\n📄 [{idx}/{len(arquivos)}] Processando {arq}")

        inicio = time.time()

        try:
            t0 = time.time()
            res = converter.convert(caminho)
            print(f"   ⏱️ Conversão: {time.time() - t0:.2f}s")

            t1 = time.time()
            # Forma mais robusta de extrair o conteúdo textual
            texto = res.document.export_to_markdown() 
            # Ou se preferir manter o formato de blocos:
            # texto = "\n".join([item.text for item, _ in res.document.iterate_items() if hasattr(item, 'text')])

            print(f"   ⏱️ Extração: {time.time() - t1:.2f}s")

            texto_limpo = limpar_texto(texto)

            if not texto_limpo:
                print("⚠️ Texto vazio.")
                continue

            lote = []
            for i, chunk in enumerate(criar_chunks_deslizantes(texto_limpo)):
                lote.append((f"{arq}_part_{i}", arq, chunk))

            cursor.executemany(
                "INSERT OR REPLACE INTO trechos (id, origem, conteudo) VALUES (?, ?, ?)",
                lote
            )
            conn.commit()

            print(f"   ✅ {len(lote)} trechos salvos em {time.time() - inicio:.2f}s")

        except Exception as e:
            # Esta linha precisa estar recuada com 1 tab ou 4 espaços
            print(f"❌ Erro ao processar {arq}: {e}")
            import traceback
            traceback.print_exc()

    conn.close()
    print("\n🏁 INGESTÃO FINALIZADA COM SUCESSO")

if __name__ == "__main__":
    processar()
