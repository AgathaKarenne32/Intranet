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
