#!/usr/bin/env python

import boto.vpc

import Config
from region import Region
from tier import Tier
from vpc import Vpc

__all__ = [ 'Config', 'Region', 'Tier', 'Vpc' ]


def find(**kwargs):
    """Find VPCs by name or ID across all regions."""
    vpc_ids = kwargs.get('vpc_ids', list())
    vpc_names = kwargs.get('vpc_names', list())
    vpcs = list()

    if type(vpc_ids) == str: vpc_ids = [vpc_ids]
    if type(vpc_names) == str: vpc_names = [vpc_names]

    for vpc_name in vpc_names:
        n_list = vpc_name.split('-')
        if len(n_list) != 4:
            raise NameError, 'Invalid VPC name: ' + vpc_name
        (reg, env) = ('-'.join(n_list[:3]), n_list[3])
        res = Region(name=reg).find_vpcs(env=env)
        for v in res:
            if not v in vpcs: vpcs.append(v)

    for vpc_id in vpc_ids:
        for region in get_regions():
            res = region.find_vpcs(id=vpc_id)
            if res:
                for v in res:
                    if not v in vpcs: vpcs.append(v)
                break

    return vpcs


def get_regions():
    """Returns a list of Region objects for all non-blacklisted regions."""
    regions = boto.vpc.get_regions('ec2', region_cls=Region, connection_cls=boto.vpc.VPCConnection)
    for r in regions[:]:
        if r.name in Config.blacklists['region']: regions.remove(r)
    return regions

