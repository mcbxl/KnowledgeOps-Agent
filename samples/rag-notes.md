# RAG Retrieval Notes

Hybrid search combines lexical retrieval and semantic retrieval. Lexical retrieval is useful for exact names, API symbols, error codes, and version strings.

## Semantic Retrieval

Embedding retrieval is useful for conceptual questions, paraphrased questions, summaries, and broad topic exploration.

## Rerank

A reranker improves the final ordering by scoring the query and candidate chunk together. Production systems often use cross-encoders or managed rerank APIs.

