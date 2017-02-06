import scrapy
import re
import pandas as pd
from ncleg.items import VoteHistory

class BillSpider(scrapy.Spider):

    def __init__(self):
        """
        WIP - A spider that crawls a bill text and metadata.
        """
        self.MOTION_PATTERN = "(A\d|Motion \d+|Suspend Rules|R\d+|M\d+|C RPT)"
        self.READING_PATTERN = "(2nd Reading|Second Reading|Third Reading|3rd Reading)"
        self.MOTION_NAME_PATTERN = "A\d+ (\w+, \w.|\w+)"  # Assumes A only
        self.BILL_ID_PATTERN = "&BillID=(\w+)"
        
        # Dict of lookup words to convert words like 'First' to 1
        self.word_to_num = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
            "sixth": 6,
            "seventh": 7,
            "eighth": 8,
            "ninth": 9,
            "tenth": 10,
        }

        self.readings = {
            '2nd Reading': 2,
            'Second Reading': 2,
            'Third Reading': 3,
            '3rd Reading': 3,
        }


    def get_doc_num_href(self, row):
        # If doc has a len greater than 1, then text is present. If so, grab name and url.
        try:
            doc_num = row.xpath("td[2]/a/text()").extract_first()
            doc_href = ''
            if len(doc_num) > 0:
                doc_num = doc_num[0].replace(" ", "")
                doc_href = self.base_url + row.xpath("td[2]/a/@href").extract_first()
        except:
            doc_href = ''
            doc_num = ''
        return doc_href, doc_num

    def get_reading_motion(self, subject_motion):
        reading = 1
        motion = ''
        motion_name = ''
        #If subject is multiple lines, then process second line. First line is the subject
        if len(subject_motion) > 1:

            #find number of readings. Search doesn't have a len. If it fails finding reading, reading = 1
            try:
                reading_search = re.search(self.READING_PATTERN, subject_motion[1]).group(0)
                if reading_search in self.readings:
                    reading = self.readings[reading_search]
            except:
                reading = 1
            try:
                motion = re.search(self.MOTION_PATTERN, subject_motion[1]).group(0)
            except:
                motion = ''

            try:
                motion_name = re.search(self.MOTION_NAME_PATTERN, subject_motion[1]).group(0)
            except:
                motion_name = ''
        return reading, motion, motion_name