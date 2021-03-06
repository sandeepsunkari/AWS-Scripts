#!/usr/bin/python

import urllib
import boto
import tempfile
import os
from optparse import OptionParser

EC2_CONN = boto.connect_ec2()
PUBLIC_IP_TEMP_FILE = os.path.join(tempfile.gettempdir(),"public_ip_address")

def get_arg_parser():
    parser = OptionParser()
    parser.add_option("-g","--group", dest="group",
        help="Required security group that port modifications will be made on.")
    parser.add_option("-p","--port", dest="ports", action="append",
        help="Required port number to be opened for the current public IP.  " + 
            "All other group allowances specify this port will be removed." +
            "This option can be specified multiple times.")
    return parser

def get_public_facing_ip():
    public_ip = urllib.urlopen("http://ip.jasonwhaley.com").read()
    with open(PUBLIC_IP_TEMP_FILE,"w") as f:
        f.write(public_ip)
    return public_ip

        
def read_ip_from_temp_file():
    if os.path.exists(PUBLIC_IP_TEMP_FILE):
        with open(PUBLIC_IP_TEMP_FILE) as f:
            return f.readlines()[0].strip()
        

def remove_all_rules_for_port(group,port):
    for rule in group.rules:
        if int(rule.from_port) == int(port) and int(rule.to_port) == int(port):
            for grant in rule.grants:
                EC2_CONN.revoke_security_group(group_name = group.name,
                                               ip_protocol="tcp",
                                               from_port = int(port),
                                               to_port = int(port),
                                               cidr_ip = grant)

def add_rule_for_port_and_pub_ip(group, ip, port):
    if "/" not in ip:
        cidr_ip = ip + "/32"
    else:
        cidr_ip = ip
    EC2_CONN.authorize_security_group(group_name = group.name, 
                                      ip_protocol="tcp",
                                      from_port=int(port),
                                      to_port=int(port),
                                      cidr_ip=cidr_ip)

if __name__ == "__main__":
    parser = get_arg_parser()
    (options,args) = parser.parse_args()
    if options.group == None or options.ports == None or len(options.ports) == 0:
        parser.print_help()
        exit(-1)

    ip = get_public_facing_ip()
    if ip != read_ip_from_temp_file:
        groups = [group for group in EC2_CONN.get_all_security_groups() 
            if options.group == group.name]
        
        for group in groups:
            for port in options.ports:
                remove_all_rules_for_port(group,port)
                add_rule_for_port_and_pub_ip(group,ip,port)
                print("Port %s opened for %s in group %s" % (port,ip,group.name))
