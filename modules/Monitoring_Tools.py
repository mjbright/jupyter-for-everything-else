
'''
   Function to read a hosts inventory file, similar to Ansible inventory file format:
       http://docs.ansible.com/ansible/intro_inventory.html
'''

import sys, os

from Ping3      import ping

from IPython.core.display import display,HTML,Javascript

#import datetime
from time import gmtime, strftime

def display_platform(platform_name):
    #dtstring = str(datetime.datetime.now())
    #dtstring = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    dtstring = strftime("%Y-%m-%d %H:%M:%S")
    display(HTML('<h1>Platform: ' + platform_name + '</h1>' + \
                 '<h4>Run at: ' + dtstring + '</h4>'))

def read_inventory(hosts_file):
    hosts_file = hosts_file.replace('~', os.getenv('HOME')).replace('$HOME', os.getenv('HOME'))
    fd = open(hosts_file, 'r')
    group=None
    
    ret=dict()
    
    for line in fd.readlines():
        line = line.strip()
        if len(line) == 0:
            if group != None:
                group = None
            continue
            
        if line[0] == '#':
            continue

        if not group:
            if line[0] == "[" and line[-1] == "]":
                group = line[1:-1]
                if group in ret:
                    print("Error: group <{}> already exists".format(group))
                    return None
                
                #print("GROUP:" + group)
                ret[group]=dict()
            else:
                print("Error: Expecting a group entry in line <{}>".format(line))
                return None
            continue

        space = line.find(' ')
        if space == -1:
            hostname=line
            ret[group][hostname]={}
        else:
            hostname=line[:space]
            ret[group][hostname]={}
            args=line[space:].strip()
            arg_entries=args.split(' ')
            #if len(arg_entries) != 0:
            #    print(str(arg_entries))
            for arg in arg_entries:
                if arg == '':
                    continue
                eqpos=arg.find('=')
                if eqpos != -1:
                    key=arg[:eqpos]
                    val=arg[eqpos+1:]
                    ret[group][hostname][key]=val
                    
        #print("hostname=<"+hostname+">")
    return ret



def ping_cmd(host, verbose=False):
    """
    Returns True if host responds to a ping request
    """
    import os, platform

    # Ping parameters as function of OS
    ping_str = "-n 2" if  platform.system().lower()=="windows" else "-c 2"

    # Ping
    cmd="ping " + ping_str + " " + host
    
    from subprocess import Popen
    import subprocess
    subproc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    retval = subproc.wait()
    stdout = subproc.stdout.read()
    if verbose:
        print(stdout)
    
    import re
    m = re.search('Packets: Sent = ([0-9]+), Received = ([0-9]+), Lost = ([0-9]+)', str(stdout))
    #print("GROUP(0)=<" + m.group(0) + ">")
    if m:
        sent=m.group(1)
        rcvd=m.group(2)
        lost=m.group(3)
    else:
        # Linux: 1 packets transmitted, 1 received, 0% packet loss, time 0ms\nrtt min/avg/max/mdev = 0.030/0.030/0.030/0.000 ms\n
        m = re.search('([0-9]+) packets transmitted, ([0-9]+) received', str(stdout))
        sent=int(m.group(1))
        rcvd=int(m.group(2))
        lost=sent-rcvd

    if verbose:
        print("Sent {}, Received {}, Lost {} packets".format(sent,rcvd,lost))

    m = re.search('Minimum = ([0-9]+)ms, Maximum = ([0-9]*)ms, Average = ([0-9]*)ms', str(stdout))
    #print("GROUP(0)=<" + m.group(0) + ">")
    mmin=0
    mmax=0
    mavg=0
    if m:
        mmin=m.group(1)
        mmax=m.group(2)
        mavg=m.group(3)
    else:
        m = re.search('rtt min\/avg\/max\/mdev = ([0-9,\.]+)\/([0-9,\.]+)\/([0-9,\.]+)\/', str(stdout))
        if m:
            mmin=m.group(1)
            mavg=m.group(2)
            mmax=m.group(3)

    if verbose:
        print("Min {}, Max {}, Avg {} msec".format(mmin,mmax,mavg))
        print("RETURNVAL=" + str(retval))
        #print("RETURNCODE=" + str(subproc.returncode))
    
    if rcvd != 0:
        return mavg
    else:
        return None
    #return(retval, sent, rcvd, lost, mmin, mmax, mavg)



def ping_all(inventory, verbose=False):
    for host in inventory['ping_check']:
        if not host in inventory['hosts']:
            print("Error: host <{}> not in hosts".format(host))
            return None
        host_entry = inventory['hosts'][host]
        ip=host
        if 'ansible_host' in host_entry:
            ip = host_entry['ansible_host']
        if 'ansible_ip' in host_entry:
            ip = host_entry['ansible_ip']
        sys.stdout.write("ping({}[{}]) ... ".format(host, ip))
        #result = ping(ip, verbose)
        result = ping_cmd(ip, verbose)
        if result:
            print("{} msec".format(result))
        #print("ping({}[{}] => {})".format(host, result, ip))
        
def display_html_ping_all(inventory, verbose=False):
    display(HTML( html_ping_all(inventory, verbose) ))

def html_ping_all(inventory, verbose=False):
    
    results=dict()
    
    for host in inventory['ping_check']:
        if not host in inventory['hosts']:
            print("Error: host <{}> not in hosts".format(host))
            return None
        host_entry = inventory['hosts'][host]
        ip=host
        if 'ansible_host' in host_entry:
            ip = host_entry['ansible_host']
        if 'ansible_ip' in host_entry:
            ip = host_entry['ansible_ip']
        host_info="{}[{}]".format(host, ip)
        sys.stdout.write("ping({}) ... ".format(host_info))
        #result = ping(ip, verbose)
        result = ping_cmd(ip, verbose)
        if result:
            results[host_info]="OK: {} msec".format(result)
        else:
            results[host_info]="TIMEOUT"
             
    ping_highlights={
        'OK':      ok_highlight,
        'TIMEOUT': error_highlight,
    }
    return DictTable._repr_html_(results, ping_highlights)


def ping_port(host, port,verbose=False,timeout=None):
    import socket;
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if timeout:
        sock.settimeout(timeout)
        
    ret = sock.connect_ex((host,port))
    if verbose:
        if ret == 0:
            print("ping_port({},{}): OK".format(host,port))
        else:
            print("ping_port({},{}): errorno={}".format(host,port,ret))
    return ret



error_highlight='<div style="background-color: red; color: white"><b>{}</b></div>'
warn_highlight='<div style="background-color: orange; color: white"><b>{}</b></div>'
ok_highlight='<div style="background-color: green; color: white"><b>{}</b></div>'

highlights={
    'active':   ok_highlight,
    'inactive': warn_highlight,
    'down':     warn_highlight,
    'stop':     warn_highlight,
    'fail':     error_highlight,
    'error':     error_highlight,
}

def applyHighlights(value, highlights):
    for highlight in highlights.keys():
        if str(value).lower()[:len(highlight)] == highlight.lower():
        #if highlight in str(value).lower():
            value=highlights[highlight].format(str(value))
            
    return value

class DictTable(dict):
    # Overridden dict class which takes a dict in the form {'a': 2, 'b': 3},
    # and renders an HTML Table in IPython Notebook.
    def _repr_html_(self, highlights=None):
        html = [ '''<table style="border: 1px solid black; border-style: collapse;" border="1" width=100%>"''' ]
        for key, value in self.items():
            html.append("<tr>")
            html.append("<td>{0}</td>".format(key))
            if highlights:
                html.append("<td>{0}</td>".format(applyHighlights(value, highlights)))
            else:
                html.append("<td>{0}</td>".format(value))
            html.append("</tr>")
        html.append("</table>")
        return ''.join(html)
    
class ListTable(list):
    # Overridden list class which takes a list,
    # and renders an HTML Table in IPython Notebook.
    def _repr_html_(self, highlights=None):
        html = [ '''<table style="border: 1px solid black; border-style: collapse;" border="1" width=100%>"''' ]
        
        for row in self:
            html.append("<tr>")
            
            for elem in row:
                s_elem = elem
                if highlights:
                    html.append("<td>{0}</td>".format(applyHighlights(s_elem, highlights)))
                else:
                    html.append("<td>{0}</td>".format(s_elem))

            html.append("</tr>")
        html.append("</table>")
        return ''.join(html)


def display_html_ping_ports_all(inventory, group='ssh_check', ports=[22], verbose=False):
     display(HTML( html_ping_ports_all(inventory, group, ports, verbose)))

def html_ping_ports_all(inventory, group='ssh_check', ports=[22], verbose=False):

    results=dict()

    for host in inventory['ssh_check']:
        if not host in inventory['hosts']:
            print("Error: host <{}> not in hosts".format(host))
            return None
        host_entry = inventory['hosts'][host]
        ip=host
        if 'ansible_host' in host_entry:
            ip = host_entry['ansible_host']
        if 'ansible_ip' in host_entry:
            ip = host_entry['ansible_ip']
        #result = ping(ip, verbose)
        for port in ports:
            ip_port=ip+":"+str(port)
            host_port_info="{}[{}]".format(host, ip_port)
            sys.stdout.write("ping({}) ... ".format(host_port_info))
            result = ping_port(ip, port, verbose, timeout=2)
            if result == 0:
                results[host_port_info]="OK"
            else:
                results[host_port_info]="TIMEOUT"

    ping_highlights={
        'OK':      ok_highlight,
        'TIMEOUT': error_highlight,
    }
    return DictTable._repr_html_(results, ping_highlights)


def display_html(html):
    display(HTML( html ))

def display_html_ping_endpoint_urls(endpoint_urls, verbose=False):
    display(HTML( html_ping_endpoint_urls(endpoint_urls, verbose)))

def html_ping_endpoint_urls(endpoint_urls, verbose=False):

    results=dict()

    for service in endpoint_urls:
        ip_port = endpoint_urls[service].split('/')[2]
        (ip, port) = ip_port.split(':')
        service_info="{} [{}]".format(ip_port, service)
        
        if verbose:
            #print("SERVICE={} HOST={} PORT={}".format(service, ip, port))
            sys.stdout.write("ping_port({}) ... ".format(service_info))
            
        result = ping_port(ip, int(port), verbose, timeout=2)
        if result == 0:
            results[service_info]="OK"
        else:
            results[service_info]="TIMEOUT"
            
        if verbose:
            print(results[service_info])
            
    ping_highlights={
        'OK':      ok_highlight,
        'TIMEOUT': error_highlight,
    }
    return DictTable._repr_html_(results, ping_highlights)

"""
Doesn't work in html copy of notebook, as e-mail client won't run the javascript:

def show_notebook_url():
    display(HTML('''
<div id="notebookurl">NOTEBOOK_URL</div>
 
<script>
ahref='<h4>The latest version of this status is available at <a href="' + window.location + '">' + window.location + '</a><h4>'
//document.getElementById("notebookurl").innerHTML = window.location;
document.getElementById("notebookurl").innerHTML = ahref;
</script>
'''))

"""

def show_notebook_url(platform, host_ip, port=8888):
    url = get_notebook_url(platform, host_ip, port)
    html='<h4>The latest version of this status is available at <a href="' + url + '">' + url + '</a></h4>'
    display(HTML( html ))

def get_notebook_url(platform, host_ip, port=8888):
    # import jupyter_client
    # import json
    # connection_info_file=jupyter_client.find_connection_file()
    # connection_info_json=json.load(open(connection_info_file,'r'))
    #print(str(connection_info_json))

    url="http://{}:{}/tree/notebooks/cron/OpenStack_Monitoring_{}.html".format(host_ip, port, platform)
    #url="http://{}:{}/notebooks/notebooks/cron/OpenStack_Monitoring_{}.ipynb".format(host_ip, port, platform)
     #http://10.3.216.210:8888/notebooks/notebooks/cron/OpenStack_Monitoring_Py3.ipynb
    return url

