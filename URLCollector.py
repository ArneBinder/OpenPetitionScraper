# !/usr/bin/python
# coding: utf-8

import urllib2  # get pages
# from fake_useragent import UserAgent # change user agent
import time     # to respect page rules
from bs4 import BeautifulSoup as BS
import pprint
import json
import os
import io
# import codecs

__author__ = 'Arne Binder'


class OpenPetitionCrawler(object):

    def __init__(self, rootUrl, outFolder):
        self.rootUrl = rootUrl # like "https://www.openpetition.de"
        self.outFolder = outFolder

    def requestPage(self, url):
        request = urllib2.Request(self.rootUrl + url, None, {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'})
        try:
            print 'request ' + self.rootUrl + url
            document = urllib2.urlopen(request).read()
        except urllib2.HTTPError, err:
            if err.code == 503:
                print "################################################# 503 #################################################"
                time.sleep(30)
                document = request(url)
            else:
                raise
        return document

    def extractPetitionIDs(self, url):
        """
        Extract all petition IDs from an overview page
        :param url: the url suffix of the overview page
        :return: all IDs of petitions found at the overview page
        """
        overviewPage = self.requestPage(url)
        soup = BS(overviewPage.decode('utf-8', 'ignore'), "html.parser")
        aList = soup.select('ul.petitionen-liste li div.text h2 a')

        return [a['href'].split("/")[-1] for a in aList]

    def getPageCountForState(self, state):
        """
        Extract the count of overview pages from the bottom of the page
        :param state: Select the group of petitions e.g. "in_zeichnung" or "beendet"
        :return: the count of pages with petitions in the selected group
        """
        root_page = self.requestPage("/?status=" + state)
        soup = BS(root_page.decode('utf-8', 'ignore'), "html.parser")
        pager = soup("p", "pager")
        a = pager[0]("a")[-1]
        maxCount = a.text
        return int(maxCount)

    def extractAllPetitionIDs(self, state):
        """
        Exctract all petition IDs for a certain state.
        Search at every overview page for the state.
        :param states: Select the group of petitions e.g. "in_zeichnung" or "beendet"
        :return: all petition IDs in the petition group
        """
        result = []
        # for state in states:
        count = self.getPageCountForState(state)
        for i in range(1, count):
            result.extend(self.extractPetitionIDs("?status=" + state + "&seite=" + str(i)))
        return set(result)

    def parsePetition(self, id):
        """
        Parse the basic data if the petition
        :param id: the ID of the petition
        :return: basic petition data
        """
        page = self.requestPage("/petition/online/" + id)
        result = {}
        soup = BS(page.decode('utf-8', 'ignore'), "html.parser")
        petition = soup.select('div#main div.content > div > div > div.col2')[0]
        result['claimShort'] = petition.find("h2").text
        content = petition.find("div", "text")

        result['claim'] = content("p")[0].text
        result['ground'] = content("p")[1].text
        return result

    def parseDebate(self, id):
        """
        Parse the debate related to a petition
        :param id: the ID of the petition the debate belongs to
        :return: The pro and con arguments of the debate including its counter arguments
        """
        page = self.requestPage("/petition/argumente/" + id)
        soup = BS(page.decode('utf-8', 'ignore'), "html.parser")
        argGroups = soup.select('div.petition-argumente > div > div > div.col2 > div > div.twocol')

        result = {}
        for argGroup in argGroups:
            articles = argGroup("article")
            args = []

            for article in articles:
                newArgument = {}
                newArgument['id'] = article['data-id']
                tags = article.find("ul", "tags")
                if tags is not None:
                    newArgument['tags'] = tags.text
                newArgument['content'] = article.find("div", "text").text
                newArgument['counterArguments'] = json.loads(self.requestPage("/ajax/argument_replies?id=" + newArgument['id']))
                args.append(newArgument)

            polarity = argGroup.find("h2", "h1").text
            if polarity == "Pro":
                result['pro'] = args
            elif polarity == "Contra":
                result['con'] = args
            # else:
                # print "no"

        return result

    def parseComments(self, id):
        """
        Parse comment data of a petition
        :param id: the ID of the petition the comments belong to
        :return: the comment data
        """
        page = self.requestPage("/petition/kommentare/" + id)
        soup = BS(page.decode('utf-8', 'ignore'), "html.parser")
        comments = soup.select('article.kommentar > div.text')
        return [comment.select(' > p')[1].text for comment in comments]

    def extractPartitionData(self, id):
        """
        Collect all data related to a petition
        :param id: the id of the petition
        :return: the data
        """
        result = self.parsePetition(id)
        result['arguments'] = self.parseDebate(id)
        result['comments'] = self.parseComments(id)
        return result

    def processIDs(self, ids, path):
        idsFailed = []
        if not os.path.exists(path):
            os.makedirs(path)
        for id in ids:
            try:
                data = self.extractPartitionData(id)
                writeJsonData(data, path + os.sep + id)
            except:
                idsFailed.append(id)
        writeJsonData(idsFailed, path + "_FAILED")

    def processSections(self, sections):
        for section in sections:
            path = self.outFolder + os.sep + section
            ids = list(self.extractAllPetitionIDs(section))
            writeJsonData(ids, path + "_ALL")
            self.processIDs(ids, path)


def writeJsonData(data, path):
    with io.open(path + '.json', 'w', encoding='utf8') as json_file:
        out = json.dumps(data, ensure_ascii=False)
        # unicode(data) auto-decodes data to unicode if str
        json_file.write(unicode(out))


def main():
    f = OpenPetitionCrawler("https://www.openpetition.de", "out")
    f.processSections(["in_zeichnung"])

    #pp = pprint.PrettyPrinter(indent=4)
    #id = "sind-vaeter-die-besseren-muetter-das-wechselmodell-als-standard-in-deutschland"
    #data = f.extractPartitionData(id)
    #pp.pprint(data)
    #writeJsonData(data, "test")


if __name__ == "__main__":
    main()

