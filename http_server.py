import os
import time
#from pijuice import PiJuice
# sudo apt-get install pijuice-gui
import threading
import psutil
import re  # split string by multiple delimeters
import numpy as np
import json
from flask import *
from concurrent.futures import ThreadPoolExecutor  # to run a function in background
import RPi.GPIO as GPIO  # battery charging
from datetime import datetime
# rest after each test
cpu_cooldown_time = 5
# cpu percentage known as cpu is idle
cpu_idle = 25
# lowest battery charge allowed for testing
battery_low_charge = 30

executor = ThreadPoolExecutor(1)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
relay_pin = 20
#pijuice = PiJuice(1, 0x14)
# monitor variables
current_time = []
battery_usage = []
cpuUtil = []
memory = []
disk_usage = []
disk_io_usage = []
cpu_temp = []
bw_usage = []

# controlling variables
benchmark_is_running = False
counter = 0
epoch_num = 0
requests_count = 0
init_name = "logs/http/server"

app = Flask(__name__)
app.config["DEBUG"] = True


# answer to benchmark requests
@app.route('/test/<int:num>', methods=['GET', 'POST'])
def test(num):
    global counter
    counter += 1

    # return json.dumps(counter)
    return str(num)


# start the monitoring
@app.route('/start/<int:epoch>/<int:req>', methods=['GET'])
def start(epoch, req):
    # test preparation
    print("Start function is called for new test")
    global requests_count
    global epoch_num
    global benchmark_is_running
    requests_count = req
    epoch_num = epoch
    # server preparation
    if server_preparation():
        benchmark_is_running = True
        executor.submit(monitor)
        return 'True'
    else:
        return 'False'


# charging
@app.route('/recharge/<int:cmd_charge>', methods=['GET'])
def recharge(cmd_charge):
    global relay_pin
    
    # turn charger on
    if cmd_charge == 1:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(relay_pin, GPIO.LOW)
        pass
    else:  # turn off
        GPIO.setup(relay_pin, GPIO.HIGH)
        pass

    return 'True'


# stop the monitoring
@app.route('/stop', methods=['GET'])
def stop():
    print("Stop function is called...")
    # stop monitor
    global benchmark_is_running
    benchmark_is_running = False
    time.sleep(1)  # wait to ensure monitor is stopped

    # save reports
    save_reports()
    # reset metrics
    reset_metrics()

    global counter
    counter = 0

    return "##SERVER: Stop function is done and monitoring variables are reset\n"


# -------------------------
# test preparation
def server_preparation():
    global cpu_idle
    global battery_low_charge
    global pijuice

    # cooldown cpu usage
    while True:
        if psutil.cpu_percent() > cpu_idle:
            print("Wait for server CPU usage to cool down: " + str(cpu_cooldown_time) + " sec")
            time.sleep(cpu_cooldown_time)
        else:
            break
        time.sleep(cpu_cooldown_time)

    # free up memory
    # cache (e.g., PageCache, dentries and inodes) and swap
    cmd = "sudo echo 3 > sudo /proc/sys/vm/drop_caches && sudo swapoff -a && sudo swapon -a && printf '\n%s\n' 'Ram-cache and Swap Cleared'"
    os.system(cmd)

    # battery status
    charge = pijuice.status.GetChargeLevel()
    battery_tmp = int(charge['data'])
    # battery_tmp =30 #???
    if battery_tmp < battery_low_charge:
        return False
    else:
        return True


# -------------------

def reset_metrics():
    # reset variables
    global test_duration
    test_duration = []
    global current_time
    current_time = []
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
    global bw_usage
    bw_usage = []


# --------------------------------------------------------

def monitor():
    print("Monitor function is started")
    global current_time
    global battery_usage
    global cpuUtil
    global memory
    global disk_usage
    global disk_io_usage
    global cpu_temp
    global bw_usage

    global benchmark_is_running
    global pijuice
    global requests_count
    global epoch_num

    
    while benchmark_is_running:
        #current time
        ct = datetime.utcnow().timestamp()
        if first_timestamp ==-1.0:
            first_timestamp = ct
        
        ct = int(ct- first_timestamp)
        #ct = datetime.now().strftime("%d%m%Y-%H%M%S")
        current_time.append(ct)
        # read battery
        charge = pijuice.status.GetChargeLevel()
        battery_usage.append(int(charge['data']))
        # read cpu
        cpu = psutil.cpu_percent()
        cpuUtil.append(cpu)
        # read memory
        memory_tmp = psutil.virtual_memory().percent
        memory.append(memory_tmp)
        # read disk
        disk_usage_tmp = psutil.disk_usage("/").percent
        disk_usage.append(disk_usage_tmp)
        # read disk I/O: read_count, write_count, read_bytes, write_bytes
        tmp = str(psutil.disk_io_counters()).split("(")[1].split(")")[0]
        tmp = re.split(', |=', tmp)
        tmp_list = [tmp[1], tmp[3], tmp[5], tmp[7]]
        disk_io_usage.append(tmp_list)
        # read cpu temperature
        cpu_temp_tmp = psutil.sensors_temperatures()
        cpu_temp_temp2 = cpu_temp_tmp['cpu-thermal'][0]
        cpu_temp_tmp = re.split(', |=', str(cpu_temp_temp2))
        cpu_temp.append(cpu_temp_tmp[3])
        # read bandwidth: packets_sent, packets_rec, bytes_sent, bytes_rec, bytes_dropin, bytes_dropout
        bw_tmp = [psutil.net_io_counters().packets_sent, psutil.net_io_counters().packets_recv,
                  psutil.net_io_counters().bytes_sent, psutil.net_io_counters().bytes_recv,
                  psutil.net_io_counters().dropin, psutil.net_io_counters().dropout]
        bw_usage.append(bw_tmp)

        time.sleep(1)

    else:
        print("monitor function is sopped")


def save_reports():
    print("Saving metrics...")
    global requests_count
    global epoch_num
    global path_for_logs
    global init_name
    
    
    log_index = init_name + "_" + str(epoch_num) + '_req' + str(requests_count)
    
    monitor_list = []
    
    # add labels
    label_list =  ['timestamp', 'battery', 'cpu', 'temperature', 'memory', 'hard',
                   'io_read_count', 'io_write_count', 'io_read_bytes', 'io_write_bytes',
                   'bw_packets_sent', 'bw_packets_rec', 'bw_bytes_sent', 'bw_bytes_rec',
                   'bw_bytes_dropin', 'by_bytes_dropout']
    
    monitor_list.append(label_list)
    
    # assuming that all monitored arrays have the same length and equal to cpuUtil
    for i in range(len(cpuUtil)):
        curr_list = []
        curr_list.append(str(current_time[i]))
        curr_list.append(str(battery_usage[i]))
        curr_list.append(str(cpuUtil[i]))
        curr_list.append(str(cpu_temp[i]))
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

        monitor_list.append(curr_list)

    np.savetxt(log_index, monitor_list, delimiter=",", fmt="%s")

    # write one-dimentional array
    # battery usage
    # with open(init_name +'battery_usage_' + log_index + ".csv", 'w') as filehandle:
    # filehandle.writelines("%s\n" % item for item in battery_usage)


# ----------------------------------------------------------------------

if __name__ == "__main__":
    counter = 0
    benchmark_is_running
    benchmark_is_running = False

app.run(host='0.0.0.0', port=5000, threaded=True)