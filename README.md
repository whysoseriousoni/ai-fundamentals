# AI / ML Fundamentals

## Topics To Cover (Checklist)

### Models

- [ ] LLM
- [ ] SLM
- [ ] Context
- [ ] Memory
- [ ] Local Host
- [ ] Transformer Architecture
  - [ ] Attention
  - [ ] Self-attention
  - [ ] Positional Encoding
  - [ ] Encoder / Decoder
  - [ ] Decoder only
- [ ] Fine tuning
  - [ ]LoRA
  - [ ]QLorRA
  - [ ]PEFT
- [ ] Quantization
  - [ ]GGUF
  - [ ]GTPQ
  - [ ]AWQ
  - [ ]int8/int4
- [ ] Model Routing

### Database

- [ ] Vector DB
- [ ] Graph DB
- [ ] Redis for LLM
- [ ] Hybrid Search
- [ ] Metadata filtering
- [ ] Index Types
  - [ ] HNSW
  - [ ] IVF
  - [ ] Product Quantization
- Metrics
  - [ ] Recall@K
  - [ ] Precision@K
  - [ ] Mean Average Precision (MAP)
  - [ ] Context Precision
  - [ ] Mean Reciprocal Rank (MRR)

### Context Window Management

- [ ] Sliding Window
- [ ] Summarization-based compression
- [ ] RoPE Scaling

### Concepts

- [ ] RAG
- [ ] Context Engineering
- [ ] Prompt Engineering
- [ ] Chunking
- [ ] Vectors
- [ ] Tools
  - [ ] Creation
  - [ ] Versioning
  - [ ] Usage
  - [ ] API Key management
- [ ] Embedding
  - [ ] Language Agnostic Embedding
  - [ ] LaBSE (Language Agnostic BERT Sentence Embedding)

### Hallucination

- [ ] Hallucination
- [ ] Prevention
- [ ] Detection
- [ ] Grounding techniques
  - [ ] Citation
  - [ ] Source Attribution

### Scaling

- [ ]**** 1 Million documents
  - [ ] Insert
  - [ ] Search
  - [ ] Deleting
  - [ ] Versioning
  - [ ] Re-embed
- [ ] Latency optimization
  - [ ] Batching
  - [ ] Streaming responses
  - [ ] Speculative Decoding
- [ ] Rate limiting
- [ ] Concurrency Handling

### Agentic AI

- [ ] Agentic AI
- [ ] Multi agent orchestration
- [ ] Agent Memory
- [ ] Planning Strategies
  - [ ] ReAct
  - [ ] Plan and Execute
  - [ ] Reflexion
- [ ] Human in the loop patterns

### Guardrails

- [ ] Types of guardrails
- [ ] Working with Guardrails
- [ ] PII detection/redaction
- [ ] Prompt injection defense
- [ ] Output content moderation

### Evaluation (EVAL)

- [ ] Manual EVAL
- [ ] Automatic EVAL
- [ ] User Feedback inclusion
- [ ] Eval metrics
  - [ ] Faithfulness,
  - [ ] Relevance
  - [ ] Answer correctness
  - [ ] BLEU/ROUGE/BERTScore
- [ ] LLM-as-Judge
- [ ] Golden dataset / Test set curation
- [ ] Regression test
  - [ ] Prompt / Model Changes

### Performance Monitoring

- [ ] Logging
- [ ] Traceback
- [ ] Observability tooling
- [ ] Cost tracking per request/user
- [ ] A/B testing in production

### Tools

- [ ] Creating tools
- [ ] Managing tools
- [ ] Monitoring
- [ ] Performance

### Applications & Packages

- [ ] Lang graph
- [ ] Lang chain
- [ ] Lang Smith
- [ ] LlamaIndex (strong alternative/complement to LangChain for RAG)
- [ ] Vector DB SDKs: Pinecone, Weaviate, Qdrant, Milvus, pgvector
- [ ] MCP (Model Context Protocol) — increasingly central to tool/agent integration
- [ ] Guardrails libraries: Guardrails AI, NeMo Guardrails, Presidio (for PII)
- [ ] Eval frameworks
  - [ ] RAGAS
  - [ ] DeepEval
  - [ ] Promptfoo
  
### Text ML Concepts

- [ ] N-Grams
- [ ] Tokenization
- [ ] TF-IDF
- [ ] BM25
- [ ] Re-ranking
- [ ] Cosine similarity / Distance metrics
- [ ] (BPE) Byte pair encoding
- [ ] Sentence Piece

### Application Designing

- [ ] System to process 1 million documents
- [ ] 

### Security & Compliance

- [ ] Data privacy in LLM pipelines (PII leakage, data residency)
- [ ] Model/output audit trails
- [ ] Licensing considerations for open models

### Deployment

- [ ] Serving frameworks: vLLM, TGI, Ollama, TensorRT-LLM
- [ ] API gateway patterns for LLM services
- [ ] Blue-green/canary deployment for model updates
