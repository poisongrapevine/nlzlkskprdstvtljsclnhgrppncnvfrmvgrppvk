import requests
import re
import json
import csv
import time
import random
import language_tool_python
import os
from telegram.ext import Updater, Handler, CommandHandler, MessageHandler, ConversationHandler, Filters
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update

token = ''
domain = ''
filename = ''

# create a file where familiar domains will be stored

with open('domains', 'a') as f:
    pass

# set method dictionaries to make links

wall = {'method':'wall.get',
        'domain':'',
        'offset':'0',
        'count':'100',
        'v':'5.130'}

comm = {'method':'wall.getComments',
        'owner_id':'',
        'post_id':'',
        'offset':'0',
        'count':'',
        'thread_items_count':'',
        'v':'5.130'}

num_id = {'method':'utils.resolveScreenName',
          'screen_name':'',
          'v':'5.130'}

# turn method dicts into urls

def url_maker(urlparts):
    url = 'https://api.vk.com/method/' + urlparts['method'] + '?'

    for ele in urlparts:
        if ele != 'v' and ele != 'method':
            url += str(ele) + '=' + str(urlparts[ele]) + '&'
        elif ele == 'v':
            url += str(ele) + '=' + str(urlparts[ele])
    url += '&access_token=' + str(token)

    return url

# gets whatever a method returns in json format

def url_getter(url):
    r = requests.get(url, allow_redirects=True)
    time.sleep(0.33)
    return json.loads(r.content)

# returns how much time is needed to process

def wait_time(req_count):
    secs = int(req_count * 0.33)
    return time.strftime('estimated time remaining: %H hours %M minutes %S seconds', time.gmtime(secs))

# returns a list of posts on the wall

def get_posts(domain):
    global filename
    filename = 'raw_table_' + domain + '.csv'
    with open('domains', 'a') as f:
        f.write(domain)

    wall = {'method':'wall.get',
        'domain':'',
        'offset':'0',
        'count':'100',
        'v':'5.130'}

    wall['domain'] = domain

    wall_url = url_maker(wall)
    post_count = url_getter(wall_url)['response']['count']
    #print(wait_time(post_count))
    posts = []

    while post_count > 0:
        posts.extend(url_getter(url_maker(wall))['response']['items'])
        if post_count < 100:
            wall['count'] = post_count
            wall['offset'] = int(wall['offset']) + 100
            post_count = 0
        else:
            wall['offset'] = int(wall['offset']) + 100
            post_count -= 100

    return posts

# ONLY WORKS AFTER get_posts METHOD IS USED
# onlu gets comments made by people (not groups; they have no meta info)
# returns a list of comments AND comment replies on the wall

def get_comments(domain, posts):
    comm = {'method':'wall.getComments',
            'owner_id':'',
            'post_id':'',
            'offset':'0',
            'count':'100',
            'thread_items_count':'10',
            'v':'5.130'}

    num_id = {'method':'utils.resolveScreenName',
              'screen_name':'',
              'v':'5.130'}

    num_id['screen_name'] = domain

    num_id_url = url_maker(num_id)
    l = str(url_getter(num_id_url)['response']['object_id'])
    comm['owner_id'] = '-' + l

    comm_posts_ids = []
    thr_comm_ids = {}
    comments = []

    for ele in posts:
        if ele['comments']['count'] > 0:
            comm_posts_ids.append(ele['id'])

    for ele in comm_posts_ids:
        comm['post_id'] = ele
        req = url_getter(url_maker(comm))
        if 'response' not in req.keys():
            continue
        comm_count = req['response']['count']

        while comm_count > 0:
            comment = req['response']['items']
            if type(comment) == list:
                comments.extend(comment)
            else:
                comments.append(comment)

            for c in comment:
                if c['thread']['count'] > 0:
                    thr_comm_ids[c['id']] = c['thread']['count']

            if comm_count <= 100:
                comm['count'] = comm_count
                comm_count = 0
            else:
                comm['offset'] = int(comm['offset']) + 100
                comm_count -= 100

    replies = []

    for comment in comments:
        if 'thread' in comment.keys():
            if comment['thread']['count'] > 0:
                replies.extend(comment['thread']['items'])
        else:
            replies.append(comment)

    comments.extend(replies)

    return comments

# set of table fieldnames

fieldnames = set()

# makes a table row

def dic_maker(comment):
    global fieldnames
    dic = {}
    fields = ['sex', 'city', 'country',
              'home_town', 'has_mobile', 'education',
              'universities', 'schools', 'occupation',
              'relation', 'timezone']

    user = {'method':'users.get',
            'user_ids':'',
            'fields':','.join(fields),
            'v':'5.130'}

    if 'text' in comment.keys():
        dic['text'] = comment['text']
        user['user_ids'] = comment['from_id']
        req = url_getter(url_maker(user))
        if 'response' in req.keys():
            for ele in req['response']:
                dic.update(ele)
                fieldnames.update(set(dic.keys()))
                return dic

# writes table rows into a specified file

def make_table(comments, filename):
    global fieldnames

    table = []

    for comment in comments:
        dic = dic_maker(comment)
        if dic:
            table.append(dic)

    with open(filename, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')

        writer.writeheader()
        for ele in table:
            writer.writerow(ele)

def ask_link(link):
    group = {'method':'groups.getById',
             'group_id':'',
             'group_ids':'',
             'fields':'',
             'v':'5.130'}

    domain = re.findall(r'https://vk.com/(.*)', link)[0]
    group['group_id'] = domain
    group['group_ids'] = domain

    req = url_getter(url_maker(group))
    if req['response'][0]['is_closed'] == 1:
        print('error: the group is closed')
    else:
        return domain

# disdicter takes a string with a dictionary and picks out the name of the city/school, etc.

def disdicter(s):
    key = ''
    keys = ['title', 'name']
    for k in keys:
        if k in s:
            key = k
    rgx = r'\'' + key + '\': \'(.+?)\''
    res = re.findall(rgx, s)
    res = '\t'.join(res)
    if s != '':
        return res
    else:
        return ''

# processer removes unnecessary fields and makes the table legible

def processer(filename):
    content = []
    relations = {'1':'unmarried',
                 '2':'dating someone',
                 '3':'engaged',
                 '4':'married',
                 '5':'complicated',
                 '6':'looking for someone',
                 '7':'in love',
                 '8':'in a civil union',
                 '0':'unknown'}

    with open(filename, 'r') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            content.append(row)
    res_filename = filename.split('.')[0] + '_fixed.csv'

    for ele in content:
        for key in ['city', 'country', 'occupation', 'schools']:
            if key in ele.keys():
                ele[key] = disdicter(ele[key])
        if ele['sex'] == '1':
            ele['sex'] = 'female'
        elif ele['sex'] == '2':
            ele['sex'] = 'male'
        if ele['relation'] != '':
            ele['relation'] = relations[ele['relation']]

    # now we take the important fields we might need

    fieldnames_fixed = ['text',
                  'first_name', 'last_name', 'sex', 'relation',
                  'country', 'city', 'home_town',
                  'relation', 'occupation', 'schools',
                  'education_form', 'university_name', 'faculty_name', 'graduation',
        'orthographic', 'small_initial_letter', 'space_trouble', 'propername_small_letter',
    'colloquialism', 'other', 'total']
    content_fixed = []

    for ele in content:
        dic = dict.fromkeys(fieldnames_fixed)
        for key in dic:
            if key in ele.keys():
                dic[key] = ele[key]
        content_fixed.append(dic)

    with open(res_filename, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames_fixed)

        writer.writeheader()
        for ele in content_fixed:
            writer.writerow(ele)

    return res_filename

def get_relevant(res_filename):
    content_fixed = []
    with open(res_filename) as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            content_fixed.append(row)

    parameters = ['sex', 'relation',
                  'country', 'city', 'home_town',
                  'relation', 'occupation', 'schools',
                  'education_form', 'university_name', 'faculty_name', 'graduation']

    stats = dict.fromkeys(parameters, 0)

    # now we pick out which parameters are defined in more than 50% (or any other %) of cases

    for ele in content_fixed:
        for key in ele.keys():
            if ele[key] != '':
                if key in stats.keys():
                    stats[key] += 1

    relevant_ps = []
    for key in stats:
        stats[key] = round(stats[key] / len(content_fixed), 2)
        if stats[key] > 0.5:          #the number may be arbitrary
            relevant_ps.append(key)

    return relevant_ps

# now count the mistakes for every line

def get_mistakes():
    tool = language_tool_python.LanguageToolPublicAPI('ru')
    content = []
    global filename

    with open(filename, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for ele in reader:
            content.append(ele)

    global fieldnames
    mistakes = ['orthographic', 'small_initial_letter', 'space_trouble', 'propername_small_letter',
    'colloquialism', 'other', 'total']
    fieldnames.update(list(mistakes))

    ortho_counter = False   # orthography mistakes
    sentence_start = False  # a sentence starting with a small letter
    whitespace = False      # space before a comma/fullstop/etc.
    capital_names = False   # proper name starting with a small letter
    talk = False            # colloquialisms
    other = False           # other types of mistakes

    for ele in content:
        line = ele['text']
        matches = tool.check(line)
        for match in matches:
            if match.ruleId == 'MORFOLOGIK_RULE_RU_RU':
                ortho_counter = True
            elif match.ruleId == 'UPPERCASE_SENTENCE_START':
                sentence_start = True
            elif match.ruleId == 'COMMA_PARENTHESIS_WHITESPACE':
                whitespace = True
            elif match.ruleId == 'Cap_Letters_Name':
                capital_names = True
            elif match.ruleId == 'RU_SIMPLE_REPLACE':
                talk = True
            elif match.ruleId != 'Latin_letters':
                other = True

        mistake_counter = {'orthographic':int(ortho_counter),
                       'small_initial_letter':int(sentence_start),
                       'space_trouble':int(whitespace),
                       'propername_small_letter':int(capital_names),
                       'colloquialism':int(talk),
                       'other':int(other),
                       'total':int(bool(ortho_counter + sentence_start + whitespace + capital_names + talk + other))}

        ortho_counter = False
        sentence_start = False
        whitespace = False
        capital_names = False
        talk = False
        other = False

        ele.update(mistake_counter)

    with open(filename, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for ele in content:
            writer.writerow(ele)

# this function comprises all of the work with table(s)

def link_to_table(link):
    global filename
    dom = ask_link(link)
    filename = 'raw_table_' + dom + '.csv'

    # if a domain has been processed before, we won't waste time on processing again
    with open('domains') as f:
        if dom in f.read():
            return get_relevant('raw_table_' + dom + '_fixed.csv')

    posts = get_posts(dom)
    comments = get_comments(dom, posts)

    make_table(comments, filename=filename)
    get_mistakes()

    return get_relevant(processer(filename))

# this function picks out mistake statistics by the chosen parameter

def par_info(parameter, mistake_type, filename):
    content = dict()
    pars = dict()
    with open(filename, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')
            for ele in reader:
                if ele[parameter] != '':
                    if ele[parameter] not in content.keys():
                        content.update({ele[parameter]:int(ele[mistake_type])})
                    else:
                        content[ele[parameter]] += int(ele[mistake_type])
                    if ele[parameter] in pars.keys():
                        pars[ele[parameter]] += 1
                    else:
                        pars[ele[parameter]] = 1

    #content = dict(sorted(content.items(), key=lambda x:x[1], reverse=True))
    content_tuples = [(par, content[par], round(100 * int(content[par])/int(pars[par]))) for par in content]
    content_tuples = sorted(content_tuples, key=lambda x:x[2], reverse=True)
    message = ''
    for ele in content_tuples:
        message += f"{ele[0]}: {ele[1]} ({ele[2]}%)\n"

    return message

# bot starts from here

START, PARAMETERS, MISTAKE = range(3)
PORT = int(os.environ.get('PORT', '8443'))

HEROKU_APPNAME = 'ischi-oshibki2-bot'
TOKEN = ''


def command_start(update, context):
    update.message.reply_text('''I can count people's mistakes for you.
Paste a link to a vk group to get started (and use /startover every time you want to go through a new group)

I will tell you who makes the most mistakes. Example:

parameter: sex
mistake: orthographic

female: 38 (30%)
male: 11 (25%)

30% of girls and 25% of boys have made orthographic mistakes

Warning: processing may take a long time, wait for a reply after /newsearch''')

    return START

def command_startover(update, context):
    update.message.reply_text('So, paste a link to a group of your choice, sir')

    return START

def link_accepted(update, context):
    update.message.reply_text('''use /newsearch to search''')
    context.user_data['link'] = update.message.text
    context.user_data['relevant_ps'] = link_to_table(context.user_data['link'])

    return ConversationHandler.END

def par_processing(update, context):
    context.user_data['parameter'] = update.message.text

    message = 'Choose a mistake'
    mistakes = ['orthographic', 'small_initial_letter', 'space_trouble', 'propername_small_letter',
    'colloquialism', 'other', 'total']
    buttons = [[KeyboardButton(mistake)] for mistake in mistakes]

    update.effective_message.reply_text(
        message, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    )

    return MISTAKE

def command_newsearch(update, context):
    message = 'Choose a parameter'
    buttons = [[KeyboardButton(parameter)] for parameter in context.user_data['relevant_ps']]

    update.effective_message.reply_text(
        message, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
    )

    return PARAMETERS

def give_results(update, context):
    context.user_data['mistake'] = update.message.text
    message = par_info(context.user_data['parameter'], context.user_data['mistake'], filename=filename.split('.')[0] + '_fixed.csv')
    update.message.reply_text(message)

    return ConversationHandler.END

def cancellation(update, context):
    context.user_data.clear()

    return ConversationHandler.END

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    link_handler = ConversationHandler(
        entry_points=[CommandHandler('start', command_start), CommandHandler('newsearch', command_newsearch),
                      (CommandHandler('startover', command_startover))],
        states={
            START: [MessageHandler(Filters.text & ~Filters.command, link_accepted)],
            PARAMETERS: [MessageHandler(Filters.text & ~Filters.command, par_processing)],
            MISTAKE: [MessageHandler(Filters.text & ~Filters.command, give_results)]

        },
        fallbacks=[CommandHandler('cancel', cancellation)]
    )


    dp.add_handler(link_handler)
    dp.add_handler(CommandHandler('newsearch', command_newsearch))
    dp.add_handler(CommandHandler('startover', command_startover))

    updater.start_webhook(listen='0.0.0.0', port=PORT, url_path=TOKEN, webhook_url=f'https://{HEROKU_APPNAME}.herokuapp.com/{TOKEN}')

    updater.idle()


if __name__ == '__main__':
    main()
