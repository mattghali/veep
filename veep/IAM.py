#!/usr/bin/env python

import boto.iam, datetime, json, uuid


class P_any(str):
    def __new__(cls):
        return str.__new__(cls, '*')

class P_aws(dict):
    def __init__(self, args):
        if type(args) == list or type(args) == tuple: self.update({'AWS': args})
        if type(args) == str: self.update({'AWS': [args]})


class Policy(dict):
    def __init__(self, **kwargs):
        self.update({ 'Id': kwargs.get('id', str(uuid.uuid4())),
                      'Version': kwargs.get('version', '2012-10-17')})
        statements = kwargs.get('statements', None)
        if type(statements) == list:
            self.update({'Statement': statements})
        else:
            self.update({'Statement': [statements]})

    def __str__(self):
        return json.dumps(self)

    def __repr__(self):
        return str(self)


class Statement(dict):
    def __init__(self, **kwargs):
        self.update({ 'Sid': kwargs.get('sid', str(uuid.uuid4())),
                      'Effect': kwargs.get('effect', 'Allow'),
                      'Principal': kwargs.get('principal', P_any()),
                      'Action': kwargs.get('actions', None),
                      'Resource': kwargs.get('resources', None)})

        conditions = kwargs.get('conditions', [])
        if type(conditions) == list:
            t = dict()
            for c in conditions:
                  t.update(c)
            self.update({'Condition': t})
        else:
            self.update({'Condition': conditions})


class Condition(dict):
    def __init__(self, cond_test, val_type, val_data):
        self.update({cond_test: { val_type: val_data }})


class Certificate(object):
    def __init__(self, **kwargs):
        self.upload_date = kwargs.get('upload_date', None)
        self.server_certificate_id = kwargs.get('server_certificate_id', None)
        self.server_certificate_name = kwargs.get('server_certificate_name', None)
        self.path = kwargs.get('path', None)
        self.arn = kwargs.get('arn', None)

        expiration = kwargs.get('expiration', None)
        self.expiration = datetime.datetime.strptime(expiration.split('Z')[0], '%Y-%m-%dT%H:%M:%S')

        self.name = self.server_certificate_name
        self.id = self.server_certificate_id

    def __str__(self):
        return self.arn

    def __repr__(self):
        return str(self)


class Profile(object):
    def __init__(self, conn, **kwargs):
        self.conn = conn
        self.instance_profile_name = kwargs.get('instance_profile_name', None)
        self.instance_profile_id = kwargs.get('instance_profile_id', None)
        self.roles = kwargs.get('roles', [])
        self.path = kwargs.get('path', None)
        self.arn = kwargs.get('arn', None)

        create_date = kwargs.get('create_date', None)
        self.create_date = datetime.datetime.strptime(create_date[:19], '%Y-%m-%dT%H:%M:%S')

        self.id = self.instance_profile_id
        self.name = self.instance_profile_name

    def __str__(self):
        return self.arn

    def __repr__(self):
        return str(self)

    def add_role(self, role):
        self.conn.add_role_to_instance_profile(self.name, role.name)
        

class Role(object):
    def __init__(self, conn, **kwargs):
        self.conn = conn
        self.role_name = kwargs.get('role_name', None)
        self.role_id = kwargs.get('role_id', None)
        self.assume_role_policy_document = kwargs.get('assume_role_policy_document', None)
        self.path = kwargs.get('path', None)
        self.arn = kwargs.get('arn', None)

        create_date = kwargs.get('create_date', None)
        self.create_date = datetime.datetime.strptime(create_date[:19], '%Y-%m-%dT%H:%M:%S')

        self.id = self.role_id
        self.name = self.role_name

    def __str__(self):
        return self.arn

    def __repr__(self):
        return str(self)


def get_certificates(conn):
    ret = conn.list_server_certs()
    for i in ret['list_server_certificates_response']['list_server_certificates_result']['server_certificate_metadata_list']:
        yield Certificate(**i)


def create_profile(conn, **kwargs):
    name = kwargs.get('name', None)
    path = kwargs.get('path', '/instance/')

    r = conn.create_instance_profile(name, path)
    p = r['create_instance_profile_response']['create_instance_profile_result']['instance_profile']
    return Profile(conn, **p)


def get_profile(conn, **kwargs):
    name = kwargs.get('name', None)

    try:
        r = conn.get_instance_profile(name)
    except boto.exception.BotoServerError, e:
        if e[0] == 404:
            return None
        else: raise e

    p = r['get_instance_profile_response']['get_instance_profile_result']['instance_profile']
    return Profile(conn, **p)


def create_role(conn, **kwargs):
    name = kwargs.get('name', None)
    path = kwargs.get('path', '/instance/')
    assume_role_policy_document = kwargs.get('assume_role_policy_document', None)

    r = conn.create_role(name, path=path, assume_role_policy_document=assume_role_policy_document)
    p = r['create_role_response']['create_role_result']['role']
    return Role(conn, **p)


def get_role(conn, **kwargs):
    name = kwargs.get('name', None)

    try:
        r = conn.get_role(name)
    except boto.exception.BotoServerError, e:
        if e[0] == 404:
            return None
        else: raise e

    p = r['get_role_response']['get_role_result']['role']
    return Role(conn, **p)


def connect(region='us-west-2'):
    return boto.iam.connect_to_region(region)

