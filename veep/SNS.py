#!/usr/bin/env python

import boto.sns


class Topic(object):
    def __init__(self, conn, topic_res):
        self.conn = conn
        self.topic_res = topic_res
        self.arn = self.topic_res['TopicArn']
        self.name = self.arn.split(':')[-1]

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __cmp__(self, obj):
        if obj == self.name:
            return 0
        else:
            return 1

    def get_subscriptions(self):
        subs = self.conn.get_all_subscriptions_by_topic(self.arn)
        return subs['ListSubscriptionsByTopicResponse']['ListSubscriptionsByTopicResult']['Subscriptions']

    def subscribe(self, sub):
        (proto, endpoint) = sub
        self.conn.subscribe(self.arn, proto, endpoint)
        return True

    def unsubscribe(self, sub_arn):
        self.conn.unsubscribe(sub_arn)


def get_all_topics(conn):
    topic_res = conn.get_all_topics()
    return [Topic(conn, i) for i in topic_res['ListTopicsResponse']['ListTopicsResult']['Topics']]


def get_topic(conn, name):
    topics = get_all_topics(conn)
    for topic in topics:
        if topic == name:
            return topic
    return None


def create_topic(conn, name):
    topic_res = conn.create_topic(name)
    return Topic(conn, topic_res['CreateTopicResponse']['CreateTopicResult'])


def connect(region):
    return boto.sns.connect_to_region(region)


