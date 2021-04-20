import csv
import re

# filename is taken from the previous part, where a raw table was assembled

filename = 'results.csv'
res_filename = filename.split('.')[0] + '_fixed.csv'

# read the table again

content = []
with open(filename, 'r') as f:
    reader = csv.DictReader(f, delimiter=',')
    for row in reader:
        content.append(row)

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

for ele in content:
    ele['city'] = disdicter(ele['city'])
    ele['country'] = disdicter(ele['country'])
    ele['occupation'] = disdicter(ele['occupation'])
    ele['schools'] = disdicter(ele['schools'])

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
        
print('Look at these parameters: ' + ', '.join(relevant_ps))

