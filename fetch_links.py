#! /usr/bin/env python
import time
from time import mktime
from datetime import datetime, timedelta
import argparse
from pprint import pprint
import json
import csv
import os
from psaw import PushshiftAPI

pushshift_rate_limit_per_minute = 20
max_comments_per_query = 150
write_every = 10

link_fields = ['author', 'created_utc', 'domain', 'id', 'is_self', 
    'num_comments', 'over_18', 'permalink', 'retrieved_on', 'score', 
    'selftext', 'stickied', 'subreddit_id', 'title', 'url']
comment_fields = ['author', 'body', 'created_utc', 'id', 'link_id', 
    'parent_id', 'score', 'stickied', 'subreddit_id']

def fetch_links(subreddit=None, date_start=None, date_stop=None, limit=None, score=None, self_only=False):
    if subreddit is None or date_start is None or date_stop is None:
        print('ERROR: missing required arguments')
        exit()

    api = PushshiftAPI(rate_limit_per_minute=pushshift_rate_limit_per_minute, detect_local_tz=False)

    # get links
    links = []
    print('fetching submissions %s to %s...' % (time.strftime('%Y-%m-%d', date_start), time.strftime('%Y-%m-%d', date_stop)))
    params = {
        'after': int(mktime(date_start)) - 86400, # make date inclusive, adjust for UTC
        'before': int(mktime(date_stop)) + 86400,
        'subreddit': subreddit,
        'filter': link_fields,
        'sort': 'asc',
        'sort_type': 'created_utc',
    }
    if limit:
        params['limit'] = int(limit)
    if score:
        params['score'] = score
    if self_only:
        params['is_self'] = True
    link_results = list(api.search_submissions(**params))
    print('processing %s links' % len(link_results))
    for s in link_results:
        # print('%s %s' % (datetime.utcfromtimestamp(int(s.d_['created_utc'])), s.d_['title']))
        # pprint(s)

        # get comment ids
        comments = []
        if s.d_['num_comments'] > 0 and not comment_data_exists(subreddit, s.d_['created_utc'], s.d_['id']):
            comment_ids = list(api._get_submission_comment_ids(s.d_['id']))
            # print('%s comment_ids: %s' % (data['id'], comment_ids))

            # get comments
            if (len(comment_ids) > 0):
                mychunks = []
                if len(comment_ids) > max_comments_per_query:
                    mychunks = chunks(comment_ids, max_comments_per_query)
                else:
                    mychunks = [comment_ids]
                for chunk in mychunks:
                    comment_params = {
                        'filter': comment_fields,
                        'ids': ','.join(chunk),
                        'limit': max_comments_per_query,
                    }
                    comments_results = list(api.search_comments(**comment_params))
                    print('%s fetch link %s comments %s/%s' % (datetime.utcfromtimestamp(int(s.d_['created_utc'])), s.d_['id'], len(comments_results), len(comment_ids)))
                    for c in comments_results:
                        comments.append(c.d_)

        s.d_['comments'] = comments
        links.append(s.d_)

        # write results
        if len(links) >= write_every:
            success = write_links(subreddit, links)
            if success:
                links = []

    # write remining results
    if len(links):
        write_links(subreddit, links)

# csvs are not guaranteed to be sorted by date but you can resume broken runs
# and change sort criteria later to add more posts without getting duplicates.
# delete csvs and re-run to update existing posts
def write_links(subreddit, links):
    if links and len(links) > 0:
        writing_day = None
        file = None
        writer = None
        existing_link_ids = []
        wrote_links = 0
        wrote_comments = 0

        for r in links:
            # print('%s link %s' % (r['id'], r['title']))

            # grab link comments
            existing_comment_ids = []
            comments = r['comments']
            # print('%s comments %s' % (r['id'], comments))

            created_ts = int(r['created_utc'])
            created = datetime.utcfromtimestamp(created_ts).strftime('%Y-%m-%d')
            created_path = datetime.utcfromtimestamp(created_ts).strftime('%Y/%m/%d')
            if created != writing_day:
                if file:
                    file.close()
                writing_day = created
                path = 'data/' + subreddit + '/' + created_path
                os.makedirs(path, exist_ok=True)

                # create and parse existing links
                filename = 'links.csv'
                filepath = path + '/' + filename
                if not os.path.isfile(filepath):
                    file = open(filepath, 'a', encoding='utf-8')
                    writer = csv.DictWriter(file, fieldnames=link_fields)
                    writer.writeheader()
                    # print('created %s' % filepath)
                else:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        reader = csv.DictReader(file)
                        for row in reader:
                            existing_link_ids.append(row['id'])

                    file = open(filepath, 'a', encoding='utf-8')
                    writer = csv.DictWriter(file, fieldnames=link_fields)

            # create and parse existing comments
            # writing empty comments csvs resuming and comment_data_exists()
            filename = r['id'] + '.csv'
            filepath = path + '/' + filename
            if not os.path.isfile(filepath):
                comments_file = open(filepath, 'a', encoding='utf-8')
                comments_writer = csv.DictWriter(comments_file, fieldnames=comment_fields)
                comments_writer.writeheader()
                # print('created %s' % filepath)
            else:
                with open(filepath, 'r', encoding='utf-8') as comments_file:
                    reader = csv.DictReader(comments_file)
                    for row in reader:
                        existing_comment_ids.append(row['id'])

                comments_file = open(filepath, 'a', encoding='utf-8')
                comments_writer = csv.DictWriter(comments_file, fieldnames=comment_fields)

            # write link row
            if r['id'] not in existing_link_ids:
                for field in list(r):
                    if field not in link_fields:
                        del r[field]

                writer.writerow(r)
                wrote_links += 1

            # write comments
            for c in comments:
                if c['id'] not in existing_comment_ids:
                    for field in list(c):
                        if field not in comment_fields:
                            del c[field]
                    comments_writer.writerow(c)
                    wrote_comments += 1
            comments_file.close()


        print('got %s links, wrote %s and %s comments' % (len(links), wrote_links, wrote_comments))
    return True

def link_data_exists(subreddit, date):
    created_path = time.strftime('%Y/%m/%d', date)
    path = 'data/' + subreddit + '/' + created_path + '/links.csv'
    if not os.path.isfile(path):
        return False
    return True

def comment_data_exists(subreddit, link_created_utc, link_id):
    created_ts = int(link_created_utc)
    created_path = datetime.utcfromtimestamp(created_ts).strftime('%Y/%m/%d')
    path = 'data/' + subreddit + '/' + created_path + '/' + link_id + '.csv'
    if os.path.isfile(path):
        return True
    return False

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]

def mkdate(datestr):
  try:
    return time.strptime(datestr, '%Y-%m-%d')
  except ValueError:
    raise argparse.ArgumentTypeError(datestr + ' is not a proper date string')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('subreddit', help='subreddit to archive')
    parser.add_argument('date_start', type=mkdate, help='start archiving at date, e.g. 2005-1-1')
    parser.add_argument('date_stop', type=mkdate, help='stop archiving at date, inclusive, cannot be date_start')
    parser.add_argument('--limit', default=None, help='pushshift api limit param, default None')
    parser.add_argument('--score', default=None, help='pushshift api score param, e.g. "> 10", default None')
    parser.add_argument('--self_only', action="store_true", help='only fetch selftext submissions, default False')
    args=parser.parse_args()

    self_only = False
    if args.self_only:
        self_only = True

    fetch_links(args.subreddit, args.date_start, args.date_stop, args.limit, args.score, self_only)
