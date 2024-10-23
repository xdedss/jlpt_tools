# run embedding for every word and save into database

import transformers
import os, json

model_name = 'Qwen/Qwen2.5-0.5B'

print("loading model")
tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
# transformers.Qwen2ForCausalLM
model = transformers.AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto",
)
model.eval()



import vocab
import tqdm
db = vocab.VocabularyDB('all_vocab.sqlite')


def get_emb(text):
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    res = model(**model_inputs, output_hidden_states=True)
    hidden = res.hidden_states[-1] # (1 * n * dim)
    return hidden[0, -1]
    


for v in tqdm.tqdm(db):
    emb = get_emb(v.word)
    emb_list = emb.tolist()
    v.data['embedding'] = emb_list
    db.update(v, instant_commit=False)
db.commit()

