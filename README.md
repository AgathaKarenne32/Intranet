# 👮‍♂️ IA Assistente de Legislação (Federal Pro)

Este projeto é um assistente jurídico baseado em RAG (Retrieval-Augmented Generation), projetado para interpretar normativos da Polícia Federal, responder dúvidas sobre legislação e consultar tabelas de índices de localidades.

---

## 🚀 Atualização de Arquitetura: A Evolução para RAG Tri-Híbrido

Nas últimas versões, realizamos uma reformulação drástica no motor de busca da IA. Saímos de uma abordagem puramente Vetorial (ChromaDB) para uma abordagem **Tri-Híbrida (Vetorial + BM25 + NER)**.

Abaixo detalhamos os motivos técnicos, as vulnerabilidades encontradas no modelo anterior e a solução implementada.

### 🚩 Vulnerabilidades e Problemas Encontrados (Post-Mortem)

Durante os testes de estresse (commits anteriores), identificamos três falhas críticas na arquitetura de busca vetorial simples:

#### 1. O Paradoxo das Tabelas Dispersas ("O Problema do Chuí")
* **Sintoma:** A IA respondia "Não consta" ou alucinava valores ao perguntar sobre índices em tabelas (ex: "Qual o índice de Chuí?").
* **Causa Técnica:** A Busca Vetorial (Embeddings) baseia-se em **densidade semântica**. Páginas de tabelas (ex: Página 14 do PDF) contêm apenas listas de nomes e números, sem frases conectivas ("O índice é..."). Para o modelo vetorial, essas páginas parecem "ruído" ou têm baixa relevância semântica comparadas a textos explicativos.
* **Falha:** O banco vetorial ignorava a página da tabela, impedindo a recuperação do dado exato (3.75).

#### 2. O Conflito de Regras (Regra Geral vs. Exceção)
* **Sintoma:** Ao perguntar "Sou recém-empossado, posso participar?", a IA respondia **NÃO** (baseado no Art. 20), ignorando a exceção do **Art. 34** ("Fica afastada a exigência...").
* **Causa Técnica:** O Artigo 20 (proibição) repete palavras-chave como "concurso" e "participação" várias vezes. O Artigo 34 (permissão) é curto e está no final do documento. O algoritmo de similaridade priorizava o texto mais denso (Art. 20), ocultando a exceção.

#### 3. A Limitação do "Hardcoding" (Busca Manual)
* **Tentativa Anterior:** Tentamos corrigir os problemas acima com `if "chuí" in texto`.
* **Vulnerabilidade:** Essa abordagem não é escalável. Exigiria escrever o nome de todas as 5.570 cidades do Brasil no código. Além disso, não funcionaria para novos PDFs com estruturas diferentes.

---

### 🛡️ A Nova Solução: Arquitetura Tri-Híbrida

Para resolver esses problemas de forma universal (sem regras manuais), implementamos três camadas de recuperação de informação:

| Camada | Tecnologia | Função Específica | Resolve Qual Problema? |
| :--- | :--- | :--- | :--- |
| **1. Semântica** | **ChromaDB** (Embeddings) | Entende o *sentido* da pergunta (ex: "Como funciona o cálculo?"). | Perguntas conceituais e interpretação de texto. |
| **2. Léxica (Raridade)** | **Rank-BM25** (TF-IDF) | Calcula a estatística de palavras. Dá peso alto para palavras raras (ex: "Empossado", "Chuí") e ignora palavras comuns. | **Tabelas e Regras Específicas.** Garante que o Art. 34 e a cidade Chuí sejam encontrados pela exatidão da palavra. |
| **3. Entidades (NER)** | **spaCy** (Large Model) | Identifica *o que* são as palavras (Locais, Pessoas, Organizações). | **Desambiguação.** Permite listar "quais cidades aparecem no texto" mesmo que a formatação mude. |

### 🧠 Engenharia de Prompt (Hierarquia Jurídica)

Além da busca, refinamos o "System Prompt" do modelo Llama 3.2 para respeitar a hierarquia das normas:

> *"⚠️ HIERARQUIA DAS REGRAS: Se o texto citar o Art. 34 (Disposições Finais), ele ANULA qualquer regra anterior de proibição. Priorize exceções explícitas."*

Isso eliminou as alucinações onde a IA tinha "medo" de contradizer a regra geral.

---

## 📦 Instalação e Dependências

Devido à inclusão de motores de PNL (Processamento de Linguagem Natural), novas bibliotecas são necessárias:

```bash
# Instalar bibliotecas de busca e processamento
pip install rank_bm25 spacy

# Baixar o modelo de linguagem em Português (Large)
python -m spacy download pt_core_news_lg