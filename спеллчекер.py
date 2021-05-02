import pandas as pd
import re
from spellchecker import SpellChecker

spell = SpellChecker(language='ru')
oneletter = ['а', 'в', 'и', 'к', 'о', 'с', 'у', 'я']
# список количеств ошибок в каждом комментарии
misspelled_list = []

df = pd.read_csv(csvfile)
# список комментариев
text = list(df.text) 

# отбор русских слов
for line in text:
    try:
        line = re.findall('[а-яё]+', line, flags=re.IGNORECASE)
    except:
        line = []
    wordlist = [word for word in line if word not in oneletter]    
    misspelled = spell.unknown(wordlist)
    mis = len(misspelled)
    misspelled_list.append(mis)
