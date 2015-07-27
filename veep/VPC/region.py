import boto.ec2, boto.ec2.autoscale, boto.ec2.elb, boto.regioninfo, boto.vpc, datetime, time
from collections import OrderedDict
import Config
from vpc import Vpc

class Region(boto.vpc.RegionInfo):
    """Container for Vpc objects. Also holds region-specific resources as attributes."""
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name', 'us-west-2')
        if args: self.name = args[0]
        self.cidr_block = kwargs.pop('cidr_block', False)
        self.vpcs = []

        kwargs['name'] = self.name
        if kwargs.get('endpoint', None) is None:
            kwargs['endpoint'] = "ec2.%s.amazonaws.com" % self.name
        if kwargs.get('self.connection_cls', None) is None:
            kwargs['connection_cls'] = boto.vpc.VPCConnection

        super(Region, self).__init__(**kwargs)

        self.conn = self.connect()
        for r in boto.ec2.regions():
            if r.name == self.name: self.ec2conn = r.connect()
        for r in boto.ec2.autoscale.regions():
            if r.name == self.name: self.asconn = r.connect()
        for r in boto.ec2.elb.regions():
            if r.name == self.name: self.elbconn = r.connect()

    def __eq__(self, obj):
        if type(obj) == Region or type(obj) == boto.regioninfo.RegionInfo:
            return self.name == obj.name
        elif type(obj) == str:
            return self.name == obj
        return False

    def __ne__(self, obj):
        return not self == obj

    def get_geoname(self):
        region_mapping = {
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-southeast-2': 'Asia Pacific (Sydney)',
            'eu-central-1': 'EU (Frankfurt)',
            'eu-west-1':    'EU (Ireland)',
            'sa-east-1':    'South America (Sao Paulo)',
            'us-east-1':    'US East (N. Virginia)',
            'us-west-1':    'US West (N. California)',
            'us-west-2':    'US West (Oregon)' }

        return region_mapping[self.name]

    def get_zones(self):
        zones = []
        zone_list = self.ec2conn.get_all_zones()
        for zone in zone_list:
            if zone.name not in Config.blacklists['az']: zones.append(zone)
        return zones

    def find_vpcs(self, **kwargs):
        """Collect a list of managed vpcs in the current region.
           Optionally select any additive combo of name, environment or id."""
        env = kwargs.get('env', None)
        name = kwargs.get('name', None)
        id = kwargs.get('id', None)
        (vpc_ids, params) = ([], {})
        for vpc in self.conn.get_all_vpcs():
            if 'Environment' in vpc.tags.keys():
                if (env and vpc.tags['Environment'] == env) \
                  or (name and vpc.tags['Name'] == name) \
                  or (id and vpc.id == id):
                    vpc_ids.append(vpc.id)
                if not env and not name and not id:
                    vpc_ids.append(vpc.id)

        if vpc_ids:
            self.conn.build_list_params(params, vpc_ids, 'VpcId')
            return self.conn.get_list('DescribeVpcs', params, [('item', Vpc)])
        else: return []

    def get_secgrps(self, **kwargs):
        """Returns a list of sec grp objects by region, selected by name, id, vpc"""
        names = kwargs.get('names', [])
        ids = kwargs.get('ids', [])
        vpcid = kwargs.get('vpcid', None)
        filters = kwargs.get('filters', {})
        if vpcid: filters.update({'vpc_id': vpcid})

        groups = self.ec2conn.get_all_security_groups(group_ids=ids, filters=filters)
        if names:
            groups = [ g for g in groups if g.name in names ]
        return groups

    def get_images(self, **kwargs):
        """Returns a list of AMIs by region, selected by name, id, vpc"""
        ids = kwargs.get('ids', [])
        owners = kwargs.get('owners', ['amazon'])
        name = kwargs.get('name', None)
        arch = kwargs.get('arch', 'x86_64')
        minimal = kwargs.get('minimal', True)
        virt_type = kwargs.get('virt_type', 'hvm')
        root_type = kwargs.get('root_type', 'instance-store') # or 'ebs'

        filters = kwargs.get('filters', {
                                        'state': 'available',
                                        'image-type': 'machine',
                                        'virtualization-type': virt_type,
                                        'architecture': arch,
                                        'root-device-type': root_type
                                        })

        images =  self.ec2conn.get_all_images(image_ids=ids, owners=owners, filters=filters)

        # filter on description
        for image in images[:]:
            if image.description is None:
                image.description = ''
            if name and name not in image.description:
                images.remove(image)
            if minimal and 'minimal' not in image.description:
                images.remove(image)

        if len(images) < 1:
            raise RuntimeWarning, "Search returned 0 images"

        # sort by date
        def dateSorter(image):
            return datetime.datetime.strptime(image.creationDate.split('.')[0], '%Y-%m-%dT%H:%M:%S')

        return sorted(images, key=dateSorter)

    def create_vpc(self, **kwargs):
        env = kwargs.get('env', False)
        region = kwargs.get('region', False)
        cidr_block = kwargs.get('cidr_block', False)
        self.debug = kwargs.get('debug', False)
        name = region.name + '-' + env

        if env is False or region is False or cidr_block is False:
            raise RuntimeError, "missing required parameters"

        v = self.conn.create_vpc(cidr_block, dry_run=self.debug)
        if not self.debug:
            self._wait(v)
            v.add_tag('Name', name)
            v.add_tag('Environment', env)
            v.add_tag('Netblock', cidr_block)
        
            igw = self.add_igw(v, name)
            tables = self.conn.get_all_route_tables(filters=[('vpc_id', v.id)])
            pub_table = tables[0]
            pub_table.add_tag('Name', 'Public')
            self.conn.create_route(pub_table.id, '0.0.0.0/0', gateway_id=igw.id)

            return self.find_vpcs(id=v.id)[0]
        return None

    def get_tables(self, vpc):
        return self.conn.get_all_route_tables(filters=[('vpc_id', vpc.id)])

    def get_igw(self, vpc):
        igws = self.conn.get_all_internet_gateways(filters={'attachment.vpc-id': vpc.id})
        if len(igws) > 0:
            return igws[0]
        else:
            return None

    def add_igw(self, vpc, name):
        if not self.get_igw(vpc):
            igw = self.conn.create_internet_gateway()
            self.conn.attach_internet_gateway(igw.id, vpc.id)
            igw.add_tag('Name', name)
            return igw
        return False

    def delete_vpc(self, vpc):
        subnets = self.conn.get_all_subnets(filters=[('vpcId', vpc.id)])
        for subnet in subnets:
            vpc.delete_subnet(subnet)
        igw = self.get_igw(vpc)
        if igw:
            self.conn.detach_internet_gateway(igw.id, vpc.id)
            self.conn.delete_internet_gateway(igw.id)
        for group in vpc.get_secgrps():
            if group.name != 'default':
                vpc.delete_secgrp(id=group.id)
        res = self.conn.delete_vpc(vpc.id)
        return res

    def _wait(self, vpc):
        try:
            while vpc.update() != 'available':
                time.sleep(1)
        except self.conn.ResponseError as e:
            self._wait(vpc)


