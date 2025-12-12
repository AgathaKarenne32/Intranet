# 1. Usa Python 3.12 Leve (Linux)
FROM python:3.12-slim

# 2. Instala compiladores (Necessário para o Llama funcionar no Linux)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Cria a pasta do site dentro do Container
WORKDIR /app

# 4. Copia seus arquivos (app_time.py e o MODELO 3B) para dentro da imagem
COPY . .

# 5. Instala as bibliotecas
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Configura o Streamlit para rodar na porta certa
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# 7. Expõe a porta para o mundo
EXPOSE 8501

# 8. Comando que liga o site
CMD ["streamlit", "run", "app_time.py"]