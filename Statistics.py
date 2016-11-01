import csv
import sys
import json
from os import listdir
from os.path import isfile, isdir, join

__author__ = 'Arne Binder'

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
    captions = ["id", "argument_count", "argument_count_pro", "argument_count_con", "argument_length_min_chars",
                "argument_length_max_chars", "argument_length_avg_chars", "argument_length_min_words",
                "argument_length_max_words", "argument_length_avg_words", "reply_count", "reply_length_min_chars",
                "reply_length_max_chars", "reply_length_avg_chars", "reply_length_min_words", "reply_length_max_words",
                "reply_length_avg_words", "state", "question"]
    statRecords = []
    sections = [f for f in listdir(inPath) if isdir(join(inPath, f))]
    for section in sections:
        sectionPath = join(inPath, section)
        debateIDs = [f[:-len('.json')] for f in listdir(sectionPath) if isfile(join(sectionPath, f))]
        for debateID in debateIDs:
            with open(join(sectionPath, debateID+'.json')) as data_file:
                data = json.load(data_file)
                print join(sectionPath, debateID+'.json')
                debateStats = {'id':debateID}
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
                statRecords.append(debateStats)

    with open(csvOutPath, 'w') as tsvFile:
        writer = UnicodeDictWriter(tsvFile, fieldnames=captions, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(statRecords)

class UnicodeDictWriter(csv.DictWriter):
    def _dict_to_list(self, rowdict):
        if self.extrasaction == "raise":
            wrong_fields = [k for k in rowdict if k not in self.fieldnames]
            if wrong_fields:
                raise ValueError("dict contains fields not in fieldnames: "
                                 + ", ".join([repr(x) for x in wrong_fields]))
        return [rowdict.get(key, self.restval).encode('utf-8') if type(rowdict.get(key, self.restval)) is unicode else rowdict.get(key, self.restval) for key in self.fieldnames]
