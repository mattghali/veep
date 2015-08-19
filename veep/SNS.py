#!/usr/bin/env python

import boto.sns


class Topic(object):
    def __init__(self, connection, topic_res):
        self.connection = connection
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
        subs = self.connection.get_all_subscriptions_by_topic(self.arn)
        return subs['ListSubscriptionsByTopicResponse']['ListSubscriptionsByTopicResult']['Subscriptions']

    def subscribe(self, sub):
        (proto, endpoint) = sub
        self.connection.subscribe(self.arn, proto, endpoint)
        return True

    def unsubscribe(self, sub_arn):
        self.connection.unsubscribe(sub_arn)

class SNSConnection(boto.sns.connection.SNSConnection):
    def __init__(self, **kwargs):
        super(SNSConnection, self).__init__(**kwargs)

    def get_all_topics(self):
        topic_res = super(SNSConnection, self).get_all_topics()
        return [Topic(self, i) for i in topic_res['ListTopicsResponse']['ListTopicsResult']['Topics']]

    def get_topic(self, name):
        topics = self.get_all_topics()
        for topic in topics:
            if topic == name:
                return topic
        return None

    def create_topic(self, name):
        topic_res = super(SNSConnection, self).create_topic(name)
        return Topic(self, topic_res['CreateTopicResponse']['CreateTopicResult'])



def connect_to_region(region_name, **kw_params):
    """
    Given a valid region name, return a
    :class:`veep.IAM.SNSConnection`.

    :type: str
    :param region_name: The name of the region to connect to.

    :rtype: :class:`veep.IAM.SNSConnection` or ``None``
    :return: A connection to the given region, or None if an invalid region
             name is given
    """
    regions = boto.sns.get_regions('sns', connection_cls=SNSConnection)

    for region in regions:
        if region.name == region_name:
            return region.connect(**kw_params)
    return None
