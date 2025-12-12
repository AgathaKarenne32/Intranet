# 1. Base Python Leve
FROM python:3.12-slim

# 2. Instala ferramentas essenciais
RUN apt-get update && apt-get install -y     build-essential     curl     && rm -rf /var/lib/apt/lists/*

# 3. Pasta de trabalho
WORKDIR /app

# 4. TRUQUE DE MESTRE: Instalar PyTorch CPU *antes* do resto
# Isso impede que ele baixe os 4GB da Nvidia depois
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 5. Copia os arquivos
COPY . .

# 6. Instala o resto das bibliotecas
RUN pip install --upgrade pip &&     pip install --no-cache-dir -r requirements.txt

# 7. Configurações Finais
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
EXPOSE 8501
CMD ["streamlit", "run", "app_time.py"]
