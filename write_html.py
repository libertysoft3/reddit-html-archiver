#! /usr/bin/env python
from datetime import datetime, date, timedelta
import argparse
import csv
import os
import re
import snudown

url_project = 'https://github.com/libertysoft3/reddit-html-archiver'
links_per_page = 30
pager_skip = 10
pager_skip_long = 100
start_date = date(2005, 1, 1)
end_date = datetime.today().date() + timedelta(days=1)
source_data_links = 'links.csv'
max_comment_depth = 8 # mostly for mobile, which might be silly
removed_content_identifiers = ['[deleted]','deleted','[removed]','removed']
default_sort = 'score'
sort_indexes = {
    'score': {
        'default': 1,
        'slug': 'score'
    },
    'num_comments': {
        'default': 0,
        'slug': 'comments',
    },
    'created_utc': {
        'default': 1000198000,
        'slug': 'date',
    }
}
missing_comment_score_label = 'n/a'

template_index = ''
with open('templates/index.html', 'r', encoding='utf-8') as file:
    template_index = file.read()

template_subreddit = ''
with open('templates/subreddit.html', 'r', encoding='utf-8') as file:
    template_subreddit = file.read()

template_link = ''
with open('templates/link.html', 'r', encoding='utf-8') as file:
    template_link = file.read()

template_comment = ''
with open('templates/partial_comment.html', 'r', encoding='utf-8') as file:
    template_comment = file.read()

template_search = ''
with open('templates/search.html', 'r', encoding='utf-8') as file:
    template_search = file.read()

template_user = ''
with open('templates/user.html', 'r', encoding='utf-8') as file:
    template_user = file.read()

template_sub_link = ''
with open('templates/partial_menu_item.html', 'r', encoding='utf-8') as file:
    template_sub_link = file.read()

template_user_url = ''
with open('templates/partial_user.html', 'r', encoding='utf-8') as file:
    template_user_url = file.read()

template_link_url = ''
with open('templates/partial_link.html', 'r', encoding='utf-8') as file:
    template_link_url = file.read()

template_search_link = ''
with open('templates/partial_search_link.html', 'r', encoding='utf-8') as file:
    template_search_link = file.read()

template_index_sub = ''
with open('templates/partial_index_subreddit.html', 'r', encoding='utf-8') as file:
    template_index_sub = file.read()

template_index_pager_link = ''
with open('templates/partial_subreddit_pager_link.html', 'r', encoding='utf-8') as file:
    template_index_pager_link = file.read()

template_selftext = ''
with open('templates/partial_link_selftext.html', 'r', encoding='utf-8') as file:
    template_selftext = file.read()

template_user_page_link = ''
with open('templates/partial_user_link.html', 'r', encoding='utf-8') as file:
    template_user_page_link = file.read()

teplate_url = ''
with open('templates/partial_url.html', 'r', encoding='utf-8') as file:
    template_url = file.read()

def generate_html(min_score=0, min_comments=0, hide_deleted_comments=False):
    delta = timedelta(days=1)
    subs = get_subs()
    stat_links = 0
    stat_filtered_links = 0
    user_index = {}
    processed_subs = []

    for sub in subs:
        d = start_date
        sub_links = []
        stat_sub_links = 0
        stat_sub_filtered_links = 0
        stat_sub_comments = 0
        while d <= end_date:
            raw_links = load_links(d, sub)
            # print ('processing %s %s %s links' % (sub, d.strftime("%Y-%m-%d"), len(sub_links)))
            stat_links += len(raw_links)
            stat_sub_links += len(raw_links)
            for l in raw_links:
                if validate_link(l, min_score, min_comments):
                    stat_filtered_links += 1
                    stat_sub_filtered_links += 1
                    stat_sub_comments += len('comments')
                    sub_links.append(l)
                    if l['author'] not in user_index.keys():
                        user_index[l['author']] = []
                    l['subreddit'] = sub
                    user_index[l['author']].append(l)
                    # TODO: return comments written
                    write_link_page(subs, l, sub, hide_deleted_comments)
            d += delta
        if stat_sub_filtered_links > 0:
            processed_subs.append({'name': sub, 'num_links': stat_sub_filtered_links})
        write_subreddit_pages(sub, subs, sub_links, stat_sub_filtered_links, stat_sub_comments)
        write_subreddit_search_page(sub, subs, sub_links, stat_sub_filtered_links, stat_sub_comments)
        print('%s: %s links filtered to %s' % (sub, stat_sub_links, stat_sub_filtered_links))
    write_index(processed_subs)
    write_user_page(processed_subs, user_index)
    print('all done. %s links filtered to %s' % (stat_links, stat_filtered_links))

def write_subreddit_pages(subreddit, subs, link_index, stat_sub_filtered_links, stat_sub_comments):
    if len(link_index) == 0:
        return True

    for sort in sort_indexes.keys():
        links = sorted(link_index, key=lambda k: (int(k[sort]) if k[sort] != '' else sort_indexes[sort]['default']), reverse=True)
        pages = list(chunks(links, links_per_page))
        page_num = 0

        sort_based_prefix = '../'
        if sort == default_sort:
            sort_based_prefix = ''

        # render subreddits list
        subs_menu_html = ''
        for sub in subs:
            sub_url = sort_based_prefix + '../' + sub + '/index.html'
            subs_menu_html += template_sub_link.replace('###URL_SUB###', sub_url).replace('###SUB###', sub)

        for page in pages:
            page_num += 1
            # print('%s page' % (page))

            links_html = ''
            for l in page:
                author_link_html = template_user_url
                author_url = sort_based_prefix + '../user/' + l['author'] + '.html'
                author_link_html = author_link_html.replace('###URL_AUTHOR###', author_url).replace('###AUTHOR###', l['author'])

                link_url = l['url']
                link_comments_url = sort_based_prefix + l['permalink'].lower().strip('/')
                link_comments_url = link_comments_url.replace('r/' + subreddit + '/', '')
                idpath = '/'.join(list(l['id']))
                link_comments_url = link_comments_url.replace(l['id'], idpath)
                link_comments_url += '.html'
                if l['is_self'] is True or l['is_self'] == 'True':
                    link_url = link_comments_url

                index_link_data_map = {
                    '###TITLE###':              l['title'],
                    '###URL###':                link_url,
                    '###URL_COMMENTS###':       link_comments_url,
                    '###SCORE###':              str(l['score']),
                    '###NUM_COMMENTS###':       l['num_comments'] if int(l['num_comments']) > 0 else str(0),
                    '###DATE###':               datetime.utcfromtimestamp(int(l['created_utc'])).strftime('%Y-%m-%d'),
                    '###LINK_DOMAIN###':        '(self.' + l['subreddit'] + ')' if l['is_self'] is True or l['is_self'] == 'True' else '',
                    '###HTML_AUTHOR_URL###':    author_link_html,
                }
                link_html = template_link_url
                for key, value in index_link_data_map.items():
                    link_html = link_html.replace(key, value)
                links_html += link_html + '\n'

            index_page_data_map = {
                '###INCLUDE_PATH###':           sort_based_prefix + '../',
                '###TITLE###':                  'by ' + sort_indexes[sort]['slug'] + ' page ' + str(page_num) + ' of ' + str(len(pages)),
                '###SUB###':                    subreddit,
                '###ARCH_NUM_POSTS###':         str(stat_sub_filtered_links),
                '###ARCH_NUM_COMMENTS###':      str(stat_sub_comments),
                '###URL_SUBS###':               sort_based_prefix + '../index.html',
                '###URL_PROJECT###':            url_project,
                '###URL_IDX_SCORE###':          sort_based_prefix + 'index.html',
                '###URL_IDX_CMNT###':           sort_based_prefix + 'index-' + sort_indexes['num_comments']['slug'] + '/index.html',
                '###URL_IDX_DATE###':           sort_based_prefix + 'index-' + sort_indexes['created_utc']['slug'] + '/index.html',
                '###URL_SEARCH###':             sort_based_prefix + 'search.html',
                '###URL_IDX_SCORE_CSS###':      'active' if sort == 'score' else '',
                '###URL_IDX_CMNT_CSS###':       'active' if sort == 'num_comments' else '',
                '###URL_IDX_DATE_CSS###':       'active' if sort == 'created_utc' else '',
                '###URL_SEARCH_CSS###':         '',
                '###HTML_LINKS###':             links_html,
                '###HTML_SUBS_MENU###':         subs_menu_html,
                '###HTML_PAGER###':             get_pager_html(page_num, len(pages)),
            }
            page_html = template_subreddit
            for key, value in index_page_data_map.items():
                page_html = page_html.replace(key, value)

            
            # write file
            suffix = '-' + str(page_num) + '.html'
            if page_num == 1:
                suffix = '.html'
            filename = 'index' + suffix
            if sort == default_sort:
                filepath = 'r/' + subreddit + '/' + filename
            else:
                filepath = 'r/' + subreddit + '/index-' + sort_indexes[sort]['slug'] + '/' + filename
            if not os.path.isfile(filepath):
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(page_html)
                    # print('wrote %s %s, %s links' % (sort, filepath, len(page)))

    return True

def write_link_page(subreddits, link, subreddit='', hide_deleted_comments=False):
    # reddit:  https://www.reddit.com/r/conspiracy/comments/8742iv/happening_now_classmate_former_friend_of/
    # archive: r/conspiracy/comments/8/7/4/2/i/v/happening_now_classmate_former_friend_of.html
    idpath = '/'.join(list(link['id']))
    filepath = link['permalink'].lower().strip('/') + '.html'
    filepath = filepath.replace(link['id'], idpath)
    if os.path.isfile(filepath):
        return True

    created = datetime.utcfromtimestamp(int(link['created_utc']))
    sorted_comments = []
    if len(link['comments']) > 0:
        sorted_comments = sort_comments(link['comments'], hide_deleted_comments)

    # traverse up to root dir, depends on id length
    static_include_path = ''
    for i in range(len(link['id']) + 2):
        static_include_path += '../'

    # render comments
    comments_html = ''
    for c in sorted_comments:
        css_classes = 'ml-' + (str(c['depth']) if int(c['depth']) <= max_comment_depth else str(max_comment_depth))
        if c['author'] == link['author'] and c['author'] not in removed_content_identifiers:
            css_classes += ' op'
        if c['stickied'].lower() == 'true' or c['stickied'] is True:
            css_classes += ' stickied'

        # author link
        url = static_include_path + 'user/' + c['author'] + '.html'
        author_link_html = template_user_url.replace('###URL_AUTHOR###', url).replace('###AUTHOR###', c['author'])

        comment_data_map = {
            '###ID###':                 c['id'],
            '###PARENT_ID###':          c['parent_id'],
            '###DEPTH###':              str(c['depth']),
            '###DATE###':               created.strftime('%Y-%m-%d'),
            '###SCORE###':              str(c['score']) if len(str(c['score'])) > 0 else missing_comment_score_label,
            '###BODY###':               snudown.markdown(c['body'].replace('&gt;','>')),
            '###CSS_CLASSES###':        css_classes,
            '###CLASS_SCORE###':        'badge-danger' if len(c['score']) > 0 and int(c['score']) < 1 else 'badge-secondary',
            '###HTML_AUTHOR_URL###':    author_link_html,
        }
        comment_html = template_comment
        for key, value in comment_data_map.items():
            comment_html = comment_html.replace(key, value)
        comments_html += comment_html + '\n'

    # render subreddits list
    subs_menu_html = ''
    for sub in subreddits:
        sub_url = static_include_path + sub + '/index.html'
        subs_menu_html += template_sub_link.replace('###URL_SUB###', sub_url).replace('###SUB###', sub)

    # render selftext
    selftext_html = ''
    if len(link['selftext']) > 0:
        selftext_html = template_selftext.replace('###SELFTEXT###', snudown.markdown(link['selftext'].replace('&gt;','>')))

    # author link
    url = static_include_path + 'user/' + link['author'] + '.html'
    author_link_html = template_user_url.replace('###URL_AUTHOR###', url).replace('###AUTHOR###', link['author'])

    html_title = template_url.replace('#HREF#', link['url']).replace('#INNER_HTML#', link['title'])
    if link['is_self'] is True or link['is_self'].lower() == 'true':
        html_title = link['title']

    # render link page
    link_data_map = {
        '###INCLUDE_PATH###':       static_include_path,
        '###SUB###':                subreddit,
        '###TITLE###':              link['title'],
        '###ID###':                 link['id'],
        '###DATE###':               created.strftime('%Y-%m-%d'),
        '###ARCHIVE_DATE###':       datetime.utcfromtimestamp(int(link['retrieved_on'])).strftime('%Y-%m-%d') if link['retrieved_on'] != '' else 'n/a',
        '###SCORE###':              str(link['score']),
        '###NUM_COMMENTS###':       str(link['num_comments']),
        '###URL_PROJECT###':        url_project,
        '###URL_SUBS###':           static_include_path + 'index.html',
        '###URL_SUB###':            static_include_path + subreddit + '/index.html',
        '###URL_SUB_CMNT###':       static_include_path + subreddit + '/index-' + sort_indexes['num_comments']['slug'] + '/index.html',
        '###URL_SUB_DATE###':       static_include_path + subreddit + '/index-' + sort_indexes['created_utc']['slug'] + '/index.html',
        '###URL_SEARCH###':         static_include_path + subreddit + '/search.html',
        '###HTML_SUBS_MENU###':     subs_menu_html,
        '###HTML_SELFTEXT###':      selftext_html,
        '###HTML_COMMENTS###':      comments_html,
        '###HTML_AUTHOR_URL###':    author_link_html,
        '###HTML_TITLE###':         html_title,
    }
    html = template_link
    for key, value in link_data_map.items():
        html = html.replace(key, value)

    # write html
    # reddit:  https://www.reddit.com/r/conspiracy/comments/8742iv/happening_now_classmate_former_friend_of/
    # archive: r/conspiracy/comments/8/7/4/2/i/v/happening_now_classmate_former_friend_of.html
    idpath = '/'.join(list(link['id']))
    filepath = link['permalink'].lower().strip('/') + '.html'
    filepath = filepath.replace(link['id'], idpath)
    if not os.path.isfile(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(html)
        # print('wrote %s %s' % (created.strftime('%Y-%m-%d'), filepath))

    return True

def write_subreddit_search_page(subreddit, subs, link_index, stat_sub_filtered_links, stat_sub_comments):
    if len(link_index) == 0:
        return True

    # name sort?
    links = sorted(link_index, key=lambda k: re.sub(r'\W+', '', k['title']).lower())

    # render subreddits list
    subs_menu_html = ''
    for sub in subs:
        sub_url = '../' + sub + '/index.html'
        subs_menu_html += template_sub_link.replace('###URL_SUB###', sub_url).replace('###SUB###', sub)

    links_html = ''
    for l in links:
        link_comments_url = l['permalink'].lower().strip('/').replace('r/' + subreddit + '/', '')
        idpath = '/'.join(list(l['id']))
        link_comments_url = link_comments_url.replace(l['id'], idpath)
        link_comments_url += '.html'
        index_link_data_map = {
            '###TITLE###':              l['title'],
            '###URL###':                link_comments_url,
        }
        link_html = template_search_link
        for key, value in index_link_data_map.items():
            link_html = link_html.replace(key, value)
        links_html += link_html + '\n'

    index_page_data_map = {
        '###INCLUDE_PATH###':           '../',
        '###TITLE###':                  'search',
        '###SUB###':                    subreddit,
        '###ARCH_NUM_POSTS###':         str(stat_sub_filtered_links),
        '###ARCH_NUM_COMMENTS###':      str(stat_sub_comments),
        '###URL_SUBS###':               '../index.html',
        '###URL_PROJECT###':            url_project,
        '###URL_IDX_SCORE###':          'index.html',
        '###URL_IDX_CMNT###':           'index-' + sort_indexes['num_comments']['slug'] + '/index.html',
        '###URL_IDX_DATE###':           'index-' + sort_indexes['created_utc']['slug'] + '/index.html',
        '###URL_SEARCH###':             'search.html',
        '###URL_IDX_SCORE_CSS###':      '',
        '###URL_IDX_CMNT_CSS###':       '',
        '###URL_IDX_DATE_CSS###':       '',
        '###URL_SEARCH_CSS###':         'active',
        '###HTML_LINKS###':             links_html,
        '###HTML_SUBS_MENU###':         subs_menu_html,
    }
    page_html = template_search
    for key, value in index_page_data_map.items():
        page_html = page_html.replace(key, value)

    # write file
    filename = 'search.html'
    filepath = 'r/' + subreddit + '/' + filename
    if not os.path.isfile(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(page_html)
            # print('wrote %s, %s links' % (filepath, len(links)))
    return True

def write_user_page(subs, user_index):
    if len(user_index.keys()) == 0:
        return False

    # subreddits list
    subs_menu_html = ''
    for sub in subs:
        sub_url = '../' + sub['name'] + '/index.html'
        subs_menu_html += template_sub_link.replace('###URL_SUB###', sub_url).replace('###SUB###', sub['name'])

    for user in user_index.keys():
        links = user_index[user]
        links.sort(key=lambda k: (int(k['score']) if k['score'] != '' else sort_indexes['score']['default']), reverse=True)

        links_html = ''
        for l in links:

            author_link_html = template_user_url
            author_url = l['author'] + '.html'
            author_link_html = author_link_html.replace('###URL_AUTHOR###', author_url).replace('###AUTHOR###', l['author'])

            link_comments_url = '../' + l['permalink'].lower().strip('/').strip('r/')
            idpath = '/'.join(list(l['id']))
            link_comments_url = link_comments_url.replace(l['id'], idpath)
            link_comments_url += '.html'
            link_url = l['url']
            if l['is_self'] is True or l['is_self'] == 'True':
                link_url = link_comments_url

            link_data_map = {
                '###TITLE###':              l['title'],
                '###URL###':                link_url,
                '###URL_COMMENTS###':       link_comments_url,
                '###SCORE###':              str(l['score']),
                '###NUM_COMMENTS###':       str(l['num_comments']) if int(l['num_comments']) > 0 else str(0),
                '###DATE###':               datetime.utcfromtimestamp(int(l['created_utc'])).strftime('%Y-%m-%d'),
                '###SUB###':                l['subreddit'],
                '###SUB_URL###':            '../' + l['subreddit'] + '/index.html',
                '###HTML_AUTHOR_URL###':    author_link_html,
            }
            link_html = template_user_page_link
            for key, value in link_data_map.items():
                link_html = link_html.replace(key, value)
            links_html += link_html + '\n'

        page_data_map = {
            '###INCLUDE_PATH###':           '../',
            '###TITLE###':                  'user/' + user,
            '###ARCH_NUM_POSTS###':         str(len(links)),
            '###URL_USER###':               user + '.html',
            '###URL_SUBS###':               '../index.html',
            '###URL_PROJECT###':            url_project,
            '###HTML_LINKS###':             links_html,
            '###HTML_SUBS_MENU###':         subs_menu_html,
        }
        page_html = template_user
        for key, value in page_data_map.items():
            page_html = page_html.replace(key, value)

        filepath = 'r/user/' + user + '.html'
        if not os.path.isfile(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(page_html)
            # print('wrote %s' % (filepath))

    return True

def write_index(subs):
    if len(subs) == 0:
        return False
    subs.sort(key=lambda k: k['name'].casefold())
    
    stat_num_links = 0
    links_html = ''
    subs_menu_html = ''
    for sub in subs:
        sub_url = sub['name'] + '/index.html'
        links_html += template_index_sub.replace('#URL_SUB#', sub_url).replace('#SUB#', sub['name']).replace('#NUM_LINKS#', str(sub['num_links']))
        subs_menu_html += template_sub_link.replace('###URL_SUB###', sub_url).replace('###SUB###', sub['name'])
        stat_num_links += sub['num_links']

    index_page_data_map = {
        '###INCLUDE_PATH###':           '',
        '###TITLE###':                  'subreddits',
        '###URL_SUBS###':               'index.html',
        '###URL_PROJECT###':            url_project,
        '###ARCH_NUM_POSTS###':         str(stat_num_links),
        '###HTML_LINKS###':             links_html,
        '###HTML_SUBS_MENU###':         subs_menu_html,
    }
    page_html = template_index
    for key, value in index_page_data_map.items():
        page_html = page_html.replace(key, value)

    filepath = 'r/index.html'
    if not os.path.isfile(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(page_html)
        # print('wrote %s' % (filepath))

    return True

# a 'top' comments sort with orphaned comments (incomplete data) rendered last
# only remove deleted comments if no children
# 
def sort_comments(comments, hide_deleted_comments=False):
    sorted_comments = []
    if len(comments) == 0:
        return sorted_comments
    parent_map = {}
    id_map = {}
    top_level_comments = []
    link_id = comments[0]['link_id']
    depth = 0

    for c in comments:
        c['depth'] = depth
        id_map[c['id']] = c
        parent_map[c['id']] = c['parent_id']
        # add stickied comments
        if c['stickied'].lower() == 'true':
            sorted_comments.append(c)
        # store top level comments      
        elif c['parent_id'] == c['link_id']:
            top_level_comments.append(c)

    # sort non stickied top level comments
    if len(top_level_comments) > 0:
        top_level_comments = sorted(top_level_comments, key=lambda k: (int(k['score']) if k['score'] != '' else 1), reverse=True)
        sorted_comments += top_level_comments

    # add each top level comment's child comments
    sorted_linear_comments = []
    for c in sorted_comments:
        if hide_deleted_comments and c['body'] in removed_content_identifiers and 't1_' + c['id'] not in parent_map.values():
            pass
        else:
            sorted_linear_comments.append(c)
            child_comments = get_comment_tree_list([], depth + 1, c, id_map, parent_map, hide_deleted_comments)
            if len(child_comments) > 0:
                sorted_linear_comments += child_comments

    # add orphaned comments
    for c in comments:
        if c['parent_id'] != link_id and c['parent_id'].strip('t1_') not in id_map.keys():
            if hide_deleted_comments and c['body'] in removed_content_identifiers:
                continue
            sorted_linear_comments.append(c)

    # print('sort_comments() in %s out %s show deleted: %s' % (len(comments), len(sorted_comments), hide_deleted_comments))
    return sorted_linear_comments

def get_comment_tree_list(tree, depth, parent_comment, id_map, parent_map, hide_deleted_comments):
    parent_id = 't1_' + parent_comment['id']
    child_comments = []
    for key, value in parent_map.items():
        if value == parent_id:
            if hide_deleted_comments and id_map[key]['body'] in removed_content_identifiers and 't1_' + key not in parent_map.values():
                pass
            else:
                child_comments.append(id_map[key])

    # sort children by score
    # TODO: sort by score and # of child comments
    if len(child_comments) > 0:
        child_comments = sorted(child_comments, key=lambda k: (int(k['score']) if k['score'] != '' else 1), reverse=True)
        for child_comment in child_comments:
            child_comment['depth'] = depth
            tree.append(child_comment)
            tree = get_comment_tree_list(tree, depth + 1, child_comment, id_map, parent_map, hide_deleted_comments)
    return tree

def validate_link(link, min_score=0, min_comments=0):
    if not link:
        return False
    elif not 'id' in link.keys():
        return False
    # apply multiple conditions as an OR, keep high score low comments and high comment low score links/posts
    if min_score > 0 and min_comments > 0:
        if int(link['score']) < min_score and int(link['num_comments']) < min_comments:
            return False
    else:
        if min_score > 0 and int(link['score']) < min_score:
            return False
        if min_comments > 0 and int(link['num_comments']) < min_comments:
            return False

    return True

def load_links(date, subreddit):
    links = []
    if not date or not subreddit:
        return links

    date_path = date.strftime("%Y/%m/%d")
    daily_path = 'data/' + subreddit + '/' + date_path
    daily_links_path = daily_path + '/' + source_data_links
    if os.path.isfile(daily_links_path):
        links = []
        with open(daily_links_path, 'r', encoding='utf-8') as links_file:
            reader = csv.DictReader(links_file)
            for link_row in reader:
                comments = []
                comments_file_path = daily_path + '/' + link_row['id'] + '.csv'
                if os.path.isfile(comments_file_path):
                    with open(comments_file_path, 'r', encoding='utf-8') as comments_file:
                        reader = csv.DictReader(comments_file)
                        for comment_row in reader:
                            comments.append(comment_row)
                link_row['comments'] = comments
                links.append(link_row)
    return links

def get_subs():
    subs = []
    if not os.path.isdir('data'):
        print('ERROR: no data, run fetch_links.py first')
        return subs
    for d in os.listdir('data'):
        if os.path.isdir('data' + '/' + d):
            subs.append(d.lower())
    return subs

def get_pager_html(page_num=1, pages=1):
    html_pager = ''

    # previous
    css = ''
    if page_num == 1:
        css = 'disabled'
    url = 'index'
    if page_num  - 1 > 1:
        url += '-' + str(page_num - 1)
    url += '.html'
    html_pager += template_index_pager_link.replace('#URL#', url).replace('#TEXT#', '&lsaquo;').replace('#CSS_CLASS#', css)
    
    # skip back
    css = ''
    prev_skip = page_num - pager_skip
    if prev_skip < 1:
        prev_skip = 1
    if page_num == 1:
        css = 'disabled'
    url = 'index'
    if prev_skip > 1:
        url += '-' + str(prev_skip)
    url += '.html'
    html_pager += template_index_pager_link.replace('#URL#', url).replace('#TEXT#', '&lsaquo;&lsaquo;').replace('#CSS_CLASS#', css)
    
    # skip back far
    css = ''
    prev_skip = page_num - pager_skip_long
    if prev_skip < 1:
        prev_skip = 1
    if page_num == 1:
        css += ' disabled'
    url = 'index'
    if prev_skip > 1:
        url += '-' + str(prev_skip)
    url += '.html'
    html_pager += template_index_pager_link.replace('#URL#', url).replace('#TEXT#', '&lsaquo;&lsaquo;&lsaquo;').replace('#CSS_CLASS#', css)

    # n-1
    start = -2
    if page_num + 1 > pages:
        start -= 1
    if page_num + 2 > pages:
        start -= 1
    for prev_page_num in range(start,0):
        if page_num + prev_page_num > 0:
            css = ''
            url = 'index'
            if page_num + prev_page_num > 1:
                url += '-' + str(page_num + prev_page_num)
            url += '.html'
            if prev_page_num < -1:
                css = 'd-none d-sm-block'
            html_pager += template_index_pager_link.replace('#URL#', url).replace('#TEXT#', str(page_num + prev_page_num)).replace('#CSS_CLASS#', css)
    # n
    url = 'index'
    if page_num > 1:
        url += '-' + str(page_num)
    url += '.html'
    html_pager += template_index_pager_link.replace('#URL#', url).replace('#TEXT#', str(page_num)).replace('#CSS_CLASS#', 'active')
    # n + 1
    css = ''
    end = 3
    if page_num -1 < 1:
        end += 1
    if page_num - 2 < 1:
        end += 1
    for next_page_num in range(1,end):
        if page_num + next_page_num <= pages:
            if next_page_num > 1:
                css = 'd-none d-sm-block'
            html_pager += template_index_pager_link.replace('#URL#', 'index' + '-' + str(page_num + next_page_num) + '.html').replace('#TEXT#', str(page_num + next_page_num)).replace('#CSS_CLASS#', css)

    # skip forward far
    next_skip = page_num + pager_skip_long
    css = ''
    if page_num == pages:
        css += ' disabled'
    if next_skip > pages:
        next_skip = pages
    url = 'index'
    if next_skip > 1:
        url += '-' + str(next_skip)
    url += '.html'
    html_pager += template_index_pager_link.replace('#URL#', url).replace('#TEXT#', '&rsaquo;&rsaquo;&rsaquo;').replace('#CSS_CLASS#', css)
    
    # skip forward
    next_skip = page_num + pager_skip
    css = ''
    if page_num == pages:
        css = 'disabled'
    if next_skip > pages:
        next_skip = pages
    url = 'index'
    if next_skip > 1:
        url += '-' + str(next_skip)
    url += '.html'
    html_pager += template_index_pager_link.replace('#URL#', url).replace('#TEXT#', '&rsaquo;&rsaquo;').replace('#CSS_CLASS#', css)

    # next
    css = ''
    next_num = page_num + 1 
    if page_num == pages:
      css = 'disabled'
      next_num = pages
    html_pager += template_index_pager_link.replace('#URL#', 'index' + '-' + str(next_num) + '.html').replace('#TEXT#', '&rsaquo;').replace('#CSS_CLASS#', css)

    return html_pager

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--min-score', default=0, help='limit post rendering, default 0')
    parser.add_argument('--min-comments', default=0, help='limit post rendering, default 0')
    parser.add_argument('--hide-deleted-comments', action='store_true', help='exclude deleted and removed comments where possible')
    args=parser.parse_args()

    hide_deleted_comments = False
    if args.hide_deleted_comments:
        hide_deleted_comments = True

    args.min_score = int(args.min_score)
    args.min_comments = int(args.min_comments)

    generate_html(args.min_score, args.min_comments, hide_deleted_comments)
