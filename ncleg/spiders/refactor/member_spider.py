import scrapy
import re
import pandas as pd
from ncleg.items import VoteHistory

class MemberSpider(scrapy.Spider):

    def __init__(self):
        """
        WIP - A spider that crawls a member biographies and metadata.
        """
        self.NAME_PATTERN = "Vote History: Representative (\w+, \w|\w+-\w+|\w+)"
        self.DISTRICT_PATTERN = "District (\d+)"
        self.NAME_DISTRICT_PATTERN = "Vote History: (Senator|Representative)(.*) (?:\((District [0-9]+)\))"


    def get_name_district(self, title):
        try:
            short_name = re.search(self.NAME_PATTERN, title).group(1)
            district = re.search(self.DISTRICT_PATTERN, title).group(1)
        except:
            #If there is no voter data available, fill with empty strings
            title = ''
            short_name = ''
            district = ''
        return short_name, district