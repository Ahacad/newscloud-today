import requests
import os
from bs4 import BeautifulSoup
from newsplease import NewsPlease
from tqdm import tqdm
import multiprocessing
import json
from datetime import datetime, timezone
import argparse
from abc import ABC, abstractmethod

# CONSTANTS
NUM_PROCESSES = 16

# arg parser for command line inputs
parser = argparse.ArgumentParser(description="Crawl news websites for articles")
parser.add_argument("--folder", type=str, nargs="?", help="folder to save articles", default="")
args = parser.parse_args()


class Crawler(ABC):
    def __init__(self, url: str, folder: str) -> None:
        self.url = url
        self.folder = folder
        self.links = []
        self.article_objs = []
        self.corpus = []
        self._mkdirs_if_not_exist(f"./{self.folder}")

    def _mkdirs_if_not_exist(self, dirname) -> None:
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    def _get_year_month_day_string(self) -> str:
        """
        get date string in format of yearmonthday, for example 20220304, 20221125, will be used as file names
        """
        now_utc = datetime.now(timezone.utc)
        year = now_utc.year
        month = '{:02d}'.format(now_utc.month)
        day = '{:02d}'.format(now_utc.day)
        return f"{year}{month}{day}"

    def get_article(self, url: str):
        """
        get article from link by using newsplease
        """
        try:
            article = NewsPlease.from_url(url, timeout=10)
            return [article, article.description, article.maintext, article.title]
        except:
            return []

    @abstractmethod
    def get_links(self):
        """
        get links to crawl, saved in self.links
        """ 
        pass

    def crawl(self):
        with multiprocessing.Pool(processes=NUM_PROCESSES) as pool:
            with tqdm(total=len(self.links)) as pbar:
                processed_lists = []
                for processed_list in pool.imap_unordered(self.get_article, self.links):
                    processed_lists.append(processed_list)
                    pbar.update()
                for lst in processed_lists:
                    if lst == None or len(lst) == 0: continue
                    self.article_objs.append(lst[0])
                    lst.pop(0)
                    self.corpus.extend(lst)

        # replace NONE in self.corpus to empty string since newsplease sometimes return NONE
        self.corpus = [x if x is not None else "" for x in self.corpus] 

    def save_to_json(self, folder):
        """
        save serialized article objects to jsons for human reading or more structured analyses
        """
        serialized_json_objs = list(map(lambda x: x.get_serializable_dict(), self.article_objs))
        date_string = self._get_year_month_day_string()
        with open(f"./{folder}/{date_string}.json", "w") as f:
            json.dump(serialized_json_objs, f)


    def save_to_txt(self, folder):
        """
        save raw corpus to txt for later text analyses, raw corpus include article descriptions, maintexts, and titles
        """
        date_string = self._get_year_month_day_string()
        with open(f"./{folder}/{date_string}.txt", "w") as f:
            lines = list(map(lambda s: str(s) + '\n', self.corpus))
            f.writelines(lines)

    def run(self):
        self.get_links()
        self.crawl()
        self.save_to_json(self.folder)
        self.save_to_txt(self.folder)


class EconomistCrawler(Crawler):
    def __init__(self, url, folder):
        super().__init__(url, folder)

    def get_links(self):
        """
        get direct child links from economist.com
        """
        response = requests.get(self.url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a'):
            href = link.get('href')
            if href.startswith("/"):
                self.links.append(f"{self.url}{href}")

class MITTechReviewCrawler(Crawler):
    def __init__(self, url, folder):
        super().__init__(url, folder)

    def get_links(self):
        """
        get direct child links from technologyreview.com
        """
        response = requests.get(self.url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a'):
            href = link.get('href')
            if href.startswith("https://www.technologyreview.com"):
                self.links.append(href)

class AmericanAffairsCrawler(Crawler):
    def __init__(self, url, folder):
        super().__init__(url, folder)

    def get_links(self):
        """
        get direct child links from americanaffairsjournal.org
        """
        response = requests.get(self.url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a'):
            href = link.get('href')
            if href.startswith("https://americanaffairsjournal.org"):
                self.links.append(href)

if __name__ == "__main__":
    economist_crawler = EconomistCrawler("https://www.economist.com", f"{args.folder}/economists")
    economist_crawler.run()
    mittechreviewcrawler = MITTechReviewCrawler("https://www.technologyreview.com", f"{args.folder}/mittechreview")
    mittechreviewcrawler.run()
    americanaffairscrawler = AmericanAffairsCrawler("https://americanaffairsjournal.org", f"{args.folder}/americanaffairs")
    americanaffairscrawler.run()
