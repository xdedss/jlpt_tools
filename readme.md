

**JLPT 词汇表来源**
https://jlpt-vocab-api.vercel.app/

保存为`all_vocab.json`

# Files

vocab: 生成词库、词库数据结构封装

从`all_vocab.json`生成`all_vocab.sqlite`
``` bash
python vocab.py
```

run_embeddings: LLM生成embedding
``` bash
python run_embeddings.py
```

clustering: 用LLM的embedding聚类，相近词分组


