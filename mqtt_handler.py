import time
import threading
import datetime
import argparse
import numpy as np
import json
from paho import mqtt # sudo pip3 install paho-mqtt
import paho.mqtt.client as mqttclient
import paho.mqtt.publish as publish
import logging

live_log =False

lock = threading.Lock()
counter = 0

# Parse arguments
parser = argparse.ArgumentParser(description="CLI for MQTT Load Generation")
parser.add_argument("--role", dest="role", type=str,
                    help="Publisher or Subscriber", default="", required=True)
parser.add_argument("--broker_ip", dest="broker_ip", type=str,
                    help="IP", default="", required=True)
parser.add_argument("--broker_port", dest="broker_port", type=int,
                    help="PORT", default=0, required=True)
parser.add_argument("--subscriber_ip", dest="subscriber_ip", type=str,
                    help="IP", default="", required=True)
parser.add_argument("--publisher_ip", dest="publisher_ip", type=str,
                    help="IP", default="", required=True)
parser.add_argument("--duration", dest="duration", type=int,
                    help="test duration",default=0, required=True)
parser.add_argument("--msg_count", dest="msg_count",help="Messages per interval",
                    type=int, default=0, required=True)
parser.add_argument("--interval", dest="interval",help="Interval in seconds",
                    type=int, default=0, required=True)
parser.add_argument("--timeout", dest="timeout",help="Requests Timeout in seconds",
                    type=int, default=0, required=True)
parser.add_argument("--qos", dest="qos", type=int,
                    help="e.g., 0, 1 or 2", default=0, required=True)
parser.add_argument("--topic_send", dest="topic_send", type=str,
                    help="e.g., /test/", default="", required=True)
parser.add_argument("--topic_recv", dest="topic_recv", type=str,
                    help="e.g., /reply/", default="", required=True)
parser.add_argument("--keep_alive", dest="keep_alive", type=int,
                    help="Keep alive msg interval in second", default=0, required=True)
parser.add_argument("--info", dest="info",help="Test info written in logs",
                    type=str, default='', required=True)
parser.add_argument("--logfile", dest="logfile",help="Log file full path, e.g. /home/pi/Desktop/logs/http/report.txt",
                    type=str, default='', required=False)


args = parser.parse_args()

#inputs
role = args.role
broker_ip = args.broker_ip
broker_port = args.broker_port
subscriber_ip = args.subscriber_ip
publisher_ip = args.publisher_ip
benchmark_duration = args.duration
msg_count = args.msg_count
msg_sending_interval = args.interval
msg_timeout = args.timeout
msg_qos = args.qos
msg_topic_send = args.topic_send
msg_topic_recv = args.topic_recv
keep_alive_interval = args.keep_alive
test_full_name = args.logfile

mqtt_protocol=mqttclient.MQTTv311
mqtt_transport = "tcp"
mqtt_tls = None


client = mqttclient.Client()

# calculate MQTT performance
total_requests_sent = 0
total_requests_recv = 0
total_requests_failed = 0
response_time = {}
if live_log:
    logging.basicConfig(level=logging.INFO)

def publisher():
           
    # start time
    start_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    
    
    iterations= int(benchmark_duration/msg_sending_interval)
    print('Sending ', str(msg_count), ' msg(s) every  ', str(msg_sending_interval), 's for ' + str(iterations) + ' iterations')
    
    for i in range(iterations):
        time1 = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
        #print('Interval #', i, ' for ', requests_count, ' reqs')
        
        threads = []
        # send X requests (i,e., requests_count)
            
        thread = threading.Thread(target=send_message, args=(msg_count,))
        thread.start()

        # every X seconds
        time2 = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
        time.sleep(msg_sending_interval - (time2 - time1))

    # end time
    end_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    
    # duration
    print('Test duration: ' + str(end_time - start_time) + 'wait for timeout ' + str(msg_timeout) + 's')
    
    time.sleep(msg_timeout)
    
    

def send_message(msg_count):
    global total_requests_sent
    global total_requests_recv
    global total_requests_failed
    global counter
    
    try:
        msgs = []
        for i in range(msg_count):
            counter +=1            
            msg = {'topic':msg_topic_send + str(counter), 'payload': None, 'retain': False, 'qos': msg_qos}
            
            msgs.append(msg)
            response_time[counter] = '@' + str(datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp())
            
                        
        publish.multiple(msgs, hostname=broker_ip, port=broker_port, keepalive=keep_alive_interval)
        total_requests_sent += int(msg_count)
        
    # if failed
    except Exception as e:
        with lock:
            total_requests_failed += msg_count
        print(e)


def subscriber():
    global counter
    
    # start time
    start_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    
    iterations= int(benchmark_duration/msg_sending_interval)
    msgs_to_be_received = iterations * msg_count
    while True:
        #all msgs received
        if counter == msgs_to_be_received:
            print('Subscriber received all ', msgs_to_be_received + ' msgs')
            break
        
        #time is over
        now_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
        elapsed_time = now_time - start_time
        
        if elapsed_time >= (benchmark_duration):
            print('Benchmark time is met.')
            break
        
        
        time.sleep(msg_sending_interval*2)
    
    # end time
    end_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    
    # duration
    print('Test duration: ' + str(end_time - start_time))
    print('Wait for timeout time of ' + str(msg_timeout))
    time.sleep(msg_timeout)
    
    
    
# callbacks
#logging
def on_log(client, userdata, level, buf):
    global live_log
    if live_log:
        logging.info(buf)
    else:
        pass

# When receives a CONBACK response from broker.
def on_connect(client, userdata, flags, rc):
    if rc==mqttclient.CONNACK_ACCEPTED:
        print("Client is connected to Broker")
        if role=='publisher' or role=='subscriber':
            client.subscribe(topic=msg_topic_recv + "+", qos=msg_qos)
    else:
        print("ERROR: Connected with result code " + str(rc))
        global live_log
        if live_log:
            logging.info('Bad connection')
        
# When the client sends a disconnect message to the broker.
def on_disconnect(client, userdata, flags, rc):
    global live_log
    if live_log:
        logging.info('In on_disconnect callback: client disconnected')
    if rc ==0:
        print("Gracefully Disconnected with result code " + str(rc))
    else:
        print("Ungracefully disconnection")
        
# on subscribe
def on_subscribe(client, obj, mid, granted_qos):
    global live_log
    if live_log:
        logging.info('In on_sub callback mid= ' + str(mid))
    print('Subscribed: ' + str(mid) + " " + str(granted_qos))

# on publish
def on_publish(client, userdata, mid):
    global live_log
    if live_log:
        logging.info('In on_pub callback mid= ' + str(mid))
    else:
        pass
    

# The callback for when a message is received on a topic from broker
def on_message(client, userdata, msg):
    global counter
    global total_requests_recv
    
    # received
    if msg_topic_recv in msg.topic:
        if role =='publisher':
            with lock:
                total_requests_recv += 1
                key = int(str(msg.topic).split('/')[-1]) # get key from  topic
                sent_time = float(response_time[key][1:]) #remove @ from the begining
                rec_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp()
                response_time[key] = rec_time - sent_time
        elif role=='subscriber':
            counter+=1
            client.publish(topic=msg_topic_send + str(msg.topic).split('/')[-1], payload=None, qos=msg.qos, retain=False)



def logs():
    global start
    global total_requests_sent
    global total_requests_recv
    global total_requests_failed
    
    end=datetime.datetime.now(datetime.timezone.utc).astimezone()
    
    log = args.info + '\n'
    log+= 'From ' + str(start) + '    To ' + str(end) + '\n'
    log += 'broker : '  + broker_ip + ':' + str(broker_port) + '\n'
    log += 'subscriber : ' + subscriber_ip + '\n'
    log += 'publisher : ' + publisher_ip + '\n'
    log+= 'Benchmark duration: ' + str(benchmark_duration) + '\n'
    log+= 'Requests: ' + str(msg_count) + '\n'
    log+= 'Interval: ' + str(msg_sending_interval) + '\n'
    log+= 'Timeout: ' + str(msg_timeout) + '\n'
    
    for val in response_time.values(): # it reads them as float
        if '@' in str(val):
            total_requests_failed +=1
            response_time[list(response_time.keys())[list(response_time.values()).index(val)]] = msg_timeout 
    #print(response_time.items())
            
    log += 'total requests sent: ' + str(total_requests_sent) + '\n'
    log+= 'total requests recevied: ' + str(total_requests_recv) + '\n'
    log += 'total requests failed: ' + str(total_requests_failed) + '\n'
    log += 'Success rate: ' + str(total_requests_recv / total_requests_sent) + '\n'
    #convert string to float in dictionery
    new_dict = dict(zip(response_time.keys(), [float(value) for value in response_time.values()]))
    
    log+= 'Avg. Response time: ' + str(sum(new_dict.values()) / len(new_dict)) + '\n'
    tmp = []
    for i in new_dict.values():
        tmp.append(float(i))
    a = np.array(tmp)
    p = [np.percentile(a, 25), np.percentile(a, 50), np.percentile(a, 75), np.percentile(a, 90),
         np.percentile(a, 95),np.percentile(a, 99),np.percentile(a, 99.9), np.percentile(a, 99.99)]
    log+= ('Percentiles: 25th: {}, 50th: {}, 75th: {}, 90th: {}, 95th: {}, 99th: {}, 99.9th: {}, 99.99th: {}'
           .format(str(p[0]),str(p[1]),str(p[2]),str(p[3]),str(p[4]),str(p[5]),str(p[6]),str(p[7])))
    log += '\n *************************** \n\n'
    
    #write logs
    print(log)
    
    with open(test_full_name, 'a') as logfile:
        logfile.write(log)
        
        
start = datetime.datetime.now(datetime.timezone.utc).astimezone() 

if __name__ == "__main__":
    start
    live_log    
    start = datetime.datetime.now(datetime.timezone.utc).astimezone() 
    print('Start: ', start)
              
    if role=='broker':
        cmd = 'sudo systemctl start mosquitto'
        print(cmd)
        os.system(cmd)
        print('Brooker serving for ', benchmark_duration + msg_timeout, 's')
        time.sleep(benchmark_duration + msg_timeout)
        
    else:
        #client without client_id
        client = mqttclient.Client(userdata=None, protocol=mqtt_protocol, transport=mqtt_transport)
        
        if live_log:
            client.on_log = on_log
            client.enable_logger()
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_subscribe = on_subscribe
        client.on_publish = on_publish
        client.on_message = on_message
        
        
        
        client.connect(host=broker_ip, port=broker_port, keepalive=keep_alive_interval)
        print("Client Loop Start ...")
        client.loop_start()

        if args.role=='publisher':
            # load generation
            publisher()
            #print logs
            logs()
        elif args.role=='subscriber':
            subscriber()
        else:
            print('ERROR- role not found')
                
        
        print("Client Loop Stop!")
        client.loop_stop()
        
        
    end = datetime.datetime.now(datetime.timezone.utc).astimezone()
    print('End: ', end)
    
    
    
    print('Test ' + args.info + ' is done and logs are written to '+ test_full_name)
