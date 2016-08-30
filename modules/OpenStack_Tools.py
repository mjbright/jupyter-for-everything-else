
from openstack import connection
from openstack import profile
from openstack import utils
from openstackclient.common import clientmanager
import sys, os
import os_client_config

from time import gmtime, strftime
import traceback
import signal

from Monitoring_Tools import *
from IPython.core.display import display,HTML

if os.getenv('VERBOSE', '0') == '0':
    VERBOSE = False
else:
    VERBOSE = True

def filter_stack_trace(frame, reject_filter, limit=None):
    tb_list = traceback.extract_stack(frame, limit=None)

    return_first_last_str=''

    # Get 1st non-IPython line:

    entry=0
    for tb_tpl in tb_list:
        entry=entry+1
        filename, line_number, function_name, text  = tb_tpl
        if not reject_filter in filename:
            return_first_last_str += 'File {}, line {}, in {},\n\t{}\n'.format(filename, line_number, function_name, text)
            pass;

        if limit and entry >= limit:
            break;

    ## # Get last non-IPython line:
    ## filename, line_number, function_name, text  = tb_list[-1]
    ## return_first_last_str += 'File {}, line {}, in {}, {}\n'.format(filename, line_number, function_name, text)

    return return_first_last_str

def signalHandler(signum, frame):
    tstring = strftime("%H:%M:%S", gmtime())
    print('{}: OpenStack_Tools: Signal handler called with signal'.format(tstring), signum)

    print(filter_stack_trace(frame, 'lib/python', 1))
    #print("-- 1:")
    traceback.print_stack(frame, limit=1, file=sys.stdout)
    #print("-- FULL:")
    #traceback.print_stack(frame, file=sys.stdout)
    raise TimeoutException("OpenStack - timeout")


dtstring = strftime("%Y-%m-%d %H:%M:%S", gmtime())
print("Starting at: " + dtstring)
signal.signal(signal.SIGALRM, signalHandler)


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
        
def displayServerList(conn, showFlavors=False, showImages=False):
    html, STATUS = getServerList(conn, showFlavors, showImages)
    display( HTML(html) )
    return STATUS

def getFlavors(conn, showFlavors=False):
    flavor_names={}

    signal.alarm(10)
    try:
        flavors = conn.compute.flavors()
        for f in flavors:
            #print("FLAVOR: " + f['name'])
            flavor_names[f['id']]=f['name']

        if showFlavors:
            html = DictTable._repr_html_(flavor_names, highlights=None)
            display( HTML(html) )

    except TimeoutException as e:
        print("Failed to determine number of flavors" + str(e))
        return "0 flavors, ", flavor_names, 'ERROR'

    finally:
        signal.alarm(0)

    info_str = "{} flavors, ".format( len(flavor_names) )
    return info_str, flavor_names, 'OK'

def getImages(conn, showImages=False):
    image_names={}

    signal.alarm(10)
    try:
        images = conn.compute.images()
        for i in images:
            #print("IMAGE: " + i['name'])
            image_names[i['id']]=i['name']

        if showImages:
            html = DictTable._repr_html_(image_names, highlights=None)
            #print(html)
            display( HTML(html) )

    except TimeoutException as e:
        print("Failed to determine number of images" + str(e))
        return "0 images, ", image_names, 'ERROR'

    finally:
        signal.alarm(0)

    info_str = "{} images, ".format( len(image_names) )
    return info_str, image_names, 'OK'

def getServers(conn):
    servers_list=[]
    servers_html=[]

    headers=['name','status','flavor','image','addresses']
    servers_html = [ [ '<center><b>'+h+'</b></center>' for h in headers ] ]

    signal.alarm(10)
    try:
        servers = conn.compute.servers()
        for s in servers:
            servers_list += s
            #print("SERVER=" + str(s))
            s_list = getServerFields(s, headers, flavor_names, image_names)
            #print("SERVER fields=" + str(s_list))

            servers_html += [ s_list ]

    except TimeoutException as e:
        print("Failed to determine number of servers: " + str(e))
        return "0 servers, ", servers_list, 'ERROR'

    finally:
        signal.alarm(0)

    info_str = "{} servers, ".format( len(servers_list) )
    return info_str, servers_list, 'OK'

def getServerList(conn, showFlavors=False, showImages=False):

    flushfile.save_stderr()

    info_str=''

    STATUS='OK'
    html=''

    i_s, servers_list, STATUS = getServers(conn)
    info_str += i_s

    if STATUS == 'OK':
        i_s, flavor_names, STATUS = getFlavors(conn, showFlavors)
        info_str += i_s

        i_s, image_names, STATUS = getImages(conn, showImages)
        info_str += i_s

    signal.alarm(10)
    try:
        print(info_str)
        html = ListTable._repr_html_(servers_list, highlights)

        flushfile.restore_stderr()

    except TimeoutException as e:
        print("Failed to handle o/p: " + str(e))
        return html, 'ERROR'

    finally:
        signal.alarm(0)

    return html, STATUS

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
            signal.alarm(10)
            try:
                url=conn.authenticator.get_endpoint(conn.session, service_type=service, interface='public')
                endpoint_urls[service]=url
            #except _exceptions.EndpointNotFound:
            #    pass
            #except TimeoutException as e:
            except Exception as e:
                #raise
                print("Failed to determine '{}' service endpoint url".format(service))
            finally:
                signal.alarm(0)

    return html_ping_endpoint_urls(endpoint_urls)

def display_html_endpoint_urls(conn):
    html, status = html_endpoint_urls(conn)
    display( HTML(html) )
    return status

def platformStatus(platform, disk_thresholds):
    HTML_OP=''

    #if VERBOSE:
    tstring = strftime("%H:%M:%S", gmtime())
    print("\n-------- {} Checking platform <{}>".format(tstring, platform))
    
    HTML_OP += '<b>' + html_platform_info(platform, '<a href="#RESULTS_STATUS"> Return to Top (RESULTS_STATUS) </a>')+ '</b>'
    
    url, html = linkto_notebook_url(platform, host_ip="10.3.216.210", port=8888)
    HTML_OP += html

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
    HTML_OP += '<h3>Ping Status</h3>' + HTML
    
    if VERBOSE:
        print("Get server/flavor/image list ...")
    HTML, VMS_STATUS = getServerList( conn )
    HTML_OP += HTML

    if VMS_STATUS == 'ERROR':
        PING_PORTS_STATUS = 'UNKNOWN'
        ENDPOINTS_STATUS = 'UNKNOWN'
    else:
        if VERBOSE:
            print("Pinging ports ...")
        HTML, PING_PORTS_STATUS = html_ping_ports_all(inventory)
        HTML_OP += '<h3>Ports Status</h3>' + HTML
    
        if VERBOSE:
            print("Pinging endpoints ...")
        HTML, ENDPOINTS_STATUS = html_endpoint_urls(conn)
        HTML_OP += '<h3>Endpoints Status</h3>' + HTML
    
    DISK_USAGE = archive_df(inventory, platform)

    HIGHEST_DISK_PC, HIGHEST_DISK_PC_HOST, SUMMARY_HIGHEST_DISK_HTML, HIGHEST_DISK_HTML = \
        diskPCTable(platform, DISK_USAGE, thresholds=disk_thresholds, colours=['lightgreen','orange','red'])

    HTML_OP += '<h3>Disk Space</h3>' + HIGHEST_DISK_HTML
    #print( HIGHEST_DISK_HTML )

    RESULTS={
      'INVENTORY': inventory,
      'HTML_OP': HTML_OP,
      'PING_STATUS': PING_STATUS,
      'VMS_STATUS': VMS_STATUS,
      'PING_PORTS_STATUS': PING_PORTS_STATUS,
      'ENDPOINTS_STATUS': ENDPOINTS_STATUS,
      'HIGHEST_DISK_PC': HIGHEST_DISK_PC,
      'HIGHEST_DISK_PC_HOST': HIGHEST_DISK_PC_HOST,
      'SUMMARY_HIGHEST_DISK_HTML': SUMMARY_HIGHEST_DISK_HTML,
      'HIGHEST_DISK_HTML': HIGHEST_DISK_HTML
    }
    return RESULTS

def getplatformStatuses(platforms):
    UNDER_CRON=True

    HTML_OPS={}
    STATUSES={}
    DISK_USAGE={}

    thresholds=[70,90]
    colours=['lightgreen','orange','red']
    for platform in platforms:    
        STATUS = platformStatus(platform, disk_thresholds=[70,90])
        HTML_OPS[platform] = STATUS['HTML_OP'] + STATUS['HIGHEST_DISK_HTML']
        STATUSES[platform] = STATUS
        
    return HTML_OPS, STATUSES, DISK_USAGE

def showPlatformStatuses(platforms, HTML_OPS, STATUSES, DISK_USAGE):
    display( HTML( '<h1><a name="RESULTS_STATUS" /> Platforms Status Summary </h1>' ))

    DISP_STATUSES={}
    DISP_STATUSES['--Platform']=[ 'Worst case Disk usage', 'Ping', 'Ports', 'Endpoints', 'VMs' ]
    for platform in platforms:
        LINK='<a href="#RESULTS_' + platform + '">' + platform +'</a>'

        VALUES=[]
        for key in [ 'SUMMARY_HIGHEST_DISK_HTML', 'PING_STATUS', 'PING_PORTS_STATUS', 'ENDPOINTS_STATUS', 'VMS_STATUS']:
            VALUES.append( STATUSES[platform][key])

        DISP_STATUSES[LINK]= VALUES

    display( HTML( DictTable._repr_html_(DISP_STATUSES, STATUS_HIGHLIGHTS) ))

    display( HTML( '<h1>Platforms results </h1>' ))
    for platform in platforms:
        display( HTML( '<a name="RESULTS_{}">_</a>'.format(platform) ))
        HTML_OP = HTML_OPS[platform]
        display( HTML( HTML_OP )) 

