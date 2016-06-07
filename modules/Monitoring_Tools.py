
'''
   Function to read a hosts inventory file, similar to Ansible inventory file format:
       http://docs.ansible.com/ansible/intro_inventory.html
'''

import sys

from Ping3      import ping

from IPython.core.display import display,HTML

#from ShowTables import DictTable, ListTable, highlights, ok_highlight, warn_highlight, error_highlight

def display_platform(platform_name):
    display(HTML('<h1>Platform: ' + platform_name + '</h1>'))

def read_inventory(hosts_file):
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
        result = ping(ip, verbose)
        if result:
            print("{} msec".format(result))
        #print("ping({}[{}] => {})".format(host, result, ip))
        
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
        sys.stdout.write("ping({}[{}]) ... ".format(host, ip))
        result = ping(ip, verbose)
        if result:
            results[ip]="OK: {} msec".format(result)
        else:
            results[ip]="TIMEOUT"
             
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



