import re
import csv
import pymorphy2
import os

morph = pymorphy2.MorphAnalyzer()

address = 'put your /archive/messages repository here'
f_json = 'result.csv'
f_ads = []

# соберем адреса файлов с сообщениями
# есть подозрения, что этот кусок кода ходит не по всем файлам, но мне он собрал около 10000 сообщений, чего
# в целом хватило

for subdir, dirs, files in os.walk(address):
    for file in files:
        f_ads.append(os.path.join(subdir, file))
        
# объявим функцию для обработки дат (в вк они записаны по-клоунски)

def datebar(date):
    datebar = date[:11].split()
    months = {'янв':'01',
             'фев':'02',
             'мар':'03',
             'апр':'04',
             'мая':'05',
             'июн':'06',
             'июл':'07',
             'авг':'08',
             'сен':'09',
             'окт':'10',
             'ноя':'11',
             'дек':'12',}
    datebar[1] = months[datebar[1]]
    datebar = '.'.join(datebar)
    return datebar

# а эта функция будет превращать сообщение в словарь с метаданными и кидать его в общий список messages
  
def dict_maker(f_name):
    with open(f_name, encoding='windows-1251') as file:
        messages = []
        text = file.read()
        regex = '''<div class="message__header"><a href=.+?>(.+?)</a>, (.{22})</div>
  <div>(.+?)<div class="kludges"></div>'''
        l = re.findall(r''+regex, text, re.MULTILINE)
        for mes in l:
            ele = dict()
            if mes[0] == 'DELETED':
                ele['name'] = ''
            else:
                ele['name'] = mes[0]
                tag = str(morph.parse(mes[0].split()[0])[0][1]).split(',')
                if len(tag) >= 2:
                    ele['gender'] = tag[2]
                else:
                    ele['gender'] = ''
            ele['date'] = datebar(mes[1])
            ele['text'] = mes[2]
            messages.append(ele)

            return messages

fieldnames = ['name', 'gender', 'date', 'text']
        
with open(f_json, 'w', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames)
    writer.writeheader()
    for file in f_ads:
        messages = dict_maker(file)
        if messages:
            for ele in messages:
                writer.writerow(ele)
                
# это добавочный кусочек, где я уже приписывала сообщениям фичу upper/lower
# что будете делать вы - это уже я не знаю
# что хотите

import csv
messages_pril = []

with open('приличный.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        messages_pril.append(row)
        
for mes in messages_pril:
    if mes['text'][0].islower():
        mes['case'] = 'lower'
    elif mes['text'][0].isupper():
        mes['case'] = 'upper'
    else:
        mes['case'] = ''
        
fieldnames_pril = ['name', 'gender', 'date', 'text', 'case']
        
with open('приличный.final.csv', 'w', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames_pril)
    writer.writeheader()
    for ele in messages_pril:
        writer.writerow(ele)
