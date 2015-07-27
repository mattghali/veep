#!/usr/bin/env python

import netaddr 


depot = 'depot.example.com'

blacklists = {
    'region': [ 'cn-north-1', 'us-gov-west-1' ],
    'az':     [ 'ap-northeast-1a', 'us-west-1b' ]
}

userdata = ''.join([ '#!/usr/bin/env bash\n\n',
                     'yum -y install aws-cli ec2-utils\n',
                     'aws s3 cp s3://' + depot + '/bootstrap/global - | sh -x\n'])
