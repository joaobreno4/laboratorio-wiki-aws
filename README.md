# Laboratório — Wiki Inteligente AWS
### Agente de Gestão de Base de Conhecimentos com RAG Serverless

> **Desafio DIO** — Construção de um Pipeline RAG (Retrieval-Augmented Generation) Serverless e Event-Driven na AWS para indexação e consulta de documentos heterogêneos em linguagem natural.

---

##  Arquitetura

```
┌──────────────────────────────────────────────────┐
│              INGESTÃO & PROCESSAMENTO             │
│                                                  │
│  [S3 raw-bucket]                                 │
│       │                                          │
│       ▼  (S3 Event / EventBridge)                │
│  [Lambda Router]                                 │
│       │                                          │
│  ┌────┼────────────────────┐                     │
│  ▼    ▼                    ▼                     │
│ PDF  IMG/Scan             CSV                    │
│ PyPDF Textract OCR        Glue/Lambda            │
│  └────┼────────────────────┘                     │
│       ▼                                          │
│  [S3 processed-bucket — JSON]                    │
└──────────────────────────────────────────────────┘
                    │
┌──────────────────────────────────────────────────┐
│               INDEXAÇÃO & CONSULTA               │
│                                                  │
│  [Bedrock Knowledge Bases]                       │
│       │              │                           │
│  [Titan Embeddings]  [OpenSearch Serverless]     │
│                           │                      │
│  [Claude 3.5 Sonnet] ◄────┘                     │
│       │                                          │
│  [Resposta + Citação de Fonte]                   │
└──────────────────────────────────────────────────┘
```

##  Estrutura do Repositório

```
laboratório-wiki-aws/
├── README.md               # Este arquivo
├── resposta.md             # Proposta de arquitetura completa (entrega DIO)
├── architecture/
│   └── diagram.md          # Detalhamento da arquitetura por componente
└── lambda/
    ├── router/             # Lambda de classificação e roteamento
    ├── pdf_processor/      # Extração de texto de PDFs nativos
    └── csv_processor/      # Transformação semântica de CSV
```

## Serviços AWS Utilizados

| Serviço | Função |
|---|---|
| Amazon S3 | Landing zone bruta + camada processada |
| AWS Lambda | Router + processadores de PDF e CSV |
| Amazon Textract | OCR avançado com handwriting |
| AWS Glue | ETL de grandes volumes CSV |
| Amazon Bedrock Knowledge Bases | Orquestrador RAG |
| Amazon Titan Text Embeddings v2 | Geração de embeddings |
| Amazon OpenSearch Serverless | Vector Store (k-NN) |
| Anthropic Claude 3.5 Sonnet | LLM de geração de respostas |

## Entrega

A proposta completa de arquitetura encontra-se em **[resposta.md](./resposta.md)**.
