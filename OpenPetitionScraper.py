# !/usr/bin/python
# coding: utf-8

import urllib2  # get pages
import time  # to respect page rules

import sys
from bs4 import BeautifulSoup as BS
import pprint
import json
import io
import csv
from os import listdir, makedirs
from os.path import isfile, isdir, join, exists

__author__ = 'Arne Binder'


class OpenPetitionScraper(object):
    def __init__(self, rootUrl, outFolder):
        self.rootUrl = rootUrl  # like "https://www.openpetition.de"
        self.outFolder = outFolder
        # create output folder if necessary
        if not exists(outFolder):
            makedirs(outFolder)

    def requestPage(self, url):
        request = urllib2.Request(self.rootUrl + url, None, {
            'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'})
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

    def getPageCountForSection(self, section):
        """
        Extract the count of overview pages from the bottom of the page
        :param section: Select the group of petitions e.g. "in_zeichnung" or "beendet"
        :return: the count of pages with petitions in the selected group
        """
        root_page = self.requestPage("/?status=" + section)
        soup = BS(root_page.decode('utf-8', 'ignore'), "html.parser")
        pager = soup("p", "pager")
        a = pager[0]("a")[-1]
        maxCount = a.text
        return int(maxCount)

    def extractAllPetitionIDs(self, section):
        """
        Exctract all petition IDs for a certain state.
        Search at every overview page for the state.
        :param states: Select the group of petitions e.g. "in_zeichnung" or "beendet"
        :return: A set of all petition IDs in the petition group
        """
        result = []
        # for state in states:
        count = self.getPageCountForSection(section)
        for i in range(1, count):
            result.extend(self.extractPetitionIDs("?status=" + section + "&seite=" + str(i)))
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
                newArgument = {'id': article['data-id']}
                tags = article.find("ul", "tags")
                if tags is not None:
                    newArgument['tags'] = tags.text
                newArgument['content'] = article.find("div", "text").text
                newArgument['weight'] = article.select('div.tools span.gewicht')[0].text
                newArgument['counterArguments'] = json.loads(
                    self.requestPage("/ajax/argument_replies?id=" + newArgument['id']))
                args.append(newArgument)

            polarity = argGroup.find("h2", "h1").text
            if polarity == "Pro":
                result['pro'] = args
            elif polarity == "Contra":
                result['con'] = args
                # else:
                # print "no"

        return result

    def parseComments(self, petitionID):
        """
        Parse comment data of a petition
        :param petitionID: the ID of the petition the comments belong to
        :return: the comment data
        """
        page = self.requestPage("/petition/kommentare/" + petitionID)
        soup = BS(page.decode('utf-8', 'ignore'), "html.parser")
        comments = soup.select('article.kommentar > div.text')
        return [comment.select(' > p')[1].text for comment in comments]

    def extractPartitionData(self, petitionID):
        """
        Collect all data related to a petition
        :param petitionID: the id of the petition
        :return: the data
        """
        result = self.parsePetition(petitionID)
        result['arguments'] = self.parseDebate(petitionID)
        result['comments'] = self.parseComments(petitionID)
        return result

    def processIDs(self, ids, path):
        idsFailed = []
        for currentID in ids:
            try:
                data = self.extractPartitionData(currentID)
                writeJsonData(data, join(path, currentID))
            except:
                idsFailed.append(currentID)
        writeJsonData(idsFailed, path + "_MISSING")

    def processSections(self, sections):
        for section in sections:
            path = join(self.outFolder, section)
            if exists(path + "_ALL.json"):
                # read id list from file
                with open(path + '_ALL.json') as fileAllIDs:
                    ids = json.load(fileAllIDs)
            else:
                ids = list(self.extractAllPetitionIDs(section))
                writeJsonData(ids, path + "_ALL")

            if not exists(path):
                makedirs(path)
            # get processedIDs from json file
            processedIDs = [f[:-len('.json')] for f in listdir(path) if isfile(join(path, f))]
            ids = [id for id in ids if id not in processedIDs]
            if exists(path + "_MISSING.json"):
                # read id list from file
                with open(path + '_MISSING.json') as fileMissingIDs:
                    missingIDs = json.load(fileMissingIDs)
                ids.extend(missingIDs)
            self.processIDs(ids, path)


def writeJsonData(data, path):
    with io.open(path + '.json', 'w', encoding='utf8') as json_file:
        out = json.dumps(data, ensure_ascii=False)
        # unicode(data) auto-decodes data to unicode if str
        json_file.write(unicode(out))


def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


def collectStats(debate):
    return None


def collectTextStats(texts, keyPrefix):
    result = {keyPrefix + '_length_min_chars': sys.maxint, keyPrefix + '_length_max_chars': 0, keyPrefix + '_length_avg_chars': 0, keyPrefix + '_length_min_words': sys.maxint, keyPrefix + '_length_max_words': 0, keyPrefix + '_length_avg_words': 0}
    for text in texts:
        # text = argument['content'].strip()
        lenChars = len(text)
        lenWords = len(text.split())

        if lenChars > result[keyPrefix + '_length_max_chars']:
            result[keyPrefix + '_length_max_chars'] = lenChars
        if lenChars < result[keyPrefix + '_length_min_chars']:
            result[keyPrefix + '_length_min_chars'] = lenChars
        result[keyPrefix + '_length_avg_chars'] += lenChars
        if lenWords > result[keyPrefix + '_length_max_words']:
            result[keyPrefix + '_length_max_words'] = lenWords
        if lenWords < result[keyPrefix + '_length_min_words']:
            result[keyPrefix + '_length_min_words'] = lenWords
        result[keyPrefix + '_length_avg_words'] += lenWords

    if len(texts) > 0:
        result[keyPrefix + '_length_avg_chars'] /= len(texts)
        result[keyPrefix + '_length_avg_words'] /= len(texts)
        return result
    else:
        return {keyPrefix + '_length_min_chars': 0, keyPrefix + '_length_max_chars': 0, keyPrefix + '_length_avg_chars': 0, keyPrefix + '_length_min_words': 0, keyPrefix + '_length_max_words': 0, keyPrefix + '_length_avg_words': 0}

def createCSVStats(inPath, csvOutPath):
    captions = ["question", "argument_count", "argument_count_pro", "argument_count_con", "argument_length_min_chars",
                "argument_length_max_chars", "argument_length_avg_chars", "argument_length_min_words",
                "argument_length_max_words", "argument_length_avg_words", "reply_count", "reply_length_min_chars",
                "reply_length_max_chars", "reply_length_avg_chars", "reply_length_min_words", "reply_length_max_words",
                "reply_length_avg_words", "state"]
    recordDict = []
    sections = [f for f in listdir(inPath) if isdir(join(inPath, f))]

    for section in sections:
        sectionPath = join(inPath, section)
        debateIDs = [f[:-len('.json')] for f in listdir(sectionPath) if isfile(join(sectionPath, f))]
        for debateID in debateIDs:
            with open(join(sectionPath, debateID+'.json')) as data_file:
                data = json.load(data_file)
                print join(sectionPath, debateID+'.json')
                debateStats = {}
                debateStats['question'] = data['claimShort']
                debateStats['argument_count_pro'] = len(data['arguments']['pro'])
                debateStats['argument_count_con'] = len(data['arguments']['con'])
                debateStats['argument_count'] = debateStats['argument_count_pro'] + debateStats['argument_count_con']
                allArgs = data['arguments']['pro'] + data['arguments']['con']
                debateStats.update(collectTextStats([argument['content'].strip() for argument in allArgs], 'argument'))
                replies = []
                for arg in allArgs:
                    replies.extend(arg['counterArguments'])
                debateStats['reply_count'] = len(replies)
                debateStats.update(collectTextStats([reply['argument_text'] for reply in replies], 'reply'))
                debateStats['state'] = section
                recordDict.append(debateStats)

    # csvUW = UnicodeWriter()




    with open(csvOutPath, 'w') as tsvFile:
        writer = csv.writer(tsvFile, delimiter='\t')

        # write captions
        writer.writerow(captions)
        for record in recordDict:
            writer.writerow([((str(record[key]) if type(record[key]) is int else record[key].encode('utf-8')) if key in record else "-") for key in captions])


def main():
    f = OpenPetitionScraper("https://www.openpetition.de", "out")
    f.processSections(["in_zeichnung", "in_bearbeitung", "erfolg", "beendet", "misserfolg", "gesperrt"])
    # createCSVStats("out", "out.tsv")


if __name__ == "__main__":
    main()
