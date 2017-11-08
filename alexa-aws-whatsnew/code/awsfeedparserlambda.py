from __future__ import print_function

import json
from botocore.vendored import requests
import feedparser
import boto3
from datetime import datetime
from datetime import timedelta
import time
import re
import os

def cleanhtml(raw_html):
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  cleantext = cleantext.replace('&nbsp;','')
  return cleantext


def lambda_handler(event, context):
    aws_rss_url = "https://aws.amazon.com/new/feed/"
    aws_feed_tbl = os.environ['awslaunchdetails_tbl']
    ttl_days = int(os.environ['retention_value'])
    feed = feedparser.parse( aws_rss_url )
    dynamo_tbl = boto3.resource('dynamodb').Table(aws_feed_tbl)
    filter_date = datetime.now() - timedelta(days=1)
    expiry_date = datetime.now() + timedelta(days=ttl_days)
    expiry_epoch = long(time.mktime(expiry_date.timetuple()))

    for item in feed[ "items" ]:
        record={}
        record["guid"]=item["guid"]
        record["title"]=item[ "title" ]
        record["description"]=cleanhtml(item["description"])
        record["url"]=item["link"]
        record["catagories"]=[]
        record["ttl"]=expiry_epoch
        for tag in item["tags"]:
            categories=tag["term"].split(",")
            for everyCat in categories:
                result=everyCat.partition("aws-")
                if not result[2]:
                    result=everyCat.partition("amazon-")
            if result[2]:
                text = result[2].replace("-"," ")
                record["catagories"].append(text)
        offset_str = item["published"].rpartition(' ')
        pub_datetime = datetime.strptime(offset_str[0], '%a, %d %b %Y %H:%M:%S')
        record["pub_date"]=pub_datetime.strftime("%Y-%m-%d")
        if pub_datetime > filter_date:
            dynamo_tbl.put_item(Item=record)
