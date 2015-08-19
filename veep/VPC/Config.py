#!/usr/bin/env python

from LocalConfig import *


blacklists = {
    'region': [ 'cn-north-1', 'us-gov-west-1' ],
    'az':     [ 'ap-northeast-1a', 'us-east-1b', 'us-west-1a' ]
}

userdata = ''.join([ '#!/usr/bin/env bash\n\n',
                     'yum -y install aws-cli ec2-utils\n',
                     'aws s3 cp s3://' + depot + '/boot/base - | sh -x\n'])
