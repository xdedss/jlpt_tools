

**JLPT 词汇表来源**
https://jlpt-vocab-api.vercel.app/

保存为`all_vocab.json`

**NHK 声调来源***
https://github.com/javdejong/nhk-pronunciation/blob/master/ACCDB_unicode.csv

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

build_accent: 从`ACCDB_unicode.csv`生成音调标记

wechat_bot: 企业微信推送词汇


