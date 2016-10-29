# !/usr/bin/python
# coding: utf-8

import urllib2  # get pages
# from fake_useragent import UserAgent # change user agent
import time     # to respect page rules
from bs4 import BeautifulSoup as BS
# import codecs

__author__ = 'Arne Binder'


class URLFront(object):

    def __init__(self, rootUrls):
        self.rootUrls = rootUrls
        # self.userAgent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'

    @staticmethod
    def requestPage(url):
        request = urllib2.Request(url, None, {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'})
        try:
            document = urllib2.urlopen(request).read()
        except urllib2.HTTPError, err:
            if err.code == 503:
                print "################################################# 503 #################################################"
                time.sleep(100)
                document = request(url)
            else:
                raise
        return document

    def extractPetitionUrlsFromPage(self, pageUrl):
        """
        Extract all petition urls from an overview page
        :param pageUrl: the url of the overview page
        :return: all urls to petitions in the overview page
        """
        overviewPage = URLFront.requestPage(pageUrl)
        soup = BS(overviewPage.decode('utf-8', 'ignore'), "html.parser")

        aList = soup.select('ul.petitionen-liste li div.text h2 a')

        # petitionList = soup("ul", "petitionen-liste")[0]("li")
        # return [petition("div", "text")[0]("h2")[0]("a")[0]['href'] for petition in petitionList]
        return [a['href'] for a in aList]

    def constructOverviewPageUrls(self, rootPageUrl):
        """
        Extract the count of overview pages from the bottom of the page
        :param rootPageUrl:
        :return: the count
        """
        root_page = URLFront.requestPage(rootPageUrl)
        soup = BS(root_page.decode('utf-8', 'ignore'), "html.parser")
        pager = soup("p", "pager")
        a = pager[0]("a")[-1]
        # href = a[u'href']
        maxCount = a.text
        # print range(int(maxCount))
        return [rootPageUrl + "&seite=" + str(x+1) for x in range(int(maxCount))]
        # return map(lambda x: rootPageUrl + "&seite=" + str(x+1), range(int(maxCount)))

    def extractPetitionUrls(self):
        result = []
        for rootPageUrl in self.rootUrls:
            overviewPageUrls = self.constructOverviewPageUrls(rootPageUrl)
            for overviewPageUrl in overviewPageUrls:
                # print overviewPageUrl
                result.extend(self.extractPetitionUrlsFromPage(overviewPageUrl))
        return set(result)

def main():
    f = URLFront(["https://www.openpetition.de/?status=in_zeichnung"])
    # f.extractPetitionUrls()
    # print f.extractPetitionUrlsFromPage("https://www.openpetition.de/?status=in_zeichnung")
    # print f.constructOverviewPageUrls("https://www.openpetition.de/?status=in_zeichnung")
    for url in f.extractPetitionUrls():
        print url



if __name__ == "__main__":
    main()

