[
    'id',
    'name',
    'description',
    'created_at',
    'updated_at',
    'splitter_type',
    'chunk_size',
    'chunk_overlap',
    'embedder_type',
    'embedder_model',
    'vector_store_type',
    'collection_name',
    'persist_directory',
    'semantic_config',
    'full_config',
    'kb_id',
    'document_count',
    'total_chunks',
    'last_updated',
    'vector_count',
    'avg_document_length',
    'total_tokens',
    'is_initialized'
]

{
    "name": "ancient_chinese_literature",
    "description": "\u4e2d\u56fd\u53e4\u4ee3\u6587\u5b66",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "embedder": {"embedder_type": "bge", "model_name": "BAAI/bge-small-zh-v1.5"},

    "vector_store": {"store_type": "chroma", "collection_name": "ancient_chinese_literature"}
}

{
    "name": "ai_kownledge",
    "description": "AI\u77e5\u8bc6\u5e93",
    "splitter_type": "recursive",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "embedder": {
        "embedder_type": "bge",
        "model": "BAAI/bge-small-zh-v1.5",
        "dimensions": null,
        "normalize_embeddings": true,
        "device": "cpu"
    },
    "vector_store": {
        "store_type": "chroma",
        "collection_name": "kb1",
        "persist_directory": "./data/vector_stores/kb",

        "host": null,
        "port": null
    },
    "semantic_config": {}
}
