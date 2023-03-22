import requests
from bs4 import BeautifulSoup
from newsplease import NewsPlease
from tqdm import tqdm
import multiprocessing
from datetime import datetime, timezone
import argparse

# CONSTANTS
num_processes = 16

# arg parser for command line inputs
parser = argparse.ArgumentParser(description="Crawl economist.com for articles")
parser.add_argument("--folder", type=str, nargs="?", help="folder to save articles", default="")
args = parser.parse_args()

# get direct child links from economist.com
url = 'https://www.economist.com/'
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
links = []
for link in soup.find_all('a'):
    href = link.get('href')
    if href.startswith("/"):
        links.append(href)


def get_article(url):
    """
    get article from economist link by using newsplease
    """
    try:
        article = NewsPlease.from_url(f"https://economist.com{url}", timeout=10)
        return [article.description, article.maintext, article.title]
    except:
        return []


corpus = []
with multiprocessing.Pool(processes=num_processes) as pool:
    with tqdm(total=len(links)) as pbar:
        processed_lists = []
        for processed_list in pool.imap_unordered(get_article, links):
            processed_lists.append(processed_list)
            pbar.update()
        for lst in processed_lists:
            corpus.extend(lst)

corpus = [x if x is not None else "" for x in corpus]


now_utc = datetime.now(timezone.utc)
year = now_utc.year
month = '{:02d}'.format(now_utc.month)
day = '{:02d}'.format(now_utc.day)
with open(f"./{args.folder}/{year}{month}{day}.txt", "w") as f:
    lines = list(map(lambda s: str(s) + '\n', corpus))
    f.writelines(lines)
