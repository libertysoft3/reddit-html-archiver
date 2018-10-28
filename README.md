## reddit html archiver

pulls reddit data from the [pushshift](https://github.com/pushshift/api) api and renders offline compatible html pages

### install

requires python 3

    sudo apt-get install pip
    pip install psaw
    git clone https://github.com/chid/snudown
    cd snudown
    sudo python setup.py install
    cd ..
    git clone [this repo]
    cd reddit-html-archiver
    chmod u+x *.py

### fetch reddit data from pushshift

data is fetched by subreddit and date range.

    ./fetch_links.py politics 2017-1-1 2017-2-1
    # or add some link/post request parameters
    ./fetch_links.py --self_only --score "> 2000" politics 2015-1-1 2016-1-1
    ./fetch_links.py -h

you may need decrease your date range or adjust `pushshift_rate_limit_per_minute` in `fetch_links.py` if you are getting connection errors.

### write web pages

write html files for all subreddits.

    ./write_html.py
    # or add some output filtering
    ./write_html.py --min-score 100 --min-comments 100 --hide-deleted-comments
    ./write_html.py -h
    

if you add more data later, delete everything in `r` aside from `r/static` and re-run the script to refresh your archive's pages.

### hosting the archived pages

copy the contents of the `r` directory to a web root or appropriately served git repo. or serve it directly.

### potential improvements

* fetch_links
  * num_comments filtering
  * thumbnails or thumbnail urls
  * media posts
  * update scores from the reddit api with [praw](https://github.com/praw-dev/praw)
* real templating
* filter output per sub, individual min score and comments filters
* js markdown url previews
* js powered search page, show no links by default
* user pages
  * add pagination, posts sorted by score, comments, date, sub
  * too many files in one directory

### see also

* [pushshift](https://github.com/pushshift/api) [subreddit](https://www.reddit.com/r/pushshift/)
* [psaw](https://github.com/dmarx/psaw)
* [snudown](https://github.com/reddit/snudown)
* [redditsearch.io](https://redditsearch.io/)
* [reddit post archiver](https://github.com/sJohnsonStoever/redditPostArchiver)

### screenshots

![](screenshots/sub.jpg)
![](screenshots/post.jpg)