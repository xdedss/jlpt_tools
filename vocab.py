import sqlite3
from dataclasses import dataclass
import json
import tqdm

@dataclass
class Word:
    word: str
    meaning: str
    furigana: str
    romaji: str
    level: int
    data: dict

class VocabularyDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.create_table()

    def create_table(self):
        query = '''
        CREATE TABLE IF NOT EXISTS data (
            word TEXT,
            furigana TEXT,
            meaning TEXT,
            romaji TEXT,
            level INTEGER,
            data TEXT,
            PRIMARY KEY (word, furigana)  -- Composite primary key
        )
        '''
        self.conn.execute(query)
        self.conn.commit()

    def update(self, word: Word, instant_commit=True):
        query = '''
        INSERT INTO data (word, furigana, meaning, romaji, level, data) 
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(word, furigana) DO UPDATE SET
            meaning = excluded.meaning,
            romaji = excluded.romaji,
            level = excluded.level,
            data = excluded.data
        '''
        self.conn.execute(query, (word.word, word.furigana, word.meaning, word.romaji, word.level, json.dumps(word.data, ensure_ascii=False)))
        if (instant_commit):
            self.conn.commit()
    
    def commit(self):
        self.conn.commit()

    def remove(self, word: Word):
        query = 'DELETE FROM data WHERE word = ? AND furigana = ?'
        self.conn.execute(query, (word.word, word.furigana))
        self.conn.commit()

    def __iter__(self):
        cursor = self.conn.execute('SELECT word, meaning, furigana, romaji, level, data FROM data')
        for row in cursor:
            word, meaning, furigana, romaji, level, data = row
            yield Word(word, meaning, furigana, romaji, level, json.loads(data))

    def __del__(self):
        self.conn.close()

    def __len__(self):
        query = 'SELECT COUNT(*) FROM data'
        cursor = self.conn.execute(query)
        count = cursor.fetchone()[0]
        return count

# create db from json
if __name__ == '__main__':

    print('Create DB')
    
    print('loading json')
    json_path = 'all_vocab.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print('updating DB')
    db = VocabularyDB('all_vocab.sqlite')
    for word in tqdm.tqdm(data):
        db.update(Word(
            word['word'],
            word['meaning'],
            word['furigana'],
            word['romaji'],
            word['level'],
            {},
        ), instant_commit=False)
    db.commit()

    print(f"len={len(db)}")
