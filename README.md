# 🏛️ Assistente Jurídico Soberano (IA Intranet - Air Gapped)

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Optimized_CPU-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Security](https://img.shields.io/badge/Security-100%25_Offline-red?style=for-the-badge&logo=lock)
![AI Model](https://img.shields.io/badge/Model-Llama_3.2_3B_GGUF-green?style=for-the-badge)

Uma solução de Inteligência Artificial Generativa **privada e containerizada**, projetada para operar em ambientes de alta segurança (sem acesso à internet/Air-Gapped). O sistema analisa documentos internos (PDFs), editais e normativas, fornecendo respostas jurídicas fundamentadas sem risco de exfiltração de dados.

---

## 🎯 O Problema

O uso de IAs públicas (como ChatGPT ou Gemini) em órgãos governamentais apresenta riscos críticos:
* **Vazamento de Dados:** As informações enviadas são processadas em servidores estrangeiros.
* **Dependência de Internet:** Em operações táticas ou servidores seguros, nem sempre há acesso à web.
* **Alucinações Jurídicas:** Modelos genéricos falham em interpretar "Lógica Negativa" em editais (ex: *Fica afastada a exigência...*).

## 💡 A Solução

Desenvolvi um microserviço que roda o modelo **Llama 3.2 3B** localmente, otimizado para CPUs convencionais (sem necessidade de GPUs de alto custo). O sistema utiliza **RAG (Retrieval-Augmented Generation)** com uma camada de injeção lógica proprietária para garantir precisão normativa.

---

## 🛡️ Segurança e Privacidade (Arquitetura Zero-Trust)

A principal característica deste projeto é a **Soberania de Dados**.

* **🚫 Sem APIs Externas:** O sistema não se conecta à OpenAI, Google ou Meta. O cabo de rede pode ser desconectado e a IA continua funcionando.
* **🧠 Modelo Estático (GGUF):** O arquivo do modelo (`.gguf`) contém apenas pesos matemáticos (tensors). Ele **não é um executável**, impossibilitando a injeção de vírus ou backdoors ativos.
* **📦 Isolamento via Docker:** A aplicação roda em um container isolado do sistema operacional hospedeiro.
* **🧹 Memória Volátil:** Nenhum dado da consulta é salvo em disco permanentemente. Ao desligar o container, o contexto da sessão é destruído.

---

## 🚀 Como Usar (Implantação via Docker)

Devido ao tamanho do modelo, a entrega é feita via imagem Docker comprimida.

### 1. Pré-requisitos

* Computador com Docker Desktop instalado.
* Arquivo da imagem: `ia_completa.tar.gz` (aprox. 2.6GB).
* **Não é necessária conexão com a internet.**

### 2. Carregar a Imagem (Load)

No terminal, navegue até a pasta do arquivo e execute:

```bash
docker load -i ia_completa.tar.gz
````

### 3. Executar o Sistema (Run)

Inicie o servidor expondo a porta 8501:

docker run -p 8501:8501 ia-offline

### 4. Acessar

Abra o navegador e acesse:

No próprio PC: http://localhost:8501
Na Intranet (outro PC): http://IP_DO_COMPUTADOR:8501

## 🛠️ Detalhes Técnicos & Stack

Linguagem: Python 3.12 (Slim)
Framework Web: Streamlit
Motor de IA: `llama-cpp-python` (Compilado para CPU)
Banco Vetorial: ChromaDB (Persistência local de embeddings)
Otimização de Build: O `Dockerfile` foi configurado para ignorar bibliotecas CUDA (Nvidia) pesadas, focando em performance pura de CPU (`pytorch-cpu`), reduzindo a imagem final de 6GB para 2.6GB.

## 🧠 Algoritmo de "Raciocínio Híbrido"

Para combater alucinações em textos jurídicos complexos, implementei uma camada de interceptação em Python:

# Exemplo da lógica no backend (app_time.py)
if "afastada" in contexto and "estabilidade" in contexto:
    system_prompt += " ATENÇÃO: O texto diz que a estabilidade foi AFASTADA. Responda que PODE participar."

Isso força o modelo probabilístico a respeitar regras determinísticas da legislação.

## 📂 Estrutura do Projeto

/
├── app_time.py          # O cérebro da aplicação (Front + Back)
├── Dockerfile           # Receita de construção da imagem (Otimizada CPU)
├── requirements.txt     # Dependências Python
├── README.md            # Documentação
└── (Llama-3.2...gguf)   # Modelo (Não versionado no Git por tamanho)

Desenvolvido por Agatha Karenne Graduanda em Engenharia de Software | Estagiária em Desenvolvimento
