#!/usr/bin/env python3

# Detailed vulnerability report script
# Runs against a customizable IP address range or 0.0.0.0
# Output is in HTML format
# v0.1
# Andrew Magnusson

from pymongo import MongoClient
import datetime, sys, ipaddress
from yattag import Doc, indent

# globals
# Mongo connection parameters
client = MongoClient('mongodb://localhost:27017')
db = client['vulnmgt']
cvedb = client['cvedb']

# Output filename
outputFile = "detailed-vuln-report.html"

def main():
 # check if there's a network. If not, use 0.0.0.0
    if len(sys.argv) > 1:
        network = sys.argv[1]
    else:
        network = '0.0.0.0/0'
    networkObj = ipaddress.ip_network(network)

# initialize the host to CVE map object
    hostCveMap = {}
# get list of assets with OIDs associated
    hostList = db.hosts.find({'oids': {'$exists' : 'true'}})
# for each asset...
    for host in hostList:
# make string of vulns found, resolving them into CVE IDs (if they exist, otherwise NOCVE)
        ip = host['ip']
        # check if it's in our range
        if ipaddress.ip_address(ip) not in networkObj:
            continue
        for oidItem in host['oids']:
            cveList = db.vulnerabilities.find_one({'oid': oidItem['oid']})['cve']
# because this is a list of one or more items:
            for cve in cveList:

# skip the NOCVE type, since it's not really useful to us
                if cve == "NOCVE":
                    continue

# if there are already IPs mapped to this vulnerability
                if cve in hostCveMap.keys():
# ignore duplicates
                    if ip not in hostCveMap[cve]:
                        hostCveMap[cve].append(ip)
# if there aren't any IPs yet, create a new list with this as the first item
                else:
                    hostCveMap[cve] = [ ip ]

# start the output doc
    doc, tag, text, line = Doc().ttl()

    with tag('html'):
        with tag('head'):
            line('title', 'Vulnerability report for ' + network)
        with tag('body'):
            line('h1', 'Vulnerability report for ' + network)

# now, for each CVE (sorted) that we've found...
            for cve in sorted(hostCveMap.keys()):

        # look up CVE details in cve-search database
                cvedetails = cvedb.cves.find_one({'id': cve})

        # get affected host information into a list
                affectedHosts = len(hostCveMap[cve])
                listOfHosts = hostCveMap[cve]

        # assemble into HTML
                line('h2', cve)
                line('b', 'Affected hosts: ')
                text(affectedHosts)
                doc.stag('br')
                if (cvedetails): # if it's not empty!
                    with tag('table'):
                        with tag('tr'):
                            line('td', 'Summary')
                            line('td', cvedetails['summary'])
                        with tag('tr'):
                            line('td', 'CWE')
                            with tag('td'):

                                id = 'Unknown'
                                if cvedetails['cwe'] != 'Unknown':
                                    id=cvedetails['cwe'].split('-')[1]

                                with tag('a', href="https://cwe.mitre.org/data/definitions/"+id):
                                    text(cvedetails['cwe'])
                                cweDetails = cvedb.cwe.find_one({'id': id})
                                if cweDetails:
                                    text(" (" + cweDetails['name'] + ")")
                                else:
                                    text(" (no title)")
                        with tag('tr'):
                            line('td', 'Published')
                            line('td', cvedetails['Published'].strftime("%Y-%m-%d"))
                        with tag('tr'):
                            line('td', 'Modified')
                            line('td', cvedetails['Modified'].strftime("%Y-%m-%d"))
                        with tag('tr'):
                            line('td', 'CVSS')
                            line('td', cvedetails['cvss'] or 'Unknown')
                        with tag('tr'):
                            with tag('td'):
                                line('b', 'Impacts')
                        if 'impact' in cvedetails:
                            with tag('tr'):
                                line('td', "Confidentiality")
                                
                                line('td', cvedetails['impact']['confidentiality'])
                            with tag('tr'):
                                line('td', "Integrity")
                                line('td', cvedetails['impact']['integrity'])
                            with tag('tr'):
                                line('td', "Availability")
                                line('td', cvedetails['impact']['availability'])
                        with tag('tr'):
                            with tag('td'):
                                line('b', 'Access')
                        if 'access' in cvedetails:
                            
                            with tag('tr'):
                                line('td', "Vector")
                                line('td', cvedetails['access']['vector'])
                            with tag('tr'):
                                line('td', "Complexity")
                                line('td', cvedetails['access']['complexity'])
                            with tag('tr'):
                                line('td', "Authentication")
                                line('td', cvedetails['access']['authentication'])
                        with tag('tr'):
                            with tag('td'):
                                line('b', "References")
                        for reference in cvedetails['references']:
                            with tag('tr'):
                                with tag('td'):
                                    with tag('a', href=reference):
                                        text(reference)

                else: # if it's empty
                    line('i', "Details unknown -- update your CVE database")
                    doc.stag('br')

                line('b', "Affected hosts:")
                doc.stag('br')
                for host in sorted(listOfHosts):
                    text(host)
                    doc.stag('br')

# output final HTML
    with open(outputFile, 'w') as htmlOut:
        htmlOut.write(indent(doc.getvalue()))
        htmlOut.close()

main()
