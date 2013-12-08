import socket
import select
import time
import math
import sys
from xml.etree import ElementTree

import requests

# i ran this code in EC2 in the IAD data center.
our_lat = 38.94
our_long = -77.45

def distance(lat1, long1, lat2, long2):
    d2r = math.pi / 180.0
    lat1 = (90 - lat1) * d2r
    lat2 = (90 - lat2) * d2r

    long1 = long1 * d2r
    long2 = long2 * d2r

    cos = (math.sin(lat1) * math.sin(lat2) * math.cos(long1 - long2) + math.cos(lat1) * math.cos(lat2))
    arc = math.acos(cos)
    radius_of_earth = 3956.6 # in miles!
    return arc * radius_of_earth

def traceroute(dest_name):
    # highly unlikely port
    PORT=12342
    # might as well send something!
    DATA_TO_SEND="abcdefgh"
    ttl = 4
    lowest_ttl_fail = None
    highest_ttl_succeed = None
    dest_ip = socket.gethostbyname(dest_name)
    success_time = -1

    while (lowest_ttl_fail or 0) != (highest_ttl_succeed or 100000000) - 1:
        print 'trying with ttl %i' % ttl
        # create an icmp recv and a udp send
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname('icmp'))
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.getprotobyname('udp'))
        try:
            # set ttl to tll
            send_sock.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
        except:
            # return error flag values
            return -1, -1, -1

        recv_sock.bind(("0.0.0.0", PORT))
        t0 = time.time()
        send_sock.sendto(DATA_TO_SEND, (dest_name, PORT))

        recv_sock.setblocking(0)

        # check if the socket is readable?
        ready = select.select([recv_sock], [], [], 5) # check if recvd in 5 seconds
        last_time = time.time() - t0
        try:
            if ready[0]:
                # if it's readable, check the icmp code
                data, address = recv_sock.recvfrom(4096)
                address = address[0] # we don't care about the port
                databytes = map(ord, data) # we get the byte values
                icmp_code = databytes[20]
                if icmp_code == 11: # ttl exceeded
                    print 'failed to reach with ttl %i' % ttl
                    lowest_ttl_fail = ttl
                    if highest_ttl_succeed:
                        ttl += (highest_ttl_succeed - ttl) / 2
                    else:
                        ttl = ttl * 2
                elif icmp_code == 3: # port unreachable
                    print 'reached with ttl %i' % ttl
                    highest_ttl_succeed = ttl
                    success_time = last_time
                    ttl -= (ttl - (lowest_ttl_fail or 0)) / 2
            else:
                print 'no response with ttl %i' % ttl
                lowest_ttl_fail = ttl
                if highest_ttl_succeed:
                    ttl += (highest_ttl_succeed - ttl) / 2
                else:
                    ttl = ttl * 2
        except Exception as e:
            print e
        finally:
            send_sock.close()
            recv_sock.close()

    # this is ludicrously inaccurate, but hey, it's in the spec.
    resp = requests.get("http://freegeoip.net/xml/" + dest_ip)
    root = ElementTree.fromstring(resp.content)
    for child in root:
        if child.tag == "Latitude":
            lat1 = float(child.text)
        if child.tag == "Longitude":
            long1 = float(child.text)
    return highest_ttl_succeed, success_time, distance(lat1, long1, our_lat, our_long)

def do_all():
    all_outputs = []
    for hostname in ['nmckinley.com', 'netflix.com', 'twitter.com', 'python.org', 'xkcd.com', 'oracle.com', 'pandora.com', 'naukri.com', 'exoclick.com', 'slickdeals.net']:
        args = [hostname]
        args.extend(traceroute(hostname))
        all_outputs.append("%s: Reached in %i hops in %f seconds, it's %f miles away." % tuple(args))
    print '\n'.join(all_outputs)

if __name__ == '__main__':
    do_all()
