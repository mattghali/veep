import boto.ec2, boto.vpc, netaddr, os, random, time
import Config
from tier import Tier

random.seed()

class Vpc(boto.vpc.vpc.VPC):
    """Container for VPC configuration and convenience methods."""
    def __init__(self, connection=None):
        super(Vpc, self).__init__(connection)
    
    def __eq__(self, obj):
        if type(obj) == Vpc:
            return (self.id, self.cidr_block) == (obj.id, obj.cidr_block)
        elif type(obj) == str:
            if obj.split('-')[0] == 'vpc':
                return self.id == obj
            elif obj.split('-')[-1] == self.get_env():
                return self.get_name() == obj
        elif type(obj) == netaddr.IPNetwork:
            return self.cidr_block == obj
        return False

    def __ne__(self, obj):
        return not self == obj

    def get_name(self):
        return self.tags.get('Name', False)

    def set_name(self, data):
        self.v.add_tag('Name', data)

    def get_env(self):
        return self.tags.get('Environment', False)

    def set_env(self, data):
        self.v.add_tag('Environment', data)

    def get_cidr(self):
        return netaddr.IPNetwork(self.cidr_block)

    def _wait(self, vpc):
        try:
            while vpc.update() != 'available':
                time.sleep(1)
        except self.connection.ResponseError as e:
            self._wait(vpc)

    def wait(self, obj):
        try:
            while obj.state != 'available':
                time.sleep(1)
        except self.connection.ResponseError as e:
            self.wait(obj)

    def encode_tag(self, values):
        """Encode a list of (key,value) tuples into a format suitable for a tag value"""
        tag_set = []
        for pair in values:
            (k, v) = pair
            tag_set.append("%s:%s" % (k, v))
        return ';'.join(tag_set)

    def decode_tag(self, tag):
        """Decode a tag value into a list of (key,value) tuples"""
        tag_set = []
        values = tag.split(';')
        for item in values:
            if item is not '':
                pair = tuple(item.split(':'))
                tag_set.append(pair)
        return tag_set

    def add_tier_tag(self, tier):
        tiers = self.get_tiers()
        tiers.append(tier)
        tag = self.encode_tag([ (t.name, t.cidr_block) for t in tiers ])
        self.add_tag('Tiers', tag)

    def del_tier_tag(self, tier):
        tiers = self.get_tiers()
        tiers.remove(tier)
        tag = self.encode_tag([ (t.name, t.cidr_block) for t in tiers ])
        self.add_tag('Tiers', tag)

    def get_tiers(self, name=False):
        tiertag = self.tags.get('Tiers', '')
        tiers = []

        for t in self.decode_tag(tiertag):
            (t_name, cidr_block) = t
            tier = Tier(name=t_name, cidr_block=netaddr.IPNetwork(cidr_block),
                        connection=self.connection, vpc_id=self.id)
            tiers.append(tier)

        if name:
            for t in tiers:
                if t.name == name:
                    return t
        else:
            return tiers

    def add_tier(self, tier_name, cidr_block, subnet_size=21):
        tier = Tier(name=tier_name, cidr_block=cidr_block, connection=self.connection, vpc_id=self.id)
        tier.build([z.name for z in self.region.get_zones()], subnet_size)
        self.add_tier_tag(tier)
        return tier

    def delete_tier(self, tier):
        tier.delete()
        self.del_tier_tag(tier)
        return True

    def rename_tier(self, old, new):
        tier = self.get_tiers(name=old)
        self.del_tier_tag(tier)
        tier.rename(new)
        self.add_tier_tag(tier)
        return tier

    def sg_rule(self, **kwargs):
        r = dict()
        r['ip_protocol'] = kwargs.get('ip_protocol', None)
        r['from_port'] = kwargs.get('from_port', None)
        r['to_port'] = kwargs.get('to_port', None)
        r['grants'] = kwargs.get('grants', [])
        r['src_group'] = kwargs.get('src_group', None)

        if type(r['src_group']) == str:
            r['src_group'] = self.get_secgrps(ids=r['src_group'])[0]

        rule = boto.ec2.securitygroup.IPPermissions()
        rule.__dict__.update(r)
        return rule


    def get_secgrps(self, **kwargs):
        """Returns a list of sec grp objects by region, selected by name, id"""
        names = kwargs.get('names', [])
        ids = kwargs.get('ids', [])
        filters = kwargs.get('filters', {})
        filters.update({'vpc_id': self.id})
        groups = self.connection.get_all_security_groups(group_ids=ids, filters=filters)
        if names:
            groups = [ g for g in groups if g.name in names ]
        return groups

    def create_secgrp(self, **kwargs):
        """Create a security group associated with this VPC"""
        name = kwargs.get('name', None)
        description = kwargs.get('description', None)
        rules = kwargs.get('rules', [])
        if name:
            group = self.connection.create_security_group(name, description, vpc_id=self.id)
            for rule in rules:
                for grant in rule.grants:
                    group.authorize(ip_protocol=rule.ip_protocol, from_port=rule.from_port,
                        to_port=rule.to_port, cidr_ip=grant, src_group=rule.src_group)
            return group

    def update_secgrp(self, **kwargs):
        """Update a security group associated with this VPC"""
        id = kwargs.get('id', None)
        group = kwargs.get('group', None)
        authorize = kwargs.get('authorize', [])
        revoke = kwargs.get('revoke', [])
        filters = {'vpc_id': self.id}

        if id:
            groups = self.connection.get_all_security_groups(group_ids=[id], filters=filters)
            group = groups[0] if groups else None

        for rule in authorize:
            # rule 'grants' are a list of boto.ec2.securitygroup.GroupOrCIDR. From what
            # I can tell, its either a single member list of an object with a group_id attr,
            # or a list of one or more objs with a cidr_ip attr.

            if rule.grants[0].group_id:
                # grant by group id
                for grant in rule.grants:
                    self.connection.authorize_security_group(group_id=group.id, 
                        ip_protocol=rule.ip_protocol, from_port=rule.from_port,
                        to_port=rule.to_port, src_security_group_group_id=grant.group_id)
            else:
                # grant by cidr_ip
                for grant in rule.grants:
                    self.connection.authorize_security_group(group_id=group.id, 
                        ip_protocol=rule.ip_protocol, from_port=rule.from_port,
                        to_port=rule.to_port, cidr_ip=grant.cidr_ip)

        for rule in revoke:
            if rule.grants[0].group_id:
                # grant by group id
                for grant in rule.grants:
                    self.connection.revoke_security_group(group_id=group.id, 
                        ip_protocol=rule.ip_protocol, from_port=rule.from_port,
                        to_port=rule.to_port, src_security_group_group_id=grant.group_id)
            else:
                # grant by cidr_ip
                for grant in rule.grants:
                    self.connection.revoke_security_group(group_id=group.id, 
                        ip_protocol=rule.ip_protocol, from_port=rule.from_port,
                        to_port=rule.to_port, cidr_ip=grant.cidr_ip)

        return group

    def delete_secgrp(self, **kwargs):
        """Delete a security group associated with this VPC"""
        id = kwargs.get('id', None)
        if id:
            self.connection.delete_security_group(group_id=id)
            return True

    def get_tables(self, **kwargs):
        name = kwargs.get('name', None)
        tables = self.connection.get_all_route_tables(filters=[('vpc_id', self.id)])

        if name:
            for t in tables:
                if t.tags.get('Name') == name:
                    return t
        else:
            return tables

    def create_table(self, **kwargs):
        name = kwargs.get('name', None)

        if name:
            table = self.connection.create_route_table(self.id)
            table.add_tag('Name', name)
            return table

    def delete_table(self, table=None, **kwargs):
        name = kwargs.get('name', None)
        id = kwargs.get('id', None)

        if name:
            table = self.get_tables(name=name)
        if table:
            id = table.id
        if id:
            self.connection.delete_route_table(id)

    def get_igw(self):
        igws = self.connection.get_all_internet_gateways(filters={'attachment.vpc-id': self.id})
        if len(igws) > 0:
            return igws[0]
        else:
            return None

    def add_igw(self):
        if not self.get_igw():
            igw = self.connection.create_internet_gateway()
            self.connection.attach_internet_gateway(igw.id, self.id)
            igw.add_tag('Name', self.get_name())
            return igw
        return False

    def run_instances(self, **kwargs):
        image_id = kwargs.setdefault('image_id', None)
        root_type = kwargs.setdefault('root_type', 'ebs')
        min_count = kwargs.setdefault('min_count', 1)
        max_count = kwargs.setdefault('max_count', 1)
        key_name = kwargs.setdefault('key_name', self.get_name())
        user_data = kwargs.setdefault('user_data', Config.userdata)
        instance_type = kwargs.setdefault('instance_type', 't2.micro')
        monitoring_enabled = kwargs.setdefault('monitoring_enabled', True)
        subnet_id = kwargs.setdefault('subnet_id', None)
        tier = kwargs.setdefault('tier', None)
        security_group_names = kwargs.setdefault('security_group_names', ['SSH'])
        security_group_ids = kwargs.setdefault('security_group_ids', [])
        instance_profile = kwargs.setdefault('instance_profile', None)
        instance_profile_name = kwargs.setdefault('instance_profile_name', None)
        instance_profile_arn = kwargs.setdefault('instance_profile_arn', None)
        ebs_optimized = kwargs.setdefault('ebs_optimized', False)
        tags = kwargs.setdefault('tags', {})
        dry_run = kwargs.setdefault('dry_run', False)

        # Pick an image ID
        if not image_id:
            images = self.region.get_images(root_type=root_type)
            if len(images) > 0:
                kwargs['image_id'] = images[-1].id # get latest image
        kwargs.pop('root_type')

        # use subnet_id if set, otherwise use tier, otherwise default to backend
        if not subnet_id:
            if not tier:
                tier = self.get_tiers(name='backend')
            kwargs['subnet_id'] = random.choice(list(tier.subnets)).id
        kwargs.pop('tier')

        # Security group selection
        if not security_group_ids:
            for s in self.get_secgrps(names=security_group_names):
                kwargs['security_group_ids'].append(s.id)
        kwargs.pop('security_group_names')

        # Set default tags, if unset.
        tags.setdefault('Type', 'Generic')
        tags.setdefault('Env', self.get_env())
        tags.setdefault('Owner', os.getlogin())
        tags.setdefault('Name', "%s-%s" % (tags['Owner'], tags['Type']))
        kwargs.pop('tags')

        # Select instance profile - if by name or arn, get Profile obj
        if instance_profile:
            kwargs['instance_profile_name'] = instance_profile.name
            kwargs['instance_profile_arn'] = instance_profile.arn
        else:
            if not instance_profile_name and not instance_profile_arn:
                # Hope there's a matching profile for the type tag.
                kwargs['instance_profile_name'] = "%s%s-%s" % (tags['Type'], 'Instance', self.get_env())
        kwargs.pop('instance_profile')

        # run the instance.
        reservation = self.region.ec2conn.run_instances(**kwargs)

        # Add tags
        for instance in reservation.instances:
            instance.add_tags(tags)

        return reservation

