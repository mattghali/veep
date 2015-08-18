import netaddr, time

class Tier(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', None)
        cidr_block = kwargs.get('cidr_block', None)
        self.connection = kwargs.get('connection', None)
        self.vpc_id = kwargs.get('vpc_id', None)
        if type(cidr_block) == netaddr.IPNetwork:
            self.cidr_block = cidr_block
        else:
            self.cidr_block = netaddr.IPNetwork(cidr_block)
        self.subnets = set()

        subnets = self.connection.get_all_subnets(filters=[('vpcId', self.vpc_id)])
        for subnet in subnets:
            cidr = netaddr.IPNetwork(subnet.cidr_block)
            if cidr in self.cidr_block:
                self.subnets.add(subnet)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

    def __eq__(self, obj):
        if type(obj) == Tier:
            if (self.name, self.cidr_block) == (obj.name, obj.cidr_block):
                return set([s.id for s in self.subnets]) == set([o.id for o in obj.subnets])
        elif type(obj) == str:
            return self.name == obj
        elif type(obj) == netaddr.IPNetwork:
            return self.cidr_block == obj
        return False

    def __ne__(self, obj):
        return not self == obj

    def build(self, zone_list, subnet_size):
        tier_subnets = list(self.cidr_block.subnet(subnet_size))
        for zone in zone_list:
            sub_name = self.name + '-' + zone
            self.add_subnet(zone, tier_subnets[zone_list.index(zone)])

    def rename(self, new_name):
        self.name = new_name
        for subnet in self.subnets:
            subnet.add_tag('Name', self.name + '-' + subnet.availability_zone)
            subnet.add_tag('Tier', self.name)

    def add_subnet(self, zone, cidr_block):
        subnet = self.connection.create_subnet(self.vpc_id, str(cidr_block), availability_zone=zone)
        # subnet isnt avail immediately, state never updates
        time.sleep(2)
        while subnet.state == 'pending':
            subnets = self.connection.get_all_subnets(filters={'vpcId': self.vpc_id})
            for i in subnets:
                if i.id == subnet.id:
                    subnet.state = i.state
            time.sleep(1)
        subnet.add_tag('Name', self.name + '-' + zone)
        subnet.add_tag('Tier', self.name)
        self.subnets.add(subnet)
        return subnet

    def del_subnet(self, subnet):
        self.connection.delete_subnet(subnet.id)
        self.subnets.remove(subnet)

    def delete(self):
        for subnet in self.subnets.copy():
            self.del_subnet(subnet)

    def associate_table(self, table):
        for subnet in self.subnets:
            subnet.connection.associate_route_table(table.id, subnet.id)

