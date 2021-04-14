#!/usr/bin/env python
# coding: utf-8

# In[49]:


import requests
import re
import json
import csv
import time
import random

token = 'acadb24bacadb24bacadb24bdfacd944d8aacadacadb24bccc70b3e0abb60674a6e4c48'

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

def get_posts():
    
    wall = {'method':'wall.get',
        'domain':'',
        'offset':'0',
        'count':'100',
        'v':'5.130'}
    
    global domain
    wall['domain'] = domain
    
    wall_url = url_maker(wall)
    post_count = url_getter(wall_url)['response']['count']
    print(wait_time(post_count))
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


# In[51]:


# ONLY WORKS AFTER get_posts METHOD IS USED
# onlu gets comments made by people (not groups; they have no meta info)
# returns a list of comments AND comment replies on the wall

def get_comments():

    global domain, posts

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
            print(req)
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


# In[52]:


# set of table fieldnames

fieldnames = set()

# makes a table row

def dic_maker(comment):
    
    global fieldnames
    dic = {}
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
    
    global fieldnames
    table = []
    
    for comment in comments:
        dic = dic_maker(comment)
        if dic:
            table.append(dic)

    with open(filename, 'w') as f:
        writer = csv.DictWriter(f, fieldnames, delimiter=';')

        writer.writeheader()
        for ele in table:
            writer.writerow(ele)


# In[53]:


# user inserts a link to a vk group

def ask_link():

    link = input('Paste a link to a vk group of your choice: ')

    group = {'method':'groups.getById',
             'group_id':'',
             'group_ids':'',
             'fields':'',
             'v':'5.130'}

    domain = re.findall(r'https://vk.com/(.*)', link)[0]
    group['group_id']  = domain
    group['group_ids']  = domain

    req = url_getter(url_maker(group))
    if req['response'][0]['is_closed'] == 1:
        print('error: the group is closed')
    else:
        return domain

