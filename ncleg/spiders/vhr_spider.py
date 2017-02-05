import scrapy
import re
import pandas as pd
from ncleg.items import VoteHistory

class VHRSpider(scrapy.Spider):
    name = "test"
    allowed_domains = ['ncleg.net']

    def __init__(self):
        """
        A spider that crawls a reps voting history
        """
        self.URL_PATTERN = "sSession=([1-3][0-9]{3}\w\d|[1-3][0-9]{3})&sChamber=(\w){1}&nUserID=(\d+)"
        self.NAME_PATTERN = "Vote History: Representative (\w+, \w|\w+-\w+|\w+)"
        self.DISTRICT_PATTERN = "District (\d+)"
        self.EXTRA_SESSION_PATTERN = "(\d+) (\w+)"
        self.YEAR_SESSION_PATTERN = "([1-3][0-9]{3})-([1-3][0-9]{3})"
        self.MOTION_PATTERN = "(A\d|Motion \d+|Suspend Rules|R\d+|M\d+|C RPT)"
        self.READING_PATTERN = "(2nd Reading|Second Reading|Third Reading|3rd Reading)"
        self.MOTION_NAME_PATTERN = "A\d+ (\w+, \w.|\w+)"  # Assumes A only
        self.BILL_ID_PATTERN = "&BillID=(\w+)"
        self.REP_REGEX = "sSession=\w+&sChamber=H&nUserID=\w+|sSession=\w+&sChamber=S&nUserID=\w+"
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

        self.base_url = "http://www.ncleg.net"
        self.rep_vote = []
        self.rep_info = []
        self.bill_info = []
        self.rep_parsed = []

    def start_requests(self):
        yield scrapy.Request(url=self.base_url, callback=self.get_available_sessions)

    def get_members_for_session(self, session_ids):
        chambers = ['H','S']
        begin_year = 2007

        member_history_base = 'http://www.ncleg.net/gascripts/voteHistory/MemberVoteHistory.pl?sSession={}&sChamber={}'
        member_history_urls = [member_history_base.format(session, chamber) for session in session_ids for chamber in chambers if int(session[:4]) >= begin_year]

        for url in member_history_urls[1:2]:
            yield scrapy.Request(url=url, callback=self.parse_find_reps_session)

    def get_available_sessions(self, response):
        session_names = response.css('#MastheadBar select[name="Session"] > option::text').extract()
        session_ids = response.css('#MastheadBar select[name="Session"] > option::attr(value)').extract()
        return self.get_members_for_session(session_ids)
        
    def parse_find_reps_session(self, response):
        #grabs all hrefs on the site
        #all_urls = response.xpath("""//*[contains(@href, 'a')]/@href""").extract()
        all_urls = response.css('#mainBody > ul > li > a::attr(href)').extract()

        #found_rep = []
        base_url = "http://www.ncleg.net"


        #Out of all the urls found, regex search for ones that match the rep_regex,
        #then parse the vote history
        for url in all_urls:
            full_url = base_url + url
            session_id, chamber, rep_id = self.get_session_chamber_rep_id(full_url)
            yield scrapy.Request(url=full_url, callback=self.parse_rep_vote_history)


    def parse_rep_vote_history(self, response):
        # Some reps did not vote during a session. Test for the "Vote data is unavailable.
        # We capture the base information about the rep for later matching
        if "Vote data is unavailable" in response.css("#mainBody::text").extract()[3]:
            cur_url = response.url
            session_id, chamber, rep_id = self.get_session_chamber_rep_id(cur_url)
            url = cur_url
            self.rep_info.append([rep_id, session_id, chamber])
        #Otherwise, we process the body of text.
        else:
            table_rows = response.css('#mainBody > table').extract()[0]
            
            pd_table = pd.read_html(table_rows, header=0, match="Doc.", attrs={'cellspacing':0})[0][['RCS\xa0#', 'Doc.','Vote','Result']]
            
            cur_url = response.url
            session_id, chamber, rep_id = self.get_session_chamber_rep_id(cur_url)
            
            pd_table['session_id'] = session_id
            pd_table['chamber'] = chamber
            pd_table['rep_id'] = rep_id

            pd_table = pd_table.reindex_axis(['session_id', 'chamber', 'rep_id', 'RCS\xa0#', 'Doc.', 'Vote', 'Result'], axis=1)

            return pd_table.to_dict(orient='records')


    def get_session_chamber_rep_id(self, url):
        """
        Takes the current url that the scraper is on and processes it
        :param url:
        :return:
        """
        matches = re.search(self.URL_PATTERN, url)
        session_id = matches.group(1)
        chamber = matches.group(2)
        rep_id = matches.group(3)
        return session_id, chamber, rep_id


    def save_results(self, session_id):
        import csv
        with open("rep_info_{}.csv".format(session_id), "a") as f:
            writer = csv.writer(f)
            for row in self.rep_info:
                writer.writerow(row)
        with open("rep_vote_{}.csv".format(session_id), "a") as f:
            writer = csv.writer(f)
            for row in self.rep_vote:
                writer.writerow(row)
        with open("bill_info_{}.csv".format(session_id), "a") as f:
            writer = csv.writer(f)
            for row in self.bill_info:
                writer.writerow(row)