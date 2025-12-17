# 1. Base Python Leve
FROM python:3.12-slim

# 2. Instala ferramentas do sistema operacional
# build-essential: para compilar bibliotecas C++ (necessário para ChromaDB/Llama)
# curl: para testes de saúde
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Pasta de trabalho
WORKDIR /app

# 4. TRUQUE DE MESTRE: PyTorch CPU
# Instala antes para evitar baixar drivers de placa de vídeo (economiza 4GB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 5. Otimização de Cache: Copia só os requisitos primeiro
# Isso faz com que o Docker não reinstale tudo se você mudar só uma linha de código
COPY requirements.txt .

# 6. Instala as bibliotecas Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6.1. NOVIDADE: Baixar o Cérebro do Spacy (NER)
# Isso garante que o modelo de língua portuguesa esteja dentro da imagem
RUN python -m spacy download pt_core_news_lg

# 7. Copia o resto do código (app_time.py, modelo .gguf, etc)
COPY . .

# 8. Configurações de Rede e Execução
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
EXPOSE 8501

CMD ["streamlit", "run", "app_time.py"]