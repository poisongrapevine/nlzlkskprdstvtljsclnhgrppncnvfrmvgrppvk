#!/usr/bin/env python
# coding: utf-8

# In[55]:


import requests
import re
import json
import csv
import time
import random

import os
import random
import string
from telegram.ext import Updater, Handler, CommandHandler, MessageHandler, ConversationHandler, Filters

token = 'acadb24bacadb24bacadb24bdfacd944d8aacadacadb24bccc70b3e0abb60674a6e4c48'
filename = 'raw_table.csv'

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


# In[50]:


# returns a list of posts on the wall

def get_posts(domain):
    
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
            
    print('got posts')

    return posts


# In[51]:


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
    print('got comms')

    return comments

# set of table fieldnames

fieldnames = set()

# makes a table row

def dic_maker(comment):
    
    dic = {}
    global fieldnames
    fields = ['sex', 'bdate', 'city', 'country', 
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
    
    table = []
    global fieldnames
    
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


# In[56]:


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

def processer(filename):
    content = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            content.append(row)
    res_filename = filename.split('.')[0] + '_fixed.csv'
    for ele in content:
        for key in ['city', 'country', 'occupation', 'schools']:
            if key in ele.keys():
                ele[key] = disdicter(ele[key])
        
    # now we take the important fields we might need

    fieldnames_fixed = ['text',
                  'first_name', 'last_name', 'sex', 'relation',
                  'country', 'city', 'home_town', 'bdate',
                  'relation', 'occupation', 'schools',
                  'education_form', 'university_name', 'faculty_name', 'graduation']
    content_fixed = []

    for ele in content:
        dic = dict.fromkeys(fieldnames_fixed)
        for key in dic:
            if key in ele:
                dic[key] = ele[key]
        content_fixed.append(dic)

    with open(res_filename, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames_fixed)

        writer.writeheader()
        for ele in content_fixed:
            writer.writerow(ele)

    parameters = ['sex', 'relation',
                  'country', 'city', 'home_town', 'bdate',
                  'relation', 'occupation', 'schools',
                  'education_form', 'university_name', 'faculty_name', 'graduation']

    stats = dict.fromkeys(parameters, 0)

    # now we pick out which parameters are defined in more than 50% (or any other %) of cases

    for ele in content_fixed:
        for key in stats:
            if ele[key] != '':
                stats[key] += 1

    relevant_ps = []
    for key in stats:
        stats[key] = round(stats[key] / len(content_fixed), 2)
        if stats[key] > 0.5:          #the number may be arbitrary
            relevant_ps.append(key)
            
    return relevant_ps


# In[57]:


# this function comprises all of the work with table(s)
# mistake counters should be added

def link_to_table(link):
    
    filename = 'raw_table.csv'
    dom = ask_link(link)
    posts = get_posts(dom)
    comments = get_comments(dom, posts)
    make_table(comments, filename=filename)
    
    return processer(filename)


# In[65]:


# this function picks out mistake statistics by the chosen parameter
# work in progress

filename = 'произошел фикл fixed.csv'
content = dict()
parameter = 'relation'
mistake_type = 'sex'

def par_info(parameter, mistake_type, filename='raw_table_fixed.csv'):
    with open(filename, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')
            for ele in reader:
                if ele[parameter] != '':
                    if ele[parameter] not in content.keys():
                        content.update({ele[parameter]:int(ele[mistake_type])})
                    else:
                        content[ele[parameter]] += int(ele[mistake_type])
    return content


# In[66]:


START, RAW, PARAMETERS = range(3)
TOKEN = '1726470276:AAGnYM6HidMFhftVIydHcqQPH9_dcYGPBc0'


def command_start(update, context):
    update.message.reply_text('''Paste a link to get started''')
    
    return START
    
def link_accepted(update, context):
    context.user_data['link'] = update.message.text
    print(context.user_data['link'])
    context.user_data['relevant_ps'] = link_to_table(context.user_data['link'])
    
    return RAW

def raw_processing(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='''Choose a parameter: 
                             ''' + ', '.join(context.user_data['relevant_ps']))
    # the bot needs a pinok pod zad before sending you the fields
    # we'd better ask for a mistake type here or later
    context.user_data['parameter'] = update.message.text
    
    return PARAMATERS

def par_processing(update, context):
    #par_info(context.user_data['parameter'])
    pass
    
def cancellation(update, context):
    context.user_data.clear()
    update.message.reply_text('Cancelled')
    
    return ConversationHandler.END

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    link_handler = ConversationHandler(
        entry_points=[CommandHandler('start', command_start)],
        states={
            START: [MessageHandler(Filters.text & ~Filters.command, link_accepted)],
            RAW: [MessageHandler(Filters.text & ~Filters.command, raw_processing)],
            PARAMETERS: [MessageHandler(Filters.text & ~Filters.command, par_processing)]
        
        },
        fallbacks=[CommandHandler('cancel', cancellation)]
    )
    
    
    dp.add_handler(link_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()


# In[ ]:




