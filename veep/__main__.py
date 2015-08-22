import veep

# This is where I'll invoke automated testing for veep.
for region in veep.VPC.get_regions():
    print region.name, region.get_geoname()
