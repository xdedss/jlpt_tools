
import json
import random
import os
import tqdm
import numpy as np
from sklearn.cluster import KMeans

import vocab

db = vocab.VocabularyDB('all_vocab_emb.sqlite')

embedding_data = []
words = []
groups = []


cutoff = 1000
n_clusters = 100
i = 0

for v in tqdm.tqdm(db):
    if (v.level != 5):
        continue
    words.append(v)
    embedding_data.append(v.data['embedding'])
    i += 1
    if (i >= cutoff):
        break

embedding_data = np.array(embedding_data, dtype=float)
words = np.array(words)


kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init="auto").fit(embedding_data)


for cluster_i in range(n_clusters):
    print(cluster_i, [w.word for w in words[kmeans.labels_ == cluster_i]])

# split and merge clusters
SPLIT_THR = 12 # >
MERGE_THR = 5 # <
clusters_to_process = []
for cluster_i in range(n_clusters):
    cluster_words = words[kmeans.labels_ == cluster_i]
    clusters_to_process.append(cluster_words)
clusters_processed = []
while (len(clusters_to_process) > 0):
    cluster_words = clusters_to_process.pop(0)
    if (len(cluster_words) > SPLIT_THR):
        # split
        num_splits = (len(cluster_words) // SPLIT_THR) + 1 # 13 -> 2, 25 -> 3
        indices = np.arange(len(cluster_words))
        for split_i in range(num_splits):
            indices_start = split_i / num_splits * len(cluster_words)
            indices_end = (split_i + 1) / num_splits * len(cluster_words)
            selected = (indices >= indices_start) & (indices < indices_end)
            clusters_processed.append(cluster_words[selected])
            # print(f"split {len(cluster_words)} into {split_i} / {num_splits}  {len(cluster_words[selected])}")
    elif (len(cluster_words) < MERGE_THR):
        # merge
        if ((len(clusters_processed) > 0) and (len(clusters_processed[-1]) + len(cluster_words) <= SPLIT_THR)):
            clusters_processed[-1] = np.concatenate([clusters_processed[-1], cluster_words])
        else:
            clusters_processed.append(cluster_words)
            # print(f"merge {len(cluster_words)}")
    else:
        clusters_processed.append(cluster_words)

clusters_processed.sort(key=lambda words: len(words))
for i, word_group in enumerate(clusters_processed):
    print(i, [w.word for w in word_group])
    for w in word_group:
        w.data['cluster'] = i
        db.update(w, instant_commit=False)
db.commit()
