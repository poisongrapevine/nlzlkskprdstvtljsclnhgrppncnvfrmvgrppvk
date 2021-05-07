import pandas as pd
import pymorphy2
import re
from spellchecker import SpellChecker

morph = pymorphy2.MorphAnalyzer()

spell = SpellChecker(language='ru')
oneletter = ['а', 'в', 'и', 'к', 'о', 'с', 'у', 'я']
# список количеств ошибок в каждом комментарии
misspelled_list = []

df = pd.read_csv('сказки под грибом.csv')
# список комментариев
text = list(df.text) 

# отбор русских слов
for line in text:
    try:
        line = re.findall('[а-яё]+', line, flags=re.IGNORECASE)
    except:
        line = []
    wordlist = [morph.parse(word)[0] for word in line if word not in oneletter]
    nf_list = [word.normal_form for word in wordlist]
    misspelled = spell.unknown(nf_list)
    mis = len(misspelled)
    misspelled_list.append(mis)

