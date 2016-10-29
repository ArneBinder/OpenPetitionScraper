# !/usr/bin/python
# coding: utf-8

import urllib2  # get pages
# from fake_useragent import UserAgent # change user agent
import time     # to respect page rules
from bs4 import BeautifulSoup as BS
# import codecs
from URLCollector import URLFront
import pprint

__author__ = 'Arne Binder'


def parsePetition(url):
    page = URLFront.requestPage(url)
    result = {}
    soup = BS(page.decode('utf-8', 'ignore'), "html.parser")
    petition = soup.select('div#main div.content > div > div > div.col2')[0]
    result['claimShort'] = petition.find("h2").text
    content = petition.find("div", "text")

    result['claim'] = content("p")[0].text
    result['ground'] = content("p")[1].text
    return result


def parseDebate(url):
    page = URLFront.requestPage(url)
    result = {}
    soup = BS(page.decode('utf-8', 'ignore'), "html.parser")

    argGroups = soup.select('div.petition-argumente > div > div > div.col2 > div > div.twocol')

    argsPro = []
    argsCon = []

    for argGroup in argGroups:
        articles = argGroup("article")
        args = []

        for article in articles:
            newArgument = {}
            tags = article.find("ul", "tags")
            if tags is not None:
                newArgument['tags'] = tags.text
            newArgument['content'] = article.find("div", "text").text
            args.append(newArgument)

        polarity = argGroup.find("h2", "h1").text
        if polarity == "Pro":
            # print "pro"
            argsPro.append(args)
        elif polarity == "Contra":
            # print "contra"
            argsCon.append(args)
        else:
            print "no"

    return {'argumentsPro': argsPro, 'argumentsCon': argsCon}


def parseComments(url):
    page = URLFront.requestPage(url)
    soup = BS(page.decode('utf-8', 'ignore'), "html.parser")
    comments = soup.select('article.kommentar > div.text')
    return [comment.select(' > p')[1].text for comment in comments]


def parse(url):
    result = parsePetition(url)
    result['arguments'] = parseDebate(url.replace("/online/", "/argumente/"))
    result['comments'] = parseComments(url.replace("/online/", "/kommentare/"))
    return result


def main():
    front = URLFront(["https://www.openpetition.de/?status=in_zeichnung"])
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(parse("https://www.openpetition.de/petition/online/versorgung-mit-lymphdrainage-in-gefahr-aenderung-der-heilmittel-richtlinie-abwenden"))
    # print parse("https://www.openpetition.de/petition/online/versorgung-mit-lymphdrainage-in-gefahr-aenderung-der-heilmittel-richtlinie-abwenden")


if __name__ == "__main__":
    main()