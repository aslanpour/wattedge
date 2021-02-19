import os
import subprocess
import time
from pijuice import PiJuice #sudo apt-get install pijuice-gui
import threading
import psutil
import re  #split by multiple items
import numpy as np
import RPi.GPIO as GPIO
import datetime
import requests
import paramiko
#INSTALL STRESS: SUDO APT INSTALL STRESS-ng


usb_meter_involved = True
battery_operated = True
wifi =True
set_time = False
benchmark_duration = (1 * 60)  # sec
benchmark_tolerance = 60 #60, for all=180
usb_meter_tail = 15 #15
epoches =1
stress_levels= [0]
start_epoch = 8 # def 1
#pgrep -f stress | xargs kill -9
#nohup $(pgrep -f stress|while read line;do cpulimit -p $line -l 10 &echo "1"; done) &

resource = 'wifi' # cpu  memory  disk all wifi idle (stress_level=0) bw http 
#1: http: run http server on both RPis
#2: load generator on both RPis in /home/pi
#3: empty report.txt, reduce bench tolerance due to request timeout
#4: check IPs
#5: check stress_level convertors in bw, http and mqtt
#6: check usbmeter is available and correct path
host_role = 'broker' #for bw (client or server), http (client or server), mqtt (subscriber, publisher, broker)


request_timeout = 10 #http 10
init_name = "/home/pi/Desktop/logs/" + resource + "/" # test specific

main_pi = "10.76.7.94"
second_pi = "10.76.7.95"

#cooldown between tests
network_reachability = 30
client_cooldown_time= 5 * 60
charge_wait_time = (25 * 60) 
cpu_cooldown_time = 5 
cpu_idle = 25
battery_low_charge = 25

#define monitoring parameters
test_duration = []
current_time = []
current_time_ts = []
battery_usage = []
cpuUtil = []
memory = []
disk_usage = []
disk_io_usage = []
cpu_temp = []
cpu_freq_curr=[]
cpu_freq_max=[]
cpu_freq_min=[]
cpu_ctx_swt = []
cpu_inter = []
cpu_soft_inter=[]

bw_usage = []

benchmark_is_running = False
epoch_num = 0
level = 0

relay_pin=6

if battery_operated:
    relay_pin = 20
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    pijuice = PiJuice(1, 0x14)

#---------------------------------------
# monitoring
def monitor_thread():
    
    global current_time
    global current_time_ts
    global battery_usage
    global pijuice
    global cpuUtil
    global memory
    global disk_usage
    global disk_io_usage
    global cpu_temp
    global cpu_freq_curr
    global cpu_freq_max
    global cpu_freq_min
    global cpu_ctx_swt
    global cpu_inter
    global cpu_soft_inter
    
    global bw_usage
    global benchmark_is_running

    while benchmark_is_running:
        #time
        #ct = datetime.datetime.now().strftime("%d%m%Y-%H%M%S")
        ct = datetime.datetime.now(datetime.timezone.utc).astimezone() # local
        ct_ts = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts

        current_time.append(ct)
        current_time_ts.append(ct_ts)
        
        # read battery
        if battery_operated:
            charge = pijuice.status.GetChargeLevel()
            battery_usage.append(int(charge['data']))
            
        else:
            battery_usage.append(-1)
        
        # read cpu
        cpu = psutil.cpu_percent()
        cpuUtil.append(cpu)
        #cpu frequency
        freq=re.split(', |=', str(psutil.cpu_freq()).split(')')[0])
        cpu_freq_curr.append(freq[1])
        cpu_freq_min.append(freq[3])
        cpu_freq_max.append(freq[5])
        
        swt=re.split(', |=', str(psutil.cpu_stats()).split(')')[0])
        cpu_ctx_swt.append(int(swt[1]))
        cpu_inter.append(int(swt[3]))
        cpu_soft_inter.append(int(swt[5]))
        
        # read memory
        memory_tmp = psutil.virtual_memory().percent
        memory.append(memory_tmp)
        # read disk
        disk_usage_tmp = psutil.disk_usage("/").percent
        disk_usage.append(disk_usage_tmp)
        # read disk I/O: read_count, write_count, read_bytes, write_bytes
        tmp = str(psutil.disk_io_counters()).split("(")[1].split(")")[0]
        tmp= re.split(', |=', tmp)
        tmp_list= [tmp[1], tmp[3], tmp[5], tmp[7]]
        disk_io_usage.append(tmp_list)
        # read cpu temperature
        cpu_temp_tmp = psutil.sensors_temperatures()
        #print(cpu_temp_tmp)
        cpu_temp_temp2 = cpu_temp_tmp['cpu_thermal'][0]
        cpu_temp_tmp = re.split(', |=', str(cpu_temp_temp2))
        cpu_temp.append(cpu_temp_tmp[3])
        # read bandwidth: packets_sent, packets_rec, bytes_sent, bytes_rec, bytes_dropin, bytes_dropout
        bw_tmp = [psutil.net_io_counters().packets_sent, psutil.net_io_counters().packets_recv,
                  psutil.net_io_counters().bytes_sent, psutil.net_io_counters().bytes_recv,
                  psutil.net_io_counters().dropin, psutil.net_io_counters().dropout]
        bw_usage.append(bw_tmp)

        time.sleep(1)

# ---------------------------------
def save_reports():
    global epoch_num
    global level
    global init_name
    
    log_index = init_name + "epoch" + str(epoch_num) + 'level' + str(level) + ".csv"

    monitor_list = []
    for i in range(len(cpuUtil)):
        curr_list =[]
        curr_list.append(str(current_time[i]))
        curr_list.append(str(current_time_ts[i]))
        curr_list.append(str(battery_usage[i]))
        curr_list.append(str(cpuUtil[i]))
        curr_list.append(str(cpu_temp[i]))
        curr_list.append(str(cpu_freq_curr[i]))
        curr_list.append(str(cpu_freq_min[i]))
        curr_list.append(str(cpu_freq_max[i]))
        curr_list.append(str(cpu_ctx_swt[i]))
        curr_list.append(str(cpu_inter[i]))
        curr_list.append(str(cpu_soft_inter[i]))
        curr_list.append(str(memory[i]))
        curr_list.append(str(disk_usage[i]))
        curr_list.append(str(disk_io_usage[i][0]))
        curr_list.append(str(disk_io_usage[i][1]))
        curr_list.append(str(disk_io_usage[i][2]))
        curr_list.append(str(disk_io_usage[i][3]))
        curr_list.append(str(bw_usage[i][0]))
        curr_list.append(str(bw_usage[i][1]))
        curr_list.append(str(bw_usage[i][2]))
        curr_list.append(str(bw_usage[i][3]))
        curr_list.append(str(bw_usage[i][4]))
        curr_list.append(str(bw_usage[i][5]))
        
        #curr_list.append('-1') #mWh
        #curr_list.append('-1') #Amper
        #curr_list.append('-1') #Watt
        
        monitor_list.append(curr_list)

    np.savetxt(log_index, monitor_list, delimiter=",", fmt="%s")
    print('######cpu=', str(sum(cpuUtil)/len(cpuUtil)))
    print('######memory=', str(sum(memory)/len(memory)))
    print('######ctx_swt=', str(cpu_ctx_swt[-1] - cpu_ctx_swt[0]))
    print('######ctx_inter=', str(cpu_inter[-1] - cpu_inter[0]))
    print('######ctx_soft=', str(cpu_soft_inter[-1]- cpu_soft_inter[0]))
    if usb_meter_involved:
        log_name = init_name + 'p_'\
            + 'epoch' + str(epoch_num) + 'level' + str(level) + '.csv'
        time.sleep(network_reachability)
        get_usbmeter_log(log_name)
        merge_monitors()
    #help: write one-dimentional array
    # battery usage
    #with open(init_name + 'battery_usage_' + log_index + ".csv", 'w') as filehandle:
        #filehandle.writelines("%s\n" % item for item in battery_usage)

def get_usbmeter_log(file):
    print('Get usbmeter log: ', file)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(second_pi, username='pi', password='disnetlab-bird')
    
    x = ["local time", "local time ts", "mWh", "mAh", "Volts",
                     "Amps", "Watts", "Temperature", "Resistence",
                     "data_line_pos_volt", "data_line_neg_volt",
                     "second_mWh", "second_mAh"]
    try:
        print('SSH ok')
        ftp_client= client.open_sftp()
        ftp_client.get(file, file) # remotefile, localfilepath
        ftp_client.close()
            
    finally:
        client.close()
        print('SSH connection close')
    

def merge_monitors():
    #usb metrics:
    x = ["local time", "local time ts", "mWh", "mAh", "Volts",
                     "Amps", "Watts", "Temperature", "Resistence",
                     "data_line_pos_volt", "data_line_neg_volt",
                     "second_mWh", "second_mAh"]
    
    try:
        monitor = init_name + 'epoch' + str(epoch_num) + 'level' + str(level) + '.csv'
        usbmeter = init_name + 'p_'\
            + 'epoch' + str(epoch_num) + 'level' + str(level) + '.csv'
        
        cmd = 'python3 /home/pi/merge_monitor.py --monitor ' + monitor + ' --usbmeter ' + usbmeter + ' --sample ' + str(benchmark_duration +1)
        print(cmd)
        os.system(cmd)
    except:
        print('Error merging monitors!')
        
#--------------------------------------------------------


def benchmark_thread():
    global level
    global test_duration

    level_str = str(level) 
    global benchmark_duration # test duration
    global benchmark_tolerance
    global resource
    
    time.sleep(5)
    cmd = 'no command'
    if not wifi:
        # wifi off
        cmd = "rfkill block all"
        #cmd= "sudo ifconfig wlan0 down"
        print(cmd)
        os.system(cmd)
        
    ct = datetime.datetime.now(datetime.timezone.utc).astimezone() # local
    print("Test started at: ", ct)
    
    start_time = time.time()
    global epoch_num
    
    #idle
    if resource=='idle':
        print('Pi in idle mode...')
        time.sleep(benchmark_duration + benchmark_tolerance)
    #wifi
    if resource=='wifi':
        #wifi on
        cmd = "rfkill unblock all"
        print(cmd)
        os.system(cmd)
        l='0'
        
        if level_str=='0': l='0'
        elif level_str=='0.5': l= '1'
        elif level_str=='1': l= '7'
        elif level_str=='2': l= '16'
        elif level_str=='2.5': l= '21'
        elif level_str=='3': l= '26'
        elif level_str=='4': l= '36'
        elif level_str=='5': l= '47'
        elif level_str=='6': l= '60'
        elif level_str=='7': l= '73'
        elif level_str=='8': l= '86'
        elif level_str=='9': l= '98'
        else:
            print('level10')
            
            
        
        
        if level_str=='10':
            cmd="stress -c 4 -t " + str(benchmark_duration + benchmark_tolerance) + " &"
        
        if l=='0':
            print('Pi in idle mode...')
            time.sleep(benchmark_duration + benchmark_tolerance)
        elif l=='10':
            cmd="stress -c 4 -t " + str(benchmark_duration + benchmark_tolerance) + " &"
            os.system(cmd)
            print(cmd)
            print('sleep')
            time.sleep(benchmark_duration + benchmark_tolerance)
        else:
            #cmd="sysbench --test=cpu --max-time=300 --num-threads=4 --cpu-max-prime=20000 run & cpulimit -P sysbench -l 60"
            #cmd=
            cmd = cmd="stress -c 4 -t " + str(benchmark_duration + benchmark_tolerance) +\
            " &  pgrep -f stress|while read line;do cpulimit -p $line -l " +str(l)+" &echo ' '; done"
            os.system(cmd)
            print(cmd)
            print('sleep')
            time.sleep(benchmark_duration + benchmark_tolerance)
            
    
        
        
    # cpu
    #if resource=='cpu':
    #    cmd = "stress-ng -t " + str(benchmark_duration + benchmark_tolerance) + " --cpu " + level_str \
    #                + " > stress_log"
    #    print(cmd)
    #    os.system(cmd)
    #cpu 
    if resource=='cpu':
        l='0'
        if level_str=='0.5': l= '1'
        elif level_str=='1': l= '7'
        elif level_str=='2': l= '16'
        elif level_str=='2.5': l= '21'
        elif level_str=='3': l= '26'
        elif level_str=='4': l= '36'
        elif level_str=='5': l= '47'
        elif level_str=='6': l= '60'
        elif level_str=='7': l= '73'
        elif level_str=='8': l= '86'
        elif level_str=='9': l= '98'
        else:
            print('level10')
            
            
        #cmd="sysbench --test=cpu --max-time=300 --num-threads=4 --cpu-max-prime=20000 run & cpulimit -P sysbench -l 60"
        #cmd=
        cmd = cmd="stress -c 4 -t " + str(benchmark_duration + benchmark_tolerance) +\
        " &  pgrep -f stress|while read line;do cpulimit -p $line -l " +str(l)+" &echo ' '; done"
        
        if level_str=='10':
            cmd="stress -c 4 -t " + str(benchmark_duration + benchmark_tolerance) + " &"
        print(cmd)
        os.system(cmd)
        
        print('sleep')
        time.sleep(benchmark_duration + benchmark_tolerance)
        
    #memory
    if resource == 'memory':
        # Stress the memory
        #https://manpages.ubuntu.com/manpages/artful/man1/stress-ng.1.html
        l =""
        if(level_str=='1'):l='25' 
        elif(level_str=='2'):l='50' 
        elif(level_str=='3'):l='75'
        elif(level_str=='4'):l='100'
        else:
            print('Stress level out of range!!!!')
        #cmd = "stress -t " + str(benchmark_duration) + " --vm " + vm_num_str + " --vm-bytes " + memory_load_size + " > logs/stress_log"
        cmd = "stress-ng --vm 1 " + " --vm-bytes " + l + "% -t " + str(benchmark_duration + benchmark_tolerance) + "s"
        
        print(cmd)
        os.system(cmd)
    #disk
    if resource == 'disk':
        l =""
        if(level_str=='1'):l='1' 
        elif(level_str=='2'):l='2' 
        elif(level_str=='3'):l='4'
        elif(level_str=='4'):l='8'
        elif(level_str=='5'):l='16'
        elif(level_str=='6'):l='32'
        elif(level_str=='7'):l='64'
        elif(level_str=='8'):l='125'
        elif(level_str=='9'):l='256'
        elif(level_str=='10'):l='512'
        elif(level_str=='11'):l='1024'
        elif(level_str=='12'):l='2048'
        elif(level_str=='13'):l='4096'
        elif(level_str=='14'):l='8192'
        else:
            print('Stress level out of range!!!!')
        #cmd = "stress -t " + str(benchmark_duration) + " --hdd " + hdd_worker_num_str \
        #                + " --hdd-bytes 2.35g> stress_log"
        
        cmd = "stress-ng --hdd 1" + " --hdd-bytes " + l +"m --timeout " + str(benchmark_duration + benchmark_tolerance) + "s"
        #cmd = "stress --hdd 1 -t 600s --hdd-bytes 9g"
        print(cmd)
        st = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local
        os.system(cmd)
        et = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local
        if (et-st) < benchmark_duration:
            print('ERROR: Benchmark failed!!!!!!!!!!!!!!!!!!!!!!!')
    #all
    if resource == 'all':
        # Stress
        #stress-ng --cpu 2 --vm 1 --vm-bytes 50% --hdd 1 --hdd-bytes 2m -t 960s
        cpu_level = '0'
        memory_level = '0'
        disk_level = '0'
        if(level_str=='1'):
            cpu_level= '1'
            memory_level='25%'
            disk_level='1m'
        elif(level_str=='2'):
            cpu_level='2'
            memory_level='50%'
            disk_level='2m'
        elif(level_str=='3'):
            cpu_level='3'
            memory_level='75%'
            disk_level='4m'
        elif(level_str=='4'):
            cpu_level='4'
            memory_level='100%'
            disk_level='8m'
            
        #cmd = "stress -t " + str(benchmark_duration) + " --cpu " + stress_level_num_str \
            #                +" --vm " + stress_level_num_str + " --vm-bytes 128M " \
            #                  " --io " + stress_level_num_str + " --hdd " + \
            #                stress_level_num_str + " > stress_log"
        cmd="stress-ng --cpu " + cpu_level + " --vm 1 --vm-bytes " + memory_level + \
                 " --hdd 1 --hdd-bytes " + disk_level + " -t " + str(benchmark_duration + benchmark_tolerance) +"s"
        print(cmd)
        
        st = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local
        print('start', datetime.datetime.now(datetime.timezone.utc).astimezone())
        os.system(cmd)
        print('end', datetime.datetime.now(datetime.timezone.utc).astimezone())
        et = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local
        if (et-st) < benchmark_duration:
            print('ERROR: Benchmarking finished earlier !!!!!!!!!!!!!!!!!!!!!!!')
    #bw
    if resource == 'bw':
        l =""
        if(level_str=='1'):l='2'
        elif(level_str=='2'):l='4' 
        elif(level_str=='3'):l='6' 
        elif(level_str=='4'):l='8'
        elif(level_str=='5'):l='10' 
        elif(level_str=='6'):l='12' 
        elif(level_str=='7'):l='14' 
        elif(level_str=='8'):l='16' 
        elif(level_str=='9'):l='18' 
        elif(level_str=='10'):l='20' 
        else:
            print('Stress BW level out of range!!!!')
            
        #server role
        if host_role == 'server':
            print('start local server', time.time())       
            #run local server
            cmd = "nohup iperf3 -s --one-off > iperflog &"
            print(cmd)
            os.system(cmd)
           
            #run remote client
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(second_pi, username='pi', password='disnetlab-bird')
            try:
                print('SSH ok')
                cmd = "iperf3 -c " + main_pi + " -t " + str(benchmark_duration + benchmark_tolerance)\
                     + " -b " + l + "m" + " --logfile " + init_name\
                     + "slog_epoch" + str(epoch_num) + "level" + str(level) + ".log"
                print(cmd)
                stdin, stdout, stderr = client.exec_command(cmd)
                print('Wait to cmd ends')
                #wait till the remote code is done
                time.sleep(benchmark_duration + benchmark_tolerance)
                
            finally:
                client.close()
                print('SSH connection close')
        # client   
        if host_role=='client':
            #run remote server
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(second_pi, username='pi', password='disnetlab-bird')
            try:
                print('SSH ok')
                cmd = "iperf3 -s --one-off"
                print(cmd)
                client.exec_command(cmd)
            finally:
                client.close()
                print('SSH connection close')
                
            #run local client note: server ip is changed
            cmd = "iperf3 -c " + second_pi + " -t " + str(benchmark_duration + benchmark_tolerance)\
                     + " -b " + l + "m" + " --logfile " + init_name\
                     + "clog_epoch" + str(epoch_num) + "level" + str(level) + ".log"
            
            print(cmd)
            os.system(cmd)
    #HTTP
    if resource=='http':
        #sample client run:
        #python3 http_load_generator.py --url http://10.76.7.95:5000/test --duration 60 --requests 1 --interval 1 --timeout 10 --info alaki --logfile /home/pi/Desktop/logs/http/c_report.txt
        l =""
        if(level_str=='1'):l='10' 
        elif(level_str=='2'):l='20' 
        elif(level_str=='3'):l='30'
        elif(level_str=='4'):l='40'
        elif(level_str=='5'):l='50'
        elif(level_str=='6'):l='60'
        elif(level_str=='7'):l='70'
        elif(level_str=='8'):l='80'
        elif(level_str=='9'):l='90'
        elif(level_str=='10'):l='100'
        else:
            print('Stress level out of range!!!!')
            
        # local server
        if host_role=='server':
            #run server
            print('Ensure local server is running!!!')
            cmd='nohup python3 http_server.py &'
            #print('RUN:', cmd)
            #os.system(cmd)
           
            #run remote client
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(second_pi, username='pi', password='disnetlab-bird')
            try:
                print('SSH ok')
                cmd = ('python3 /home/pi/http_load_generator.py '
                    ' --url http://' + main_pi + ':5000/test '
                    ' --duration ' + str(benchmark_duration) +
                    ' --requests ' + l + ' --interval 1 --timeout ' + str(request_timeout) +
                    ' --info epoch' + str(epoch_num) + 'level' + str(level) +
                    ' --logfile /home/pi/Desktop/logs/http/s_report.txt')
                
                print(cmd)
                client.exec_command(cmd)
                
                #wait till the remote code is done
                print('Wait till client is done')
                time.sleep(benchmark_duration + request_timeout)
                
            finally:
                client.close()
                print('SSH connection close')
        # local client
        if host_role=='client':
            #run remote server
            #assume the server is already run
            print('Ensure remote server is running!!!')
           
            #run local client
                #IPs change
            cmd = ('python3 /home/pi/http_load_generator.py '
                ' --url http://' + second_pi + ':5000/test '
                ' --duration ' + str(benchmark_duration) +
                ' --requests ' + l + ' --interval 1 --timeout ' + str(request_timeout) +
                ' --info epoch' + str(epoch_num) + 'level' + str(level) +
                ' --logfile /home/pi/Desktop/logs/http/c_report.txt')
                
            print(cmd)
            os.system(cmd)
    #mqtt       
    if resource =='mqtt':
        l =""
        if(level_str=='1'):l='10' 
        elif(level_str=='2'):l='20' 
        elif(level_str=='3'):l='30'
        elif(level_str=='4'):l='40'
        elif(level_str=='5'):l='50'
        elif(level_str=='6'):l='60'
        elif(level_str=='7'):l='70'
        elif(level_str=='8'):l='80'
        elif(level_str=='9'):l='90'
        elif(level_str=='10'):l='100'
        else:
            print('Stress level out of range!!!!')
            
        #publisher
        if host_role=='publisher':
            broker = second_pi
            sub = second_pi
            pub=main_pi
            #run remote broker
            #sudo systemctl status mosquitto
            print('Ensure remote broker is up and running!!')
            
            #run remote subscriber
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(second_pi, username='pi', password='disnetlab-bird')
            try:
                print('SSH ok')
                                
                cmd = ('python3 mqtt_handler.py '
                    ' --role subscriber --broker_ip ' + broker + ' --broker_port 1883 '
                    ' --subscriber_ip ' + sub + ' --publisher_ip ' + pub +
                    ' --duration ' + str(benchmark_duration + benchmark_tolerance) +
                    ' --msg_count ' + l + ' --interval 1 '
                    ' --timeout ' + str(request_timeout) +
                    ' --qos 0 --topic_send /reply/ --topic_recv /test/ '
                    ' --keep_alive 60 '
                    ' --info epoch' + str(epoch_num) + 'level' + str(level) + '')
                print(cmd)
                client.exec_command(cmd)
                
                                
            finally:
                client.close()
                print('SSH connection close')
            
            #run local publisher
                
            cmd=('python3 mqtt_handler.py --role publisher '
                 '--broker_ip {} --broker_port 1883 '
                 ' --subscriber_ip {} --publisher_ip {} '
                 ' --duration {} '
                 ' --msg_count {} --interval 1 '
                 ' --timeout {} --qos 0 '
                 ' --topic_send /test/ --topic_recv /reply/ '
                 ' --keep_alive 60 '
                 ' --logfile /home/pi/Desktop/logs/mqtt/p_report.txt'
                 ' --info epoch{}{}'.format(broker, sub, pub, benchmark_duration, l, request_timeout,
                         epoch_num, level))
            print(cmd)
            os.system(cmd)
        
        #Host is subscriber
        elif host_role == 'subscriber':
            broker = second_pi
            sub = main_pi
            pub=second_pi
            #run remote broker
            print('Ensure remote broker is up and running!!')
            #run local subscriber
            cmd = ('nohup python3 mqtt_handler.py '
                    ' --role subscriber --broker_ip {} --broker_port 1883 '
                    ' --subscriber_ip {} --publisher_ip {} '
                    ' --duration {} --msg_count {} --interval 1 '
                    ' --timeout {} --qos 0 --topic_send /reply/ --topic_recv /test/ '
                    ' --keep_alive 60  --info epoch{}level{} &'.format(broker, sub, pub,
                            str(benchmark_duration + benchmark_tolerance),
                            l, request_timeout, epoch_num, level))
            print(cmd)
            os.system(cmd)
            
            #run remote publisher
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(second_pi, username='pi', password='disnetlab-bird')
            try:
                print('SSH ok')
                cmd=('python3 mqtt_handler.py --role publisher '
                 '--broker_ip {} --broker_port 1883 --subscriber_ip {} --publisher_ip {} '
                 ' --duration {} '
                 ' --msg_count {} --interval 1 '
                 ' --timeout {} --qos 0 '
                 ' --topic_send /test/ --topic_recv /reply/ '
                 ' --keep_alive 60 '
                 ' --logfile /home/pi/Desktop/logs/mqtt/s_report.txt'
                 ' --info epoch{}{}'.format(broker, sub, pub,
                        benchmark_duration, l, request_timeout,
                        epoch_num, level))               
                
                client.exec_command(cmd)
                
                                
            finally:
                client.close()
                print('SSH connection close, wait for benchmark duration')
                time.sleep(benchmark_duration + benchmark_tolerance)
        
        #host is broker        
        elif host_role == 'broker':
            broker = main_pi
            sub = second_pi
            pub=second_pi
            #run local broker
            print("Run local broker, Mosquitto Service")
            cmd = "sudo systemctl start mosquitto"
            os.system(cmd)
            #run remote subscriber
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(second_pi, username='pi', password='disnetlab-bird')
            try:
                print('SSH ok')
                cmd = ('python3 mqtt_handler.py '
                ' --role subscriber --broker_ip {} --broker_port 1883 '
                ' --subscriber_ip {} --publisher_ip {} '
                ' --duration {} --msg_count {} --interval 1 '
                ' --timeout {} --qos 0 --topic_send /reply/ --topic_recv /test/ '
                ' --keep_alive 60  --info epoch{}level{}'.format(broker, sub, pub, 
                            str(benchmark_duration + benchmark_tolerance),
                            l, request_timeout, epoch_num, level))
                print(cmd)          
                client.exec_command(cmd)
                
                #run remote publisher
                cmd=('python3 mqtt_handler.py --role publisher '
                 '--broker_ip {} --broker_port 1883 '
                 ' --subscriber_ip {} --publisher_ip {} '
                 ' --duration {} '
                 ' --msg_count {} --interval 1 '
                 ' --timeout {} --qos 0 '
                 ' --topic_send /test/ --topic_recv /reply/ '
                 ' --keep_alive 60 '
                 ' --logfile /home/pi/Desktop/logs/mqtt/b_report.txt'
                 ' --info epoch{}{}'.format(broker, sub, pub,
                        benchmark_duration, l, request_timeout,
                        epoch_num, level))               
                
                print(cmd)
                client.exec_command(cmd)
                
            finally:
                client.close()
                print('SSH connection close, wait for benchmark duration')             
                time.sleep(benchmark_duration + benchmark_tolerance)
            
        else:
            print('Error-unknown host role for mqtt')
  
    end_time = time.time()
    test_duration.append(str(start_time))
    test_duration.append(str(end_time))
    test_duration.append(end_time-start_time)
    
    if not wifi:
        #wifi on
        cmd = "rfkill unblock all"
        #cmd="sudo ifconfig wlan0 up"
        print(cmd)
        os.system(cmd)
    
    time.sleep(10)
        
    
    global benchmark_is_running
    benchmark_is_running = False



#--------------------------
def usb_meter_connection():
    global epoch_num
    global level
    global benchmark_duration
    global init_name
    log_name = init_name + 'p_'\
            + 'epoch' + str(epoch_num) + 'level' + str(level)
    
    success = False
    
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(second_pi, username='pi', password='disnetlab-bird')
    try:
        print('SSH ok')
        if set_time:
            #worked better
            #ssh pi@10.76.7.95 sudo date -s @`( date -u +"%s" )`
            client.exec_command("sudo date --set='$(ssh pi@" + second_pi + " date)'")
        #unbuffer ---> sudo apt-get install expect (to print output in real time)
        stdin, stdout, stderr = client.exec_command('unbuffer python3 /home/pi/usbmeter  --addr ' \
            ' 00:15:A3:00:52:2B --timeout ' + str(benchmark_duration + usb_meter_tail) +
            ' --interval 1 --out ' + log_name)
        #cmd=python3 /home/pi/usbmeter --addr 00:15:A3:00:52:2B --timeout 10 --interval 1 --out /home/pi/logsusb
        time.sleep(5)
        if "Connected OK" in str(stdout.readlines(1)):
            print("USB Meter connected OK")
            success =True
        else:
            print("ERROR - USB Meter connection Failed!!!!!!!!!!!!!!!")
            
    finally:
        client.close()
        print('SSH connection close')
        
    return success

#------------------------------
 # reset metrics
def reset_metrics():
    global test_duration
    test_duration = []
    global current_time
    current_time = []
    global current_time_ts
    current_time_ts = []
    global battery_usage
    battery_usage = []
    global cpuUtil
    cpuUtil = []
    global memory
    memory = []
    global disk_usage
    disk_usage = []
    global disk_io_usage
    disk_io_usage = []
    global cpu_temp
    cpu_temp = []
    global cpu_freq_curr
    cpu_freq_curr=[]
    global cpu_freq_min
    cpu_freq_min=[]
    global cpu_freq_max
    cpu_freq_max=[]
    global cpu_ctx_swt
    cpu_ctx_swt = []
    global cpu_inter
    cpu_inter=[]
    global cpu_soft_inter
    cpu_soft_inter=[]
    global bw_usage
    bw_usage = []


#----------------------------------------------------------------------

def client_preparation():
    global cpu_idle
    global battery_low_charge
    global pijuice
    global cpu_cooldown_time
    global charge_wait_time

    # cooldown cpu usage > 50%
    while True:
        if psutil.cpu_percent() > cpu_idle:
            print("Wait for client CPU usage to cool down: " + str(cpu_cooldown_time)+ " sec" )
            time.sleep(cpu_cooldown_time)
        else:
            break


    # free up memory
        # cache (e.g., PageCache, dentries and inodes) and swap
    cmd = "sudo echo 3 > sudo /proc/sys/vm/drop_caches && sudo swapoff -a && sudo swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
    print(cmd)
    os.system(cmd)
    
    #Turn OFF HDMI output
    cmd="sudo /opt/vc/bin/tvservice -o"
    os.system(cmd)
    
    #stop mqtt broker
    if resource == 'mqtt' and host_role =='broker':
        print("Start Mosquitto Service")
        cmd = "sudo systemctl start mosquitto"
        os.system(cmd)
    else:
        print("Stop Mosquitto Service")
        cmd = "sudo systemctl stop mosquitto"
        os.system(cmd)
      
    #Turn OFF USB chip: https://learn.pi-supply.com/make/how-to-save-power-on-your-raspberry-pi/#disable-wi-fi-bluetooth
    cmd="echo '1-1' |sudo tee /sys/bus/usb/drivers/usb/unbind"
    os.system(cmd)
    
    if not battery_operated:
        return "Preparation done without battery check!"
    
    # battery status
    while True:
        charge = pijuice.status.GetChargeLevel()
        battery_tmp=int(charge['data'])
        print("Charge", battery_tmp)
        if battery_tmp < battery_low_charge:
            low_battery = \
                "###################\n" \
                "#                 #\n" \
                "#                 #\n" \
                "#                 #\n" \
                "#                 #\n" \
                "#   Low battery   #\n" \
                "#                 #\n" \
                "#                 #\n" \
                "#                 #\n" \
                "#                 #\n" \
                "###################\n" \
                "###################\n" \
                "###################\n"
            print(low_battery)
            print("ERROR: Client is not ready due to low battery charge")
            
            #turn on the client charger
            battery_power('ON')
            
            time.sleep(charge_wait_time)
        else:
            break

    # charge off
    battery_power('OFF')
            
    return "Preparation done with battery check"

# ----------------------------------------

def battery_power(command):
    if command=='ON':
        # turn on relay
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(relay_pin, GPIO.LOW)
    elif command=='OFF':
        # disconnect off the charger
        GPIO.setup(relay_pin, GPIO.HIGH)
    else:
        print("Error in battery_power command")
        
if __name__ == "__main__":
    
    epoches
    stress_levels

    benchmark_is_running
    client_cooldown_time

    epoch_num
    level

    for i in range(epoches):
        if i<3:
            epoch_num = i + start_epoch
        elif i<6 and i >=3:
            epoch_num = i + start_epoch - 3
            resource="disk"
        elif i<9 and i>=6:
            epoch_num = i + start_epoch - 6
            resource="all"
        
        for j in range(len(stress_levels)):
            level = stress_levels[j]

            # Test info
            info = "epoch #" + str(epoch_num) + " level =" + str(level)
            print("Test " + info + " is going to start...")
                       
                
            # test preparation client side
            client_preparation()

            # USB Meter connection
            if usb_meter_involved:
                attempts =3
                while not usb_meter_connection():
                    attempts -=1
                    time.sleep(60)
                    if attempts <=0:
                        #wifi on
                        cmd = "rfkill unblock all"
                        print(cmd)
                        os.system(cmd)
                        print('ERROR-USB Meter Failed to connect!!!!!')
                        if battery_operated: battery_power('ON')
                        time.sleep(86400)
                        
                if battery_operated: battery_power('OFF')
                    
            # run monitor and benchmark on client side
            benchmark_is_running = True
            
            
            print("Start Threads...")
            start_time = time.time()
            # monitoring thread
            thread1 = threading.Thread(target=monitor_thread, args=())
            # benchmarking thread
            thread2 = threading.Thread(target=benchmark_thread, args=())

            thread1.start()
            thread2.start()
            thread1.join()
            thread2.join()

            end_time = time.time()
            print("Test #" + info + " is done")


            # save reports
            print("Saving metrics in client side...")
            save_reports()
            # reset metrics
            reset_metrics()
            print("Client in cooldown (" + str(client_cooldown_time) + " s)")
            if battery_operated: battery_power('ON')
            
            time.sleep(client_cooldown_time)

            # print reports
            print("---%s seconds ---" % (end_time - start_time))
            # print("cpu util = ", *cpuUtil,sep=", ")
            # print("memory= ", *memory, sep=", ")
            # print("disk usage = ", *disk_usage, sep=", ")
            # print("disk IO = ", *disk_io_usage, sep=", ")
            # print("cpu temperature=", *cpu_temp, sep=", ")
            # print("bw=", *bw_usage, sep=", ")
            # print("battery=", *battery_usage, sep=", ")


    print('All tests are done.')
    #charge on
    # turn on the client charger
    if battery_operated: battery_power('ON')
    
    
