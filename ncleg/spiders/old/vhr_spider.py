import scrapy
import re

class VHRSpider(scrapy.Spider):
    name = "vhr"
    allowed_domains = ['ncleg.net']

    def __init__(self):
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

    def start_requests(self):
        # urls = ['http://www.ncleg.net/Legislation/voteHistory/voteHistory.html']
        # for url in urls:
        #     yield scrapy.Request(url=url, callback=self.parse_vote_history_list)

        #TESTING SPIDER
        test_urls = ['http://www.ncleg.net/gascripts/voteHistory/MemberVoteHistory.pl?sSession=2015E5&sChamber=H']
        for url in test_urls:
            yield scrapy.Request(url=url, callback=self.parse_find_reps_session)


    def parse_vote_history_list(self, response):
        house_list = []
        senate_list = []
        all_urls = response.xpath("""//*[contains(@href, 'a')]/@href""").extract()

        house_vote_regex = "MemberVoteHistory.pl\?sSession=\w+&sChamber=H|MemberVoteHistory.pl\?sSession=\w+&sChamber=S"
        senate_vote_regex = "MemberVoteHistory.pl\?sSession=\w+&sChamber=S"
        base_votehist_url = "http://www.ncleg.net/gascripts/voteHistory/"

        #find matching urls
        for item in all_urls:
            house_partial_result = re.search(house_vote_regex, item)
            senate_partial_result = re.search(senate_vote_regex, item)
            if house_partial_result:
                house_list.append(base_votehist_url + house_partial_result.group(0))
            if senate_partial_result:
                senate_list.append(base_votehist_url + senate_partial_result.group(0))

        for href in house_list:
            yield scrapy.Request(url=href, callback=self.parse_find_reps_session)

    def parse_find_reps_session(self, response):
        #grabs all hrefs on the site
        all_urls = response.xpath("""//*[contains(@href, 'a')]/@href""").extract()
        found_rep = []
        base_url = "http://www.ncleg.net/gascripts/voteHistory/MemberVoteHistory.pl?"

        #Out of all the urls found, regex search for ones that match the rep_regex,
        #then parse the vote history
        for url in all_urls:
            result = re.search(self.REP_REGEX, url)
            if result:
                full_url = base_url + result.group(0)
                yield scrapy.Request(url=full_url, callback=self.parse_rep_vote_history)

    def parse_rep_vote_history(self, response):
        #Some reps did not vote during a session. Test for the "Vote data is unavailable.
        #We capture the base information about the rep for later matching
        if "Vote data is unavailable" in response.xpath("""//*[@id="mainBody"]/text()""").extract()[3]:
            cur_url = response.url
            session_id, chamber, rep_id = self.get_session_chamber_rep_id(cur_url)
            url = cur_url
            self.rep_info.append([rep_id, session_id, chamber])
        #Otherwise, we process the body of text.
        else:
            table_rows = response.xpath('//*[@id="mainBody"]/table[1]/tr')
            cur_url = response.url
            title = response.xpath("""//*[@id="title"]/text()""").extract_first()
            #First row of the table is the headers. Don't need those
            for row in table_rows[1:]:
                self.process_row(row, cur_url, title)
        session_id, chamber, rep_id = self.get_session_chamber_rep_id(cur_url)
        print("*"*50)
        print(session_id)
        self.save_results(session_id)
        self.rep_vote = []
        self.rep_info = []
        self.bill_info = []

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

    def process_row(self, row, url, title):
        session_id, chamber, rep_id = self.get_session_chamber_rep_id(url)
        rep_short_name, district = self.get_name_district(title)

        rep_short_name, district = rep_short_name, district

        recess = row.xpath("td[1]/text()").extract_first()

        doc_href, doc_num = self.get_doc_num_href(row)

        # Not all subjects have motions. Subjects and motions get mixed up.
        # Need to build a tester for processing data
        subject_motion = row.xpath("td[3]/text()").extract()
        timestamp = row.xpath("td[4]/text()").extract_first()
        vote = row.xpath("td[5]/text()").extract_first()

        # Subject/Motion Information for Validation
        aye_tot = row.xpath("td[6]/text()").extract_first()
        no_tot = row.xpath("td[7]/text()").extract_first()
        no_vote_tot = row.xpath("td[8]/text()").extract_first()
        excused_abs_tot = row.xpath("td[9]/text()").extract_first()
        excused_vote_tot = row.xpath("td[10]/text()").extract_first()
        tot_votes = row.xpath("td[11]/text()").extract_first()
        result = row.xpath("td[12]/text()").extract_first()
        reading, motion, motion_name = self.get_reading_motion(subject_motion)

        bill_id = session_id + '_' + recess
        self.rep_info.append([rep_id, session_id, chamber, rep_short_name, district])
        self.rep_vote.append([rep_id, session_id, bill_id, vote, timestamp, reading, motion, motion_name])
        self.bill_info.append([bill_id, chamber, session_id, doc_num, doc_href, timestamp, subject_motion, result, aye_tot, no_tot, no_vote_tot, excused_abs_tot, excused_vote_tot, tot_votes])

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