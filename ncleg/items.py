# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class VoteHistory(scrapy.Item):
    """
    Bill Information
    """
    #Required
    url = scrapy.Field()
    rep_id = scrapy.Field()
    rep_short_name = scrapy.Field()
    district = scrapy.Field()
    chamber = scrapy.Field()
    session = scrapy.Field()
    recess = scrapy.Field()
    subject_motion = scrapy.Field()
    timestamp = scrapy.Field()
    vote = scrapy.Field()

    #Not all subjects have motions or doc numbers
    doc_num = scrapy.Field()
    doc_href = scrapy.Field()

    #Subject/Motion Information for Validation
    aye_tot = scrapy.Field()
    no_tot = scrapy.Field()
    no_vote_tot = scrapy.Field()
    excused_abs_tot = scrapy.Field()
    excused_vote_tot = scrapy.Field()
    tot_votes = scrapy.Field()
    result = scrapy.Field()

class BillsItems():
    #A bill may have both or just one. CSS class = identicalBill if both
    house_bill_id = scrapy.Field()
    senate_bill_id  = scrapy.Field()
    bill_title = scrapy.Field()
    bill_sub_title = scrapy.Field()
    session = scrapy.Field()
    primary_sponsors = scrapy.Field()
    other_sponsors = scrapy.Field()
    attributes = scrapy.Field()
    counties = scrapy.Field() # may not have counties associated to bill
    statutes = scrapy.Field()
    keywords = scrapy.Field()
    house_history = scrapy.Field() # stored as array of events
    senate_history = scrapy.Field() # stored as array of events


