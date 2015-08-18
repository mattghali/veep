# veep
Automation for AWS VPC management, built on top of boto.

At its core, veep contains a set of objects subclassing familiar boto objects, adding convenience methods. It also contains a set of helper functions written to make common AWS operations more convenient. Most of the library is built around managing multiple VPCs across multiple regions as painless as possible, reducing the opportunity for config drift across vpcs and regions. Inside VPC you will find a hierarchy of objects and associated methods:
* Region
* VPC
* Tier

Region and VPC objects should be instantly familiar to anyone who uses boto. The Tier object is a veep abstraction not shared with boto. Tiers allow easy mapping of a set of access policies across all availability zones in a VPC.

Instances can be broken down into a small number of groups with specific access policy requirements. For instance, in a typical web app architecture, you might have a set of web servers which require direct inbound access from clients on the internet. Behind this set of web servers, another set of app servers need no direct inbound connectivity, but must talk to external services for things like boot-time patching. Commonly these app servers would sit behind NAT instead of an AWS Internet Gateway. Other things might need no external connectivity at all, like VPC Service Endpoints. Or you may want a small set of admin instances as bastion hosts between the rest of your VPC and a VPN tunnel. Tiers are an abstraction of this mapping between policies implemented via Route Tables and the set of AZs in a VPC's region.

```
# Create a new 'prod' environment VPC in us-west-2
region = veep.VPC.Region('us-west-2')
vpc = region.create_vpc(env='prod', cidr_block='10.0.0.0/16')

# Add a tier allocated from the first /18 of the VPC's ip space.
# Subnets in the tier will be consecutive /22 blocks from that /18.
tier = vpc.add_tier('frontend', list(vpc.get_cidr().subnet(18))[0], subnet_size=22)

# create_vpc() initalized a route table
table = vpc.get_tables(name='Public')

# Associate route table with Tier subnets
tier.associate_table(table)

# Et voila, you have a subnet for each AZ, associated with your route table:
>>> for s in tier.subnets:
...     print s.tags.get('Name'), s.cidr_block
... 
frontend-us-west-2b 10.0.4.0/22
frontend-us-west-2c 10.0.8.0/22
frontend-us-west-2a 10.0.0.0/22
```
To see Tiers in action check out examples/build_vpcs

There is also a Config class which contains common configuration for your organization. This class imports LocalConfig, which tries to isolate attributes likely to be similar for most library users from attributes which will definitely change per user. Likely there is a better long-term solution for this config data, like home directory .ini files.
