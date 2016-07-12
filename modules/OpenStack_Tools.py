
from openstack import connection
from openstack import profile
from openstack import utils
from openstackclient.common import clientmanager
import sys, os
import os_client_config
import traceback

#from Monitoring_Tools import DictTable, ListTable, highlights, ok_highlight, warn_highlight, error_highlight
#from Monitoring_Tools import DictTable, ListTable, highlights, html_ping_endpoint_urls
from Monitoring_Tools import *
from IPython.core.display import display,HTML

if os.getenv('VERBOSE', '0') == '0':
    VERBOSE = False
else:
    VERBOSE = True


'''
Read connection information for specified cloud from clouds.yaml file
'''

utils.enable_logging(False, stream=sys.stdout)

def connectToCloud(cloudName):
    occ = os_client_config.OpenStackConfig()

    cloud = occ.get_one_cloud(cloudName)

    return connection.from_config(cloud_config=cloud)

def getServerFields(server, fields, flavor_names, image_names):
    
    values=[]
    for field in fields:
        if field == 'name' or field == 'status':
            values.append( server[field] )
        elif field == 'addresses':
#{'Net-External': [{'version': 4, 'addr': '10.3.48.10', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:46:78:ca', 'index': 2}], 'net2440': [{'version': 4, 'addr': '10.24.40.162', 'OS-EXT-IPS:type': 'fixed', 'OS-EXT-IPS-MAC:mac_addr': 'fa:16:3e:62:0d:ee', 'index': 1}]}
            text = ''
            for key in server[field].keys():
                text += '<u>' + key + '</u><br/>' 
                network = server[field][key][0]
                text += network['addr'] + '<br/>'
            values.append( text )
        elif field == 'flavor':
            if 'id' in server[field]:
                fieldid = server[field]['id']
                value = flavor_names[ fieldid ]
            else:
                fieldid = "None"
                value = "None"
            values.append( "<u>{}</u><br/>[{}]".format(value, fieldid) )
        elif field == 'image':
            if 'id' in server[field]:
                fieldid = server[field]['id']
                value = image_names[ fieldid ]
            else:
                fieldid = "None"
                value = "None"
            values.append( "<u>{}</u><br/>[{}]".format(value, fieldid) )
        elif field in server:
            values.append( server[field] )
        else:
            values.append("")
                                       
    return values
    #s_list=[ s['name'], s['status'], flavor_names[ s['flavor']['id'] ], image_names[ s['image']['id'] ], s['addresses']]

class flushfile():
    oldstderr=None
    def __init__(self, f):
        self.f = f
    def __getattr__(self,name): 
        return object.__getattribute__(self.f, name)
    def write(self, x):
        self.f.write(x)
        self.f.flush()
    def flush(self):
        self.f.flush()
    def save_stderr():
        flushfile.oldstderr = sys.stderr
        sys.stderr = open('openstack_errorlog.txt', 'a')
        sys.stderr = flushfile(sys.stderr)
        #from __future__ import print_function
    def restore_stderr():
        sys.stderr = flushfile.oldstderr
        
def showServerList(conn, showFlavors=False, showImages=False):
    html = getServerList(conn, showFlavors, showImages)
    display( HTML(html) )

def getServerList(conn, showFlavors=False, showImages=False):
    servers_list=[]
    flavor_names={}
    image_names={}

    flushfile.save_stderr()

    try:
        flavors = conn.compute.flavors()
        print("{} flavors".format(sum(1 for i in flavors)))
        flavors = conn.compute.flavors()
        for f in flavors:
            #print("FLAVOR: " + f['name'])
            flavor_names[f['id']]=f['name']

        if showFlavors:
            html = DictTable._repr_html_(flavor_names, highlights=None)
            #print(html)
            display( HTML(html) )
    except Exception as e:
        print("Failed to determine number of flavors")

    try:
        images = conn.compute.images()
        print("{} images".format(sum(1 for i in images)))
        images = conn.compute.images()
        for i in images:
            #print("IMAGE: " + i['name'])
            image_names[i['id']]=i['name']

        if showImages:
            html = DictTable._repr_html_(image_names, highlights=None)
            #print(html)
            display( HTML(html) )
    except Exception as e:
        print("Failed to determine number of images")

    try:
        headers=['name','status','flavor','image','addresses']
        servers_list = [ [ '<center><b>'+h+'</b></center>' for h in headers ] ]
        servers = conn.compute.servers()
        print("{} servers".format(sum(1 for i in servers)))
        #print(highlights)
    except Exception as e:
        print("Failed to determine number of servers: " + str(e))

    try:
        servers = conn.compute.servers()
        for s in servers:
            #print("SERVER=" + str(s))

            s_list = getServerFields(s, headers, flavor_names, image_names)
            #print("SERVER fields=" + str(s_list))

            servers_list += [ s_list ]
    except Exception as e:
        print("Failed to enumerate servers: " + str(e))
        traceback.print_exc(file=sys.stdout)

    html = ListTable._repr_html_(servers_list, highlights)

    flushfile.restore_stderr()

    return html, "OK"

def html_endpoint_urls(conn):
    from openstack import profile as _profile
    from openstack import exceptions as _exceptions

    prof = _profile.Profile()
    services = [service.service_type for service in prof.get_services()]
    #print(services)

    #service_list=['compute', 'clustering', 'orchestration', 'database', 'network', 'volume', 'messaging', 'identity',
    #              'metering', 'object-store', 'key-manager', 'image']
    #service_list=['compute', 'orchestration', 'network', 'volume', 'identity', 'metering', 'object-store', 'image']
    service_list=['compute', 'network', 'volume', 'identity', 'image']

    endpoint_urls={}
    for service in services:
        if service in service_list:
            #print("SERVICE:" + service)
            try:
                url=conn.authenticator.get_endpoint(conn.session, service_type=service, interface='public')
                endpoint_urls[service]=url
            #except _exceptions.EndpointNotFound:
            #    pass
            except Exception as e:
                #raise
                print("Failed to determine {} service endpoint url".format(service))

    return html_ping_endpoint_urls(endpoint_urls)

def display_html_endpoint_urls(conn):
    html, status = html_endpoint_urls(conn)
    display( HTML(html) )
    return status

def platformStatus(platform):
    HTML_OP=''
    
    show_notebook_url(platform, host_ip="10.3.216.210", port=8888)
    HTML_OP += '<b>' + html_platform_info(platform, '<a href="#RESULTS_STATUS"> Return to Top (RESULTS_STATUS) </a>')+ '</b>'
    
    ini_file="$HOME/env/{}_hosts.ini".format(platform)
    if VERBOSE:
        print("Reading " + ini_file)

    inventory = read_inventory(ini_file)
    
    if VERBOSE:
        print("Connecting to cloud: " + platform)
    conn = connectToCloud(platform)
    
    if VERBOSE:
        print("Pinging ...")
    HTML, PING_STATUS = html_ping_all(inventory)
    HTML_OP += HTML
    
    if VERBOSE:
        print("Get server/flavor/image list ...")
    HTML, VMS_STATUS = getServerList( conn )
    HTML_OP += HTML
    
    if VERBOSE:
        print("Pinging ports ...")
    HTML, PING_PORTS_STATUS = html_ping_ports_all(inventory)
    HTML_OP += HTML
    
    if VERBOSE:
        print("Pinging endpoints ...")
    HTML, ENDPOINTS_STATUS = html_endpoint_urls(conn)
    HTML_OP += HTML
    
    #archive_df(inventory)
    return HTML_OP, PING_STATUS, VMS_STATUS, PING_PORTS_STATUS, ENDPOINTS_STATUS


