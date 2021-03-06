#!/usr/bin/python

import boto
import time
import sys
import argparse
import itertools
from datetime import datetime

MAX_STATUS_CHECKS = 20

def generate_image_name(base_name="",instance=None):
    if base_name is None or base_name.strip() == "":
        if "Name" in instance.tags:
            base_name = instance.tags["Name"]
        else:
            base_name = instance.id

    now = datetime.now()
    return base_name + "-" + str(now.year) + "." + str(now.month).zfill(2) \
        + "." + str(now.day).zfill(2) + "." + str(now.hour).zfill(2) \
        + str(now.minute).zfill(2)

parser = argparse.ArgumentParser(description='ec2-backup-instance')
parser.add_argument("--id","--instance_id", dest="id",required="true", 
    help="An instance id must be supplied")
parser.add_argument("--name","--base_name", dest="base_name",
    help="Base name prepended to a timestamp to forming the name of the AMI")
arguments = parser.parse_args()


ec2 = boto.connect_ec2()
chain = itertools.chain.from_iterable
existing_instances = list(
    chain([res.instances for res in ec2.get_all_instances()]))

if unicode(arguments.id) not in \
[instance.id for instance in existing_instances]:
    print "Error: backup not taken.  " + \
        "Supplied instance id must represent an existing instance."
    sys.exit()
else:
    target_instance = [instance for instance in existing_instances
        if instance.id == arguments.id][0]

image_name = generate_image_name(arguments.base_name,target_instance)

ami_id = ec2.create_image(
    instance_id=target_instance.id, name=image_name, no_reboot=True)
print "Started AMI creation of:  " + str(ami_id) + " with name of " + image_name

#Loop until state is 'available' or until threshold has elapsed
iterations = 0
while True:
    iterations = iterations + 1
    time.sleep(60)
    image = ec2.get_image(ami_id)
    if image.state == "available":
        message = "Backup succeeded for " + target_instance.id
        break
    elif image.state == "pending" and iterations <= MAX_STATUS_CHECKS:
        continue
    else:
        message = "Backup failed for " + target_instance.id + \
            " with state of " + image.state
        break

print message
