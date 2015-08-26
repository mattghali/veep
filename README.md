# veep
Automation for AWS VPC management, built on top of boto.

At its core, veep contains a set of objects subclassing familiar boto objects, adding convenience methods. It also contains a set of helper functions written to make common AWS operations more convenient. Most of the library is built around managing multiple VPCs across multiple regions as painless as possible, reducing the opportunity for config drift across vpcs and regions.

You can find documentation and usage examples at [veep.snark.net](http://veep.snark.net).

