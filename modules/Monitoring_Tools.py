
'''
   Function to read a hosts inventory file, similar to Ansible inventory file format:
       http://docs.ansible.com/ansible/intro_inventory.html
'''

import sys, os

from Ping3      import ping

from IPython.core.display import display,HTML,Javascript

#import datetime
from time import gmtime, strftime

import signal
import traceback

class TimeoutException(Exception):
    """Exception raised for timeouts

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message

def signalHandler(signum, frame):
    tstring = strftime("%H:%M:%S", gmtime())
    print('{}: Monitoring_Tools: Signal handler called with signal'.format(tstring), signum)

    traceback.print_stack(frame, limit=-1, file=sys.stdout)
    traceback.print_stack(frame, limit=1, file=sys.stdout)
    raise TimeoutException("Monitoring - timeout")


## dtstring = strftime("%Y-%m-%d %H:%M:%S", gmtime())
## print("Starting at: " + dtstring)
signal.signal(signal.SIGALRM, signalHandler)

error_highlight='<div style="background-color: red; color: white"><b>{}</b></div>'
warn_highlight='<div style="background-color: orange; color: white"><b>{}</b></div>'
unknown_highlight='<div style="background-color: gray; color: white"><b>{}</b></div>'
ok_highlight='<div style="background-color: lightgreen; color: white"><b>{}</b></div>'

STATUS_HIGHLIGHTS={
    'OK':      ok_highlight,
    'WARN':  warn_highlight,
    'UNKNOWN':  unknown_highlight,
    'ERROR': error_highlight,
}

# Check if UNDER_CRON variable is set or not
if os.getenv('UNDER_CRON', '0') == '0':
    UNDER_CRON = False
else:
    UNDER_CRON = True

if os.getenv('VERBOSE', '0') == '0':
    VERBOSE = False
else:
    VERBOSE = True

import paramiko, socket

def aslicedict(aDict, str):
    return {k:v for k,v in aDict.items() if k.startswith(str)}

def slicedict(aDict, aList):
    return {k:v for k,v in aDict.items() if k in aList}

def ssh_command(host_name, host_ip, user, pkey, command):
    '''
       Simple wrapper around paramiko

       See http://stackoverflow.com/questions/13930858/what-error-exception-does-paramiko-throw-for-failed-connects
       for possible Exceptions handling.
    '''
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host_ip, username=user, key_filename=pkey, look_for_keys=False, timeout=10)
        stdin, stdout, stderr = ssh.exec_command(command)
        return stdout.read().decode('utf-8'), stderr.read().decode('utf-8')
    except paramiko.SSHException as e:
        print("SSHException: Failed to connect to {} [{}@{}]".format(host_name, user, host_ip))
    except paramiko.BadHostKeyException as e:
        print("BadHostKeyException: Failed to connect to {} [{}@{}]".format(host_name, user, host_ip))
    except paramiko.AuthenticationException as e:
        print("AuthenticationException: Failed to connect to {} [{}@{}]".format(host_name, user, host_ip))
    except socket.error  as e:
        print("ssh socket.error: Failed to connect to {} [{}@{}]".format(host_name, user, host_ip))
    except Exception as e:
        print("Failed to connect to {} [{}@{}]".format(host_name, user, host_ip))
    return "",""
    #return str(stdout.read()), str(stderr.read())

def strip_uptime(line):
    '''
       Strip the actual 'uptime' from the uptime output,
       e.g. given
            08:02:12 up 73 days, 18:12,  5 users,  load average: 0.04, 0.03, 0.05
       return
            73 days, 18:12
    '''
    #print(line)
    up_pos = line.find(" up ")
    if up_pos != -1:
        up_str = line[up_pos + 4:]
        comma_pos = up_str.find(",")
        if comma_pos != -1:
            comma_pos2 = up_str[comma_pos+1:].find(",")
            if comma_pos2 != -1:
                up_str=up_str[:comma_pos+comma_pos2+1]
                return up_str
    return ""

def display_platform(platform_name):
    display( HTML( html_platform_info(platform_name) ))

def html_platform_info(platform_name, extra_html=''):
    dtstring = strftime("%Y-%m-%d %H:%M:%S")
    #return '<h3>Platform: ' + platform_name + '</h3>' + '<h4>Run at: ' + dtstring + '</h4>'+extra_html
    return '<h3>Platform: ' + platform_name + ' [at ' + dtstring + '] </h3>'

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
                    
        #print("file=<" + hosts_file + "> hostname=<"+hostname+">")
    return ret



def ping_cmd(host):
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
    if VERBOSE:
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

    if VERBOSE:
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

    if VERBOSE:
        print("Min {}, Max {}, Avg {} msec".format(mmin,mmax,mavg))
        print("RETURNVAL=" + str(retval))
        #print("RETURNCODE=" + str(subproc.returncode))
    
    if rcvd != 0:
        return mavg
    else:
        return None
    #return(retval, sent, rcvd, lost, mmin, mmax, mavg)



def ping_all(inventory):

    for host in sorted(inventory['ping_check']):
        if not host in inventory['hosts']:
            print("Error: host <{}> not in hosts".format(host))
            return None
        host_entry = inventory['hosts'][host]
        ip=host
        if 'ansible_host' in host_entry:
            ip = host_entry['ansible_host']
        if 'ansible_ip' in host_entry:
            ip = host_entry['ansible_ip']
        if not UNDER_CRON and VERBOSE:
            sys.stdout.write("ping({}[{}]) ... ".format(host, ip))
        #result = ping(ip)
        signal.alarm(3)
        try:
            result = ping_cmd(ip)
        except:
            result = None
        finally:
            signal.alarm(0)

        if result:
            print("{} msec".format(result))
        #print("ping({}[{}] => {})".format(host, result, ip))
        
def display_html_ping_all(inventory):
    html, status = html_ping_all(inventory)
    display(HTML( html ))
    return status

def html_ping_all(inventory):
    
    results=dict()
    
    ping_checks=0
    for host in sorted(inventory['ping_check']):
        if not host in inventory['hosts']:
            print("Error: host <{}> not in hosts".format(host))
            return None, "ERROR"

        ping_checks += 1
        host_entry = inventory['hosts'][host]
        ip=host
        if 'ansible_host' in host_entry:
            ip = host_entry['ansible_host']
        if 'ansible_ip' in host_entry:
            ip = host_entry['ansible_ip']
        host_info="{}[{}]".format(host, ip)
        if not UNDER_CRON:
            sys.stdout.write("ping({}) ... ".format(host_info))
        #result = ping(ip)

        signal.alarm(3)
        try:
            result = ping_cmd(ip)
            if result:
                results[host_info]="OK: {} msec".format(result)
            else:
                results[host_info]="TIMEOUT"
        except KeyboardInterrupt:
            results[host_info]="TIMEOUT"
        except Exception as e:
            results[host_info]="TIMEOUT"
        finally:
            signal.alarm(0)
             
    if ping_checks == 0:
        return "<b>No ping_check entries in inventory</b>", "OK"

    ping_highlights={
        'OK':      ok_highlight,
        'TIMEOUT': error_highlight,
    }
    return DictTable._repr_html_(results, ping_highlights), "OK"


def ping_port(host, port,timeout=None):
    import socket;
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if timeout:
        sock.settimeout(timeout)
        
    ret = sock.connect_ex((host,port))
    if VERBOSE:
        if ret == 0:
            print("ping_port({},{}): OK".format(host,port))
        else:
            print("ping_port({},{}): errorno={}".format(host,port,ret))
    return ret


highlights={
    'active':   ok_highlight,
    'none':     warn_highlight,
    'inactive': warn_highlight,
    'down':     warn_highlight,
    'stop':     warn_highlight,
    'fail':     error_highlight,
    'error':    error_highlight,
}

def applyHighlights(value, highlights):
    for highlight in highlights.keys():
        str_value=str(value)
        lc_value=str(value).lower()
        if str_value[:len(highlight)] == highlight:
            value=highlights[highlight].format(str_value)

        elif lc_value[:len(highlight)] == highlight.lower():
            value=highlights[highlight].format(str(lc_value))

        #if highlight.lower() in lc_value:
        #    value=lc_value.replace(lc_value, highlights[highlight].format(lc_value))
            
    return value

class DictTable(dict):
    # Overridden dict class which takes a dict in the form {'a': 2, 'b': 3},
    # and renders an HTML Table in IPython Notebook.
    def _repr_html_(self, highlights=None, widths=None):
        html = [ '''<table width=700 style="border: 1px solid black; border-style: collapse;" border="1" width=100%>''' ]
        #for key, value in self.items():

        headerSeen=False
        for key in sorted(self):
            value = self[key]

            ''' If the first column starts with '--' we assume this row is the header and make it bold'''
            td='<td>'
            _td='</td>'
            if not headerSeen and key[0:2] == '--':
                key = key[2:]
                #tdwidth=''
                #if widths == None:
                    #tdwidth=' width={}%'.format(XX)
                #td='<td{}><b>'.format(tdwidth)
                td='<td><b>'
                _td='</b></td>'
                headerSeen = True

            _tdtd=_td+td

            html.append("<tr>")
            html.append("{}{}{}".format(td, key, _td))

            # If a tuple, convert to list:
            if type(value) is tuple:
                value=list(value)

            # If a list, expand to <td>'s:
            if type(value) is list:
                if highlights:
                    #print(str(value))
                    value=_tdtd.join( [ applyHighlights(str(val), highlights) for val in value] )
                else:
                    value=_tdtd.join(value)
            else:
                if highlights:
                    value=applyHighlights(value, highlights)

            html.append("{}{}{}".format(td, value, _td))
            html.append("</tr>\n")

        html.append("</table>\n")
        return ''.join(html)
    
class ListTable(list):
    # Overridden list class which takes a list,
    # and renders an HTML Table in IPython Notebook.
    def _repr_html_(self, highlights=None):
        html = [ '''<table style="border: 1px solid black; border-style: collapse;" border="1" width=100%>''' ]
        
        for row in self:
            html.append("<tr>")
            
            for elem in row:
                s_elem = elem
                if highlights:
                    html.append("<td>{0}</td>".format(applyHighlights(s_elem, highlights)))
                else:
                    html.append("<td>{0}</td>".format(s_elem))

            html.append("</tr>\n")
        html.append("</table>\n")
        return ''.join(html)


def display_html_ping_ports_all(inventory, group='ssh_check', ports=[22]):
     html, status = html_ping_ports_all(inventory, group, ports)
     display(HTML( html ))
     return status

def html_ping_ports_all(inventory, group='ssh_check', ports=[22]):

    results=dict()

    for host in sorted(inventory['ssh_check']):
        if not host in inventory['hosts']:
            print("Error: host <{}> not in hosts".format(host))
            return None, "ERROR"
        host_entry = inventory['hosts'][host]
        ip=host
        if 'ansible_host' in host_entry:
            ip = host_entry['ansible_host']
        if 'ansible_ip' in host_entry:
            ip = host_entry['ansible_ip']
        #result = ping(ip)
        for port in ports:
            ip_port=ip+":"+str(port)
            host_port_info="{}[{}]".format(host, ip_port)
            if not UNDER_CRON:
                sys.stdout.write("ping({}) ... ".format(host_port_info))
            result = ping_port(ip, port, timeout=2)
            if result == 0:
                results[host_port_info]="OK"
            else:
                results[host_port_info]="TIMEOUT"

    ping_highlights={
        'OK':      ok_highlight,
        'TIMEOUT': error_highlight,
    }
    return DictTable._repr_html_(results, ping_highlights), "OK"


def display_html(html):
    display(HTML( html ))

def display_html_ping_endpoint_urls(endpoint_urls):
    html, status = html_ping_endpoint_urls(endpoint_urls)
    display(HTML( html ))
    return status

def html_ping_endpoint_urls(endpoint_urls):

    results=dict()

    for service in endpoint_urls:
        ip_port = endpoint_urls[service].split('/')[2]
        (ip, port) = ip_port.split(':')
        service_info="{} [{}]".format(ip_port, service)
        
        if VERBOSE:
            #print("SERVICE={} HOST={} PORT={}".format(service, ip, port))
            sys.stdout.write("ping_port({}) ... ".format(service_info))
            
        result = ping_port(ip, int(port), timeout=2)
        if result == 0:
            results[service_info]="OK"
        else:
            results[service_info]="TIMEOUT"
            
        if VERBOSE:
            print(results[service_info])
            
    ping_highlights={
        'OK':      ok_highlight,
        'TIMEOUT': error_highlight,
    }
    return DictTable._repr_html_(results, ping_highlights), "OK"

"""
Doesn't work in html copy of notebook, as e-mail client won't run the javascript:

def show_notebook_url():
    html = notebook_url()
    display(HTML(html))

def linkto_notebook_url():

    return '''
<div id="notebookurl">NOTEBOOK_URL</div>
 
<script>
ahref='<h4>The latest version of this status is available at <a href="' + window.location + '">' + window.location + '</a><h4>'
//document.getElementById("notebookurl").innerHTML = window.location;
document.getElementById("notebookurl").innerHTML = ahref;
</script>
'''))

"""

def linkto_notebook_url(platform, host_ip, port=8888):
    url = get_notebook_url(platform, host_ip, port)
    #html='<h4>The latest version of this status is available at <a href="' + url + '">' + url + '</a></h4>'
    html='The latest version of this status is available at <a href="' + url + '">' + url + '</a>'
    return url, html

def show_notebook_url(platform, host_ip, port=8888):
    url, html = linkto_notebook_url(platform, host_ip, port)
    display(HTML(html))
    return url

def get_notebook_url(platform, host_ip, port=8888):
    # import jupyter_client
    # import json
    # connection_info_file=jupyter_client.find_connection_file()
    # connection_info_json=json.load(open(connection_info_file,'r'))
    #print(str(connection_info_json))

    #url="http://{}:{}/tree/notebooks/cron/OpenStack_Monitoring_{}.html".format(host_ip, port, platform)
    if UNDER_CRON:
        url="http://{}:{}/tree/notebooks/cron/OpenStack_MultipleSystems_Monitoring_ALL.html#RESULTS_STATUS".format(host_ip, port, platform)
    else:
        url="http://{}:{}/tree/notebooks/OpenStack_MultipleSystems_Monitoring_ALL.html#RESULTS_STATUS".format(host_ip, port, platform)
    #url="http://{}:{}/notebooks/notebooks/cron/OpenStack_Monitoring_{}.ipynb".format(host_ip, port, platform)
     #http://10.3.216.210:8888/notebooks/notebooks/cron/OpenStack_Monitoring_Py3.ipynb
    return url

def displayDiskPCTable(DISK_USAGE, thresholds=[70,90], colours=['lightgreen','orange','red']):
    highestpc, html = diskPCTable(platform, DISK_USAGE, thresholds, colours)
    display(HTML(html))
    return highestpc

def diskPCBarChart(label, pcs, thresholds=[70,90], colours=['lightgreen','orange','red'], orientation='height'):
    HTML_TABLE="<table class='noborder' height=120><tbody><tr>\n{}</tr></tbody></table>\n"
    table_rows = ""

    #table_rows += "<tr>"
    #PC_HOST="<b>{}</b>".format(label)
    for pc in pcs:
        #table_rows += "<td><table class='noborder'><tr>"
        PC = diskPCCell(pc, 0.8, thresholds, colours, orientation)

        #table_rows += '<tr><td width=20%>' + PC_HOST + '</td><td>' + PC + '</td></tr>\n'
        #table_rows += '<td>' + PC + '</td>'
        table_rows += PC
        #table_rows += "</tr>\n</table>\n</td>"
            
    #table_rows += "</tr>\n"
    html_table=HTML_TABLE.format(table_rows)
    return html_table

def diskPCCell(pc, pcwidth, thresholds=[70,90], colours=['lightgreen','orange','red'], orientation='width'):
    
    colour=colours[0]
    for t in range(len(thresholds)):
        if pc >= thresholds[t]:
            colour=colours[t+1]
            
    #width = 1+int(pcwidth * pc)
    if orientation == 'width':
        html_cell = "<tr><td class='noborder' style='color: #000; background-color: {};' width={}%><b>{}%</b></td><td></td></tr>".format(colour,pc,pc)
        return "<table width=500 class='noborder'><tr>" + html_cell + "</tr>\n</table>\n"
    else:
        html_cell = "<td><table class='noborder'>\n  "
        html_cell += "<tr height={} style='vertical-align:bottom;'><td class='noborder' style='vertical-align:bottom; color: #000; background-color: {};'><b>{}%</b></td></tr><tr><td style='vertical-align:bottom;'></td></tr>".format(pc, colour, pc)
        html_cell += "</table></td>\n  "
        return html_cell
    #return "<table class='noborder'><tr>" + html_cell + "</tr>\n</table>\n"
    return "____NEVER____"
    
def diskPCTable(platform, DISK_USAGE, thresholds=[70,90], colours=['lightgreen','orange','red']):
    HTML_TABLE="<table><tbody>\n{}</tbody></table>\n"
    elements={}
    
    for host in DISK_USAGE.keys():
        #print("host: " + host + " " + str(DISK_USAGE[host]))
        for partn in DISK_USAGE[host].keys():
            pc = DISK_USAGE[host][partn]
            #print("{}:{} {}%".format(host, partn, pc))
            hp = host + ':' + partn
            if pc in elements:
                elements[pc].append( hp )
            else:
                elements[pc] = [ hp ]
    
    reverse_sorted_keys=sorted(elements.keys(), reverse=True)
    highestpc=reverse_sorted_keys[0]
    highestpc_label=elements[highestpc]
    
    #thresholds.append(100)
    table_rows=''
    summary_table_rows=''
    
    for pc in reverse_sorted_keys:
        for label in elements[pc]:
            #TEST: import random
            #TEST: pc = random.randrange(0, 101, 2)

            table_row = "<table width=600 class='noborder'>"
            PC_HOST="<b>{}</b>".format(label)
            PC = diskPCCell(int(pc), 0.8, thresholds, colours, orientation='width')

            table_row += '<tr><td width=15%>' + PC_HOST + '</td><td>' + PC + '</td></tr>\n'
            table_row += "</table>\n"

            if summary_table_rows == '':
                summary_table_rows = table_row

            table_rows += table_row

            #pcs=[10,20,30,50,45,60,70,75,85,95,85]
            colon_pos=label.find(':')
            host=label[:colon_pos]
            part=label[colon_pos+1:].strip() # Why?
            df_trend = get_df_trend(platform, host, part)
            SEEN={}
            pcs=[]
            for i in df_trend:
                date, pc = i
                if not date in SEEN:
                    #print(i)
                    SEEN[date]=True
                    pcs.append(int(pc))
            #print("{} {}:{} %ages:{}".format(platform, host, part, str(pcs[-10:])))

            html = '<h4> ' + label + ': Disk usage trend</h4>' + diskPCBarChart(label, pcs)
            table_rows += '<table><tr><td>\n  ' + html + '\n</td></tr></table>'
            
    #html_table=HTML_TABLE.format(table_rows)
    html_table=HTML_TABLE.format(table_rows)
    #summary_html_table=HTML_TABLE.format(summary_table_rows)
    summary_html_table=summary_table_rows
    #print(table)
    #display(HTML(table))
    return highestpc, highestpc_label, summary_html_table, html_table

def archive_df(inventory, platform):
    #TODO: ! [ ! -d history ] && mkdir history

    import datetime
    import time

    #d = datetime.date.today().strftime("%B %d, %Y")
    #dt = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
    d = datetime.date.today().strftime("%Y-%m-%d")
    dt = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")
    if VERBOSE:
        print(d)
        print(dt)

    DISK_USAGE={}
    for host in sorted(inventory['df_check']):    
        ip = inventory['hosts'][host]['ansible_host']
        user = inventory['hosts'][host]['ansible_user']
        pkey = inventory['hosts'][host]['ssh_key']
        df_check = inventory['hosts'][host]['df_check']

        # write to history subdir (~/notebooks/cron for cron jobs)
        history_file='history/df_history_' + platform + '_' + host + '.txt'
        history_fd = open(history_file, 'a')

        full_df_cmd="hostname; df 2>&1"
        df_op, stderr = ssh_command(host, ip, user, pkey, full_df_cmd)    
        history_fd.write('DATE:' + dt + '\n' + df_op)
        history_fd.close()

        df_cmd="df " + df_check.replace(",", " ") + "| grep -v ^Filesystem"
        df_op, stderr = ssh_command(host, ip, user, pkey, df_cmd)    
        #df_op = stdout.decode('utf8')
        #print("HOST[" + host + "]<" + df_check + ">{" + df_cmd +"}:" + df_op)

        DISK_USAGE[host]={}
        df_lines=df_op.split("\n")
        for df_line in df_lines:
            #print("LINE: " + df_line)
            pc_pos = df_line.find("%")
            if pc_pos != -1:
                pc=int(df_line[pc_pos-3:pc_pos])
                partn=df_line[pc_pos+1:]
                if VERBOSE:
                    print(host + " " + str(pc) + "% " + partn)
                DISK_USAGE[host][partn]=pc

    return DISK_USAGE

def show_df_trend(inventory, platform):
    # TODO:
    for host in sorted(inventory['df_check']):    
        ip = inventory['hosts'][host]['ansible_host']

        # read from history subdir (~/notebooks/cron for cron jobs)
        history_file='history/df_history_' + platform + '_' + host + '.txt'
        history_fd = open(history_file, 'r')

        df_check = inventory['hosts'][host]['df_check']

        df_partns=df_check.split(",")

def get_df_trend(platform, host, part):
    # read from history subdir (~/notebooks/cron for cron jobs)
    history_file='history/df_history_' + platform + '_' + host + '.txt'
    history_fd = open(history_file, 'r')

    ENTRY=0
    PROCESS_ENTRY=False
    SEEN=dict()
    df_trend=[]

    for line in history_fd.readlines():
        line=line.rstrip()
        #print(line)
            
        if line.find("DATE:") == 0:
            date=line[5:]
            #date=date[ : date.find('_')]
            date=date[ : 10]
            if date in SEEN:
                PROCESS_ENTRY=False
                pass
            
            ENTRY += 1
            SEEN[date]=True
            PROCESS_ENTRY=True
            continue
        
        if PROCESS_ENTRY:
            #print("LINE:" + line)
            part_pos = line.rfind(' ' + part)
            exp_part_pos = len(line) - len(part) - 1
            
            #print("part[{}]_pos={}/{} llen={}".format(part, part_pos, exp_part_pos, len(line)))
            if part_pos != -1 and part_pos == exp_part_pos:
                #print("part[{}]_pos={} llen={}".format(part, part_pos, len(line)))
                pcpos=line.rfind("%")
                #print(pcpos)
                pcage=line[ pcpos-2:pcpos].strip()
                #print("{} PCAGE: {}%".format(part, pcage))
                df_trend.append( (date, pcage ))

    #print("Read {} entries [{} used] from {}".format(ENTRY, len(df_trend), history_file))
    return df_trend

def showUptimes():
    for host in sorted(inventory['ssh_check']):    
        ip = inventory['hosts'][host]['ansible_host']
        user = inventory['hosts'][host]['ansible_user']
        pkey = inventory['hosts'][host]['ssh_key']

        stdout, stderr = ssh_command(host, ip, user, pkey, "uptime")

        #print("LINE=" + stdout)
        uptime = strip_uptime(stdout)
        print(host + ":" + uptime)

