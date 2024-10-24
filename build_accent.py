
# please download pronunciation data from https://github.com/javdejong/nhk-pronunciation/blob/master/ACCDB_unicode.csv

import os
import numpy as np
import pandas as pd
import vocab
import tqdm

pronunciation_csv = 'ACCDB_unicode.csv'

df = pd.read_csv(pronunciation_csv, names=['NID','ID','WAVname','K_FLD','ACT','midashigo','nhk','kanjiexpr','NHKexpr','numberchars','nopronouncepos','nasalsoundpos','majiri','kaisi','KWAV','midashigo1','akusentosuu','bunshou','ac'], dtype=str, header=None)

def is_alike(s1: str, s2: str):
    if (abs(len(s1) - len(s2)) > 1):
        return False
    return s1 in s2 or s2 in s1

def query_prononciation(word: vocab.Word, df: pd.DataFrame):
    word_str = repr(word.word.split('/')[0].strip())

    q = df.query(f'kanjiexpr == {word_str}')
    if (len(q) == 0):
        q = df.query(f'nhk == {word_str}')
    if (len(q) == 0):
        q = df[df.apply(lambda x: is_alike(word.word, x['kanjiexpr']), axis=1)]
    if (len(q) == 0):
        return None
    return q

def extract_pron_info(row):
    txt = str(row.midashigo1)
    ac = str(row.ac)
    nasalsoundpos = str(row.nasalsoundpos)
    nopronouncepos = str(row.nopronouncepos)
    strlen = len(txt)
    acclen = len(ac)
    accent = "0"*(strlen-acclen) + ac
    
    # Get the nasal positions
    nasal = []
    if nasalsoundpos and nasalsoundpos.lower() != 'nan':
        positions = nasalsoundpos.split('0')
        for p in positions:
            if p:
                nasal.append(int(p))
            if not p:
                # e.g. "20" would result in ['2', '']
                nasal[-1] = nasal[-1] * 10

    # Get the no pronounce positions
    nopron = []
    if nopronouncepos and nopronouncepos.lower() != 'nan':
        positions = nopronouncepos.split('0')
        for p in positions:
            if p:
                nopron.append(int(p))
            if not p:
                # e.g. "20" would result in ['2', '']
                nopron[-1] = nopron[-1] * 10

    outstr = ""
    overline = False

    for i in range(strlen):
        a = int(accent[i])
        # Start or end overline when necessary
        if not overline and a > 0:
            outstr = outstr + '↑'
            overline = True
        if overline and a == 0:
            outstr = outstr + '↓'
            overline = False

        if (i+1) in nopron:
            outstr = outstr + '('

        # Add the character stuff
        outstr = outstr + txt[i]

        # Add the pronunciation stuff
        if (i+1) in nopron:
            outstr = outstr + ")"
        # if (i+1) in nasal:
        #     outstr = outstr + '<span class="nasal">&#176;</span>'

        # If we go down in pitch, add the downfall
        if a == 2:
            outstr = outstr + '↓'
            # note that this will prevent another down arrow in the next iteration
            overline = False
    
    return {
        'txt': txt,
        'accent': accent,
        'nasal': nasal,
        'nopron': nopron,
        'formatted': outstr,
    }



print(df)
db = vocab.VocabularyDB('all_vocab_emb.sqlite')
good = []
pbar = tqdm.tqdm(db)
for word in pbar:
    # if (word.level != 5):
    #     continue
    q = query_prononciation(word, df)
    possible_pron = []
    if (q is None):
        print(word.word)
    else:
        for i, row in q.iterrows():
            possible_pron.append(extract_pron_info(row))
    good.append(q is not None)
    pbar.set_description(f'{np.mean(good):.4f}')

    word.data['pronunciations'] = possible_pron
    db.update(word, False)
db.commit()

print(np.mean(good))

    
