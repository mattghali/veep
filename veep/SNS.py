#!/usr/bin/env python

import boto.exception, boto.sns


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
        s_list = subs['ListSubscriptionsByTopicResponse']['ListSubscriptionsByTopicResult']['Subscriptions']
        return [Subscription(self, i) for i in s_list]

    def subscribe(self, proto, endpoint):
        r = self.connection.subscribe(self.arn, proto, endpoint)['SubscribeResponse']['SubscribeResult']
        r['TopicArn'] = self.arn
        r['Owner'] = self.arn.split(':')[4]
        r['Endpoint'] = endpoint
        r['Protocol'] = proto
        return Subscription(self, r)

    def unsubscribe(self, sub_arn):
        return self.connection.unsubscribe(sub_arn)

    def confirm(self, token, aos=False):
        try:
            return self.connection.confirm_subscription(self.arn,
                token, authenticate_on_unsubscribe=aos)['ConfirmSubscriptionResponse']['ConfirmSubscriptionResult']
        except boto.exception.BotoServerError, e:
            if e[0] == 400:
                return False
            else: raise e


class Subscription(object):
    def __init__(self, topic, sub_res):
        self.topic = topic
        self.connection = topic.connection
        self.topicarn = sub_res['TopicArn']
        self.owner = sub_res['Owner']
        self.endpoint = sub_res['Endpoint']
        self.protocol = sub_res['Protocol']
        self.proto = self.protocol
        self.confirmed = sub_res['SubscriptionArn'] != 'PendingConfirmation'

        if self.confirmed:
            self.subscriptionarn = sub_res['SubscriptionArn']
            self.arn = self.subscriptionarn
            self.name = self.subscriptionarn.split(':')[-1]
        else:
            self.subscriptionarn = None
            self.arn = None
            self.name = sub_res['SubscriptionArn']

    def __repr__(self):
        return self.name

    def confirm(self, token, aos=False):
        res = self.topic.confirm(token, aos=aos)
        if res:
            self.subscriptionarn = res['SubscriptionArn']
            self.arn = self.subscriptionarn
            self.name = self.arn.split(':')[-1]
            self.confirmed = True
            return True
        else:
            return False


class SNSConnection(boto.sns.connection.SNSConnection):
    def __init__(self, **kwargs):
        super(SNSConnection, self).__init__(**kwargs)

    def get_all_topics(self):
        topic_res = super(SNSConnection, self).get_all_topics()
        return [Topic(self, i) for i in topic_res['ListTopicsResponse']['ListTopicsResult']['Topics']]

    def get_topic(self, name):
        for topic in self.get_all_topics():
            if topic.name == name:
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
