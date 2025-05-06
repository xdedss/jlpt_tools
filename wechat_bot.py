import requests
import json
import jsonschema
import os
import openai
import logging
import time
import vocab
import traceback
from typing import List
from retry import retry
import seeds
import random

logger = logging.getLogger('wechat_bot')

WX_APPID = os.environ.get('WX_APPID')
WX_AGENTID = os.environ.get('WX_AGENTID')
WX_APPKEY = os.environ.get('WX_APPKEY')
OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')


def send_to_wecom(text, wecom_touid='@all'):
    get_token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={WX_APPID}&corpsecret={WX_APPKEY}"
    response = requests.get(get_token_url).content
    access_token = json.loads(response).get('access_token')
    if access_token and len(access_token) > 0:
        send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
        data = {
            "touser": wecom_touid,
            "agentid": WX_AGENTID,
            "msgtype": "text",
            "text": {
                "content": text
            },
            "duplicate_check_interval": 600
        }
        # print(data)
        
        response = requests.post(send_msg_url, data=json.dumps(data)).content
        return response
    else:
        return False


def chat_once(system: str, user: str, temperature: float = 0.7, model_name: str = 'gpt-4o'):

    logger.info(f"using model {model_name}")

    client = openai.OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_API_BASE,
    )

    for i in range(20):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            text = response.choices[0].message.content
            return (text)

        except openai.RateLimitError:
            # we should try again later
            wait_time = min(2 ** i, 30)
            logger.warning(
                f'openai rate limit, retry #{i+1} after {wait_time} s')
            time.sleep(wait_time)


def find_last_valid_json(input_string):
    # Find the last occurrence of ']' or '}'
    last_index = max(input_string.rfind(']'), input_string.rfind('}'))

    # If neither ']' nor '}' is found, return None
    if last_index == -1:
        return None

    # Extract the potential JSON string
    for i in range(last_index):
        if (input_string[i] in ['[', '{']):
            potential_json = input_string[i:last_index + 1]

            # Try to parse the string as JSON
            try:
                json_object = json.loads(potential_json)
                return json_object  # Return the JSON object if parsing is successful
            except json.JSONDecodeError:
                pass
    return None  # Return None if parsing fails


EXAMPLE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "sentence": {
                "type": "string",
            },
            "romaji": {
                "type": "string",
            },
            "chinese": {
                "type": "string",
            }
        },
        "required": ["sentence", "romaji", "chinese"],
    }
}

# @retry(tries=3, delay=2)
def get_example_sentences(words: List[vocab.Word]):
    json_format = '[{"sentence": "...", "romaji": "...", "chinese": "..."}, ...]'
    def format_word(word: vocab.Word):
        res = f'{word.word}'
        if word.furigana != '':
            res += f'({word.furigana})'
        return res
    prompt = f'''{[format_word(w) for w in words]}
make one or more sentences in japanese using these words. 
- Cover all words provided.
- The sentences should be short and simple to beginners learning the language.
- provide romaji and Chinese translation.
- use json format {json_format}'''
    
    sentences = []
    sentences_dedup = set()
    counter = 0
    while (len(sentences) < 3 and counter < 3):
        counter += 1

        res = chat_once("You are a helpful assistant", prompt)

        res_json = find_last_valid_json(res)
        jsonschema.validate(res_json, EXAMPLE_SCHEMA)

        for s in res_json:
            if (s['sentence'] not in sentences_dedup):
                sentences.append(s)
                sentences_dedup.add(s['sentence'])
    
    return sentences


TIP_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "q": {
                "type": "string",
            },
            "a": {
                "type": "string",
            },
        },
        "required": ["q", "a"],
    }
}

def get_tips(context: str):
    json_format = '[{"q": "问题", "a": "解答"}, ...]'
    prompt = f'''```
{context}
```

以上是一些日语词汇和读音、释义、例句。有哪些相关的容易让日语初学者产生疑问但上述信息没有覆盖到的知识点？
- 只列出3条最重要的
- 以Q&A的形式列出来，使用json格式：{json_format}'''

    res = chat_once("You are a helpful assistant", prompt)

    res_json = find_last_valid_json(res)
    jsonschema.validate(res_json, TIP_SCHEMA)
    return res_json


JP_CN_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "jp": {
                "type": "string",
            },
            "cn": {
                "type": "string",
            },
        },
        "required": ["jp", "cn"],
    }
}

def get_trip_scene_v1():
    
    json_format = '[{"jp": "...", "cn": "中文翻译..."}, ...]'

    places = random.sample(seeds.PLACES_JP, k=1)
    verbs = random.sample(seeds.VERBS_JP, k=2)
    nouns = random.sample(seeds.NOUNS_JP, k=2)

    all_keywords = places + verbs + nouns

    print(all_keywords)

    prompt = f'''keywords: {", ".join(all_keywords)}

以上是一些关键词，在这些关键词的基础上，发挥想象，自由创作，编一段小汪（ワンちゃん）和小喵（ネコちゃん）两个人在日本旅行时发生的故事，需要包含故事背景、开头、至少一段和旅行中遇到的人的对话、结尾。
- 故事中的每一句话都要有日语原文和中文翻译，日语中的汉字词用括号内的平假名注音
- 故事的整体难度适合日语初学者
- 使用json格式的数组表示：{json_format}'''

    res = chat_once("You are a helpful assistant", prompt)

    res_json = find_last_valid_json(res)
    jsonschema.validate(res_json, JP_CN_SCHEMA)
    return res_json


GRAMMAR_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "grammar_template": {
                "type": "string",
            },
            "explanation": {
                "type": "string",
            },
        },
        "required": ["grammar_template", "explanation"],
    }
}

def get_important_grammar(context: str):
    json_format = '[{"grammar_template": "..", "explanation": "中文解释"}, ...]'
    prompt = f'''```
{context}
```

以上是一些日语句子，从中总结出两个重点语法或句式
- 对于每个重点语法或句式，给出日语的句式模版和中文的语法讲解
- 必须使用json格式的数组表示：{json_format}'''

    res = chat_once("You are a helpful assistant", prompt)

    res_json = find_last_valid_json(res)
    jsonschema.validate(res_json, GRAMMAR_SCHEMA)
    return res_json



@retry(tries=3, delay=300)
def task_entry():

    trip_scene = get_trip_scene_v1()

    raw_text = '\n'.join(d['jp'] for d in trip_scene)

    # print(trip_scene)

    grammar = get_important_grammar(raw_text)

    # print(grammar)

    print("Sending msg")
    message_parts = []
    for d in trip_scene:
        message = f"{d['jp']}\n{d['cn']}"
        message_parts.append(message)
    merge_step = 5
    for i in range(0, len(message_parts), merge_step):
        message = '====== 故事 ======\n' if i == 0 else ''
        message += '\n'.join(message_parts[i:i+merge_step])
        r = send_to_wecom(message)
        print(r)
        time.sleep(1.5)
    message_p2 = '====== 语法讲解 ======\n'
    message_p2 += '\n'.join(f"{d['grammar_template']}\n{d['explanation']}" for d in grammar)
    r = send_to_wecom(message_p2)
    print(r)

# legacy since 0506
@retry(tries=3, delay=300)
def task_entry_vocab():
    progress_file = 'wechat_bot_progress.txt'
    if (not os.path.isfile(progress_file)):
        with open(progress_file, 'w') as f:
            f.write('0')

    with open(progress_file, 'r') as f:
        try:
            progress = int(f.read())
        except Exception:
            progress = 0
    
    print(f"progress = {progress}")
    db = vocab.VocabularyDB('all_vocab_emb.sqlite')
    words: List[vocab.Word] = []
    for word in db:
        if word.data.get('cluster', None) == progress:
            words.append(word)

    print([w.word for w in words])
    print('generating examples:')
    example_sentences = []
    try:
        example_sentences = get_example_sentences(words)
    except Exception:
        traceback.print_exc()
        print('unable to generate')
    
    # build messages
    print('build messages')
    message = ''
    tip_context = ''
    message += '==== 词汇 ====\n'
    for word in words:
        message += f'''{word.word}: {word.furigana} ({word.romaji})\n'''
        tip_context += f'''{word.word}: {word.furigana} ({word.romaji})\n'''
        message += f'''{word.meaning}\n'''
        formatted = set()
        for pronunciation in word.data.get('pronunciations', []):
            formatted.add(pronunciation['formatted'])
        if (len(formatted) > 0):
            # message += f"可能的读音声调:\n"
            for s in formatted:
                message += f"{s}\n"

        message += '\n'
    
    if (len(example_sentences) > 0):
        message += '==== 例句 ====\n'
        for sentence in example_sentences:
            text = sentence['sentence']
            romaji = sentence['romaji']
            chinese = sentence['chinese']
            message += f'''{text}\n{romaji}\n{chinese}\n'''
            tip_context += f'''{text}\n{romaji}\n{chinese}\n'''
            message += '\n'

    print("========== P1 ==========")
    print(message)
    print("========== P1 ==========")

    
    message_p2 = ''
    print('generating tips:')
    tips = []
    try:
        tips = get_tips(tip_context)
    except Exception:
        traceback.print_exc()
        print('unable to generate')
        
    if (len(tips) > 0):
        message_p2 += '==== QA ====\n'
        for tip in tips:
            q = tip['q']
            a = tip['a']
            message_p2 += f'''Q:{q}\nA:{a}\n'''
            message_p2 += '\n'
    
    print("========== P2 ==========")
    print(message_p2)
    print("========== P2 ==========")

    print("Sending msg")
    r = send_to_wecom(message)
    print(r)
    time.sleep(0.5)
    r = send_to_wecom(message_p2)
    print(r)
    
    progress += 1
    print(f"next progress is {progress}")
    with open(progress_file, 'w') as f:
        f.write(str(progress))

if __name__ == '__main__':
    task_entry()

