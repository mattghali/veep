#!/usr/bin/env python

import boto.iam, datetime, json, uuid


class P_any(str):
    """Instances of this object are used to define Principals in a Statement.
    This object takes no arguments at constuction and creates the special
    Principal type of `*` (any).

    Args: None.
    """
    def __new__(cls):
        return str.__new__(cls, '*')

class P_aws(dict):
    """Instances of this object are used to define Principals in a Statement.
    This object takes an arn argument at construction and creates a Principal
    type of "AWS": <arn>.

    Args:
        param1  (str or list) One or more ARNs.
    """
    def __init__(self, args):
        if type(args) == list or type(args) == tuple: self.update({'AWS': args})
        if type(args) == str: self.update({'AWS': [args]})


class Policy(dict):
    """Contains one or more Statement objects and returns an object
    suitable for passing as a policy to IAM api calls.

    **kwargs:
        id (str): Policy ID (optional)
        version (str): Policy version (optional)
        statements (list): one or more Statement instances
    """
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
    """Container assembling principals, condtions, actions and resources.

    **kwargs:
        sid (str): Statement ID (optional)
        effect (str): Effect- Allow/Deny (optional)
        principal (str): instance of Principal object (optional)
        actions (list): one or more actions
        resources (list): one or more resource ARNs
    """
    def __init__(self, **kwargs):
        self.update({ 'Sid': kwargs.get('sid', str(uuid.uuid4())),
                      'Effect': kwargs.get('effect', 'Allow'),
                      'Principal': kwargs.get('principal', P_any()),
                      'Action': kwargs.get('actions', None),
                      'Resource': kwargs.get('resources', None)})

        conditions = kwargs.get('conditions', [])
        if conditions:
            if type(conditions) == list:
                t = dict()
                for c in conditions:
                    t.update(c)
                self.update({'Condition': t})
            else:
                self.update({'Condition': conditions})


class Condition(dict):
    """Instance defines a condition applied to a Statement.

    Args:
        cond_test (str): An IAM condition.
        val_type (str): Key for value from request
        val_data (str): Value for comparison
    """
    def __init__(self, cond_test, val_type, val_data):
        self.update({cond_test: { val_type: val_data }})


class Certificate(object):
    """Object returned by get_certificates(), with expiration date
    converted into a datetime.datetime() object.
    """
    def __init__(self, connection, **kwargs):
        self.connection = connection
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

    def delete(self):
        """Deletes the certificate from the IAM cert store."""
        return self.connection.delete_server_cert(self.name)

    def update(self, **kwargs):
        """Updates the name and/or path attribute of an existing certificate.

        **kwargs:
            name (str): New name for certificate. (optional)
            path (str): New path for certificate. (optional)
        """
        name = kwargs.get('name', self.name)
        path = kwargs.get('path', self.path)
        return self.connection.update_server_cert(self.name, new_cert_name=name, new_path=path)


class Profile(object):
    """Object returned by create_profile() and get_profile(), with creation
    date converted into a datetime.datetime() object.
    """
    def __init__(self, connection, **kwargs):
        self.connection = connection
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
        """Add a Role to this Profile. 

        Args:
            role (Role): Instance of Role object to attach to profile.
        """
        self.connection.add_role_to_instance_profile(self.name, role.name)
        

class Role(object):
    """Object returned by create_role() and get_role(), with creation
    date converted into a datetime.datetime() object.
    """
    def __init__(self, connection, **kwargs):
        self.connection = connection
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


def connect(**kwargs):
    """Create veep.IAM connection object

    Returns:
        instance of veep.IAM.IAMConnection
    """
    return IAMConnection(**kwargs)


class IAMConnection(boto.iam.IAMConnection):
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, **kwargs):
        super(IAMConnection, self).__init__(aws_access_key_id, aws_secret_access_key, **kwargs)

    def list_server_certs(self):
        """Yields a list of server certificates stored in the account as
        Certificate object instances.

        Returns:
            iterator of Certificate instances.
        """
        ret = super(IAMConnection, self).list_server_certs()
        for i in ret['list_server_certificates_response']['list_server_certificates_result']['server_certificate_metadata_list']:
            yield Certificate(self, **i)


    def create_instance_profile(self, name, **kwargs):
        """Create an instance profile.

        args:
            name (str): Name of profile to create.

        **kwargs:
            path (str): Optional path for profile.

        Returns:
            instance of Profile
        """
        path = kwargs.get('path', '/instance/')

        r = super(IAMConnection, self).create_instance_profile(name, path)
        p = r['create_instance_profile_response']['create_instance_profile_result']['instance_profile']
        return Profile(self, **p)


    def get_instance_profile(self, name):
        """Find an instance profile by name.

        args:
            name (str): Name of profile to select.

        Returns:
            instance of Profile
        """

        try:
            r = super(IAMConnection, self).get_instance_profile(name)
        except boto.exception.BotoServerError, e:
            if e[0] == 404:
                return None
            else: raise e

        p = r['get_instance_profile_response']['get_instance_profile_result']['instance_profile']
        return Profile(self, **p)


    def create_role(self, name, **kwargs):
        """Create a role.

        args:
            name (str): Name of role to create.

        **kwargs:
            path (str): Optional path for role.
            assume_role_policy_document (str): A polcy document.

        Returns:
            instance of Role
        """
        path = kwargs.get('path', '/instance/')
        assume_role_policy_document = kwargs.get('assume_role_policy_document', None)

        r = super(IAMConnection, self).create_role(name, path=path,
                                        assume_role_policy_document=assume_role_policy_document)
        p = r['create_role_response']['create_role_result']['role']
        return Role(self, **p)


    def get_role(self, name):
        """Find role by name.

        args:
            name (str): Name of role to select.

        Returns:
            instance of Role
        """

        try:
            r = super(IAMConnection, self).get_role(name)
        except boto.exception.BotoServerError, e:
            if e[0] == 404:
                return None
            else: raise e

        p = r['get_role_response']['get_role_result']['role']
        return Role(self, **p)

    def get_user_arn(self):
        """Returns arn for effective IAM user

        Returns:
            (str) AWS account arn
        """

        getuser = self.get_user()
        return getuser['get_user_response']['get_user_result']['user']['arn']

