#!/usr/bin/env python

import os, sys
from ConfigParser import SafeConfigParser



self = sys.modules[__name__]

# read in environment variables for config file and section
vars = (('VEEP_CONFIG_FILE', 'cfg_path', os.path.join(os.environ['HOME'], '.veep.cfg')),
        ('VEEP_CONFIG_PROFILE', 'cfg_section', 'DEFAULT'))

for (env_name, var_name, default) in vars:
    if os.environ.has_key(env_name):
        setattr(self, var_name, os.environ[env_name])
    else:
        setattr(self, var_name, default)


# you're going to want to override these in your ~/.veep.cfg
home_region = 'us-west-2'
depot = 'depot.snark.net'
ct_bucket = 'cloudtrail.snark.net'

# Other handy things to define
blacklists = {
    'region': [ 'cn-north-1', 'us-gov-west-1' ],
    'az':     [ 'ap-northeast-1a', 'us-east-1b', 'us-west-1a' ]
}

userdata = ''.join([ '#!/usr/bin/env bash\n\n',
                     'yum -y install aws-cli ec2-utils\n',
                     'aws s3 --region=' + home_region + ' cp s3://' + depot + '/boot/base - | sh -x\n'])


# Read in values from your dotfile
parser = SafeConfigParser()
if parser.read(cfg_path):
    for (name, value) in parser.items(cfg_section):
        setattr(self, name, value)


