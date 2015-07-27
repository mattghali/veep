import netaddr

class Tier(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', None)
        cidr_block = kwargs.get('cidr_block', None)
        if type(cidr_block) == netaddr.IPNetwork:
            self.cidr_block = cidr_block
        else:
            self.cidr_block = netaddr.IPNetwork(cidr_block)
        self.subnets = set()

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

    def add_subnet(self, subnet):
        self.subnets.add(subnet)

    def del_subnet(self, subnet):
        self.subnets.remove(subnet)

