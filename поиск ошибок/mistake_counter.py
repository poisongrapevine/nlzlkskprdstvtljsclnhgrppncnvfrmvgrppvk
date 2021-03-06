import language_tool_python
import csv

tool = language_tool_python.LanguageTool('ru')

# что-то что соберёт комментарии в список
comments = []
with open(filename, encoding='utf-8') as csvfile:
    text = csv.DictReader(csvfile)
    for line in text:
        comments.append(line['text'])

ortho_counter = 0   # считаем орфографические ошибки
sentence_start = 0  # предложение с маленькой буквы
whitespace = 0      # пробел перед запятой или перед скобкой/после скобки
capital_names = 0   # имя с маленькой буквы
talk = 0            # просторечия
other = 0           # другие правила (всего правил 880 и 1.всё кроме вышеперечисленного встречается очень редко в интернет-речи
                    # 2.в их названиях нет ничего что помогло бы их группировать)
csv_list = [['Орфографические ошибки', 'Предложение с маленькой буквы', 'Пробел перед запятой или скобкой', 'Имя с маленькой буквы', 
'Просторечные слова', 'Другие ошибки']]
for line in comments:
    matches = tool.check(line)
    for match in matches:
        if match.ruleId == 'MORFOLOGIK_RULE_RU_RU':
            ortho_counter += 1
        elif match.ruleId == 'UPPERCASE_SENTENCE_START':
            sentence_start += 1
        elif match.ruleId == 'COMMA_PARENTHESIS_WHITESPACE':
            whitespace += 1
        elif match.ruleId == 'Cap_Letters_Name':
            capital_names += 1
        elif match.ruleId == 'RU_SIMPLE_REPLACE':
            talk += 1
        elif match.ruleId != 'Latin_letters':
            other += 1
        list_line = [ortho_counter, sentence_start, whitespace, capital_names, talk, other]
        csv_list.append(list_line)
        ortho_counter = 0
        sentence_start = 0
        whitespace = 0
        capital_names = 0
        talk = 0
        other = 0

# подсчёты записываются в csv табличку
with open(filename, 'w', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(csv_list)
