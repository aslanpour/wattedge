import time
import threading
import requests
import datetime
import argparse
import concurrent.futures
#sample code
#python3 http_load_generator.py --url http://10.76.7.95:5000/test --duration 60 --requests 1 --interval 1 --timeout 10 --info alaki --logfile /home/pi/Desktop/logs/http/c_report.txt

# Parse arguments
parser = argparse.ArgumentParser(description="CLI for HTTP Load Generation")
parser.add_argument("--url", dest="url", type=str,
                    help="Url e.g. http://10.76.7.91:5000/test ", default="", required=True)
parser.add_argument("--duration", dest="duration", type=int,
                    help="test duration",default=0, required=True)
parser.add_argument("--requests", dest="requests",help="Requests per interval",
                    type=int, default=0, required=True)
parser.add_argument("--interval", dest="interval",help="Interval in seconds",
                    type=int, default=0, required=True)
parser.add_argument("--timeout", dest="timeout",help="Requests Timeout in seconds",
                    type=int, default=0, required=True)
parser.add_argument("--info", dest="info",help="Test info written in logs",
                    type=str, default='', required=True)
parser.add_argument("--logfile", dest="logfile",help="Log file full path, e.g. /home/pi/Desktop/logs/http/report.txt",
                    type=str, default='', required=True)

args = parser.parse_args()

#inputs
url = args.url
benchmark_duration = args.duration
requests_count = args.requests
request_sending_interval = args.interval
request_timeout = args.timeout
test_full_name = args.logfile

#logging
total_requests_sent = 0
total_requests_recv = 0
total_requests_failed = 0
response_time = []

lock = threading.Lock()

def generator():
    global url
    global benchmark_duration
    global requests_count
    global request_sending_interval
    global request_timeout  # sec
    
    interval = request_sending_interval
    # start time
    start_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts

    with concurrent.futures.ThreadPoolExecutor(max_workers= requests_count * request_sending_interval) as executor:
        iterations= int(benchmark_duration/request_sending_interval)
        print('Sending ', str(requests_count), ' req(s) every  ', str(request_sending_interval), 's for ' + str(iterations) + ' iterations')
        counter = 0
        for i in range(iterations):
            time1 = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts

            for index in range(requests_count):
                counter +=1
                executor.submit(send_request, counter, url)
            
            # every X seconds
            time2 = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
            time.sleep(interval - (time2 - time1))
    
    #end time
    end_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    
    # duration
    print('Wait for timeout ', str(request_timeout), '   Test duration: ' + str(end_time - start_time))
    
    time.sleep(request_timeout)
        
        
def old_generator():
    global url
    global benchmark_duration
    global requests_count
    global request_sending_interval
    global request_timeout  # sec
        
    # start time
    start_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    
    
    iterations= int(benchmark_duration/request_sending_interval)
    print('Sending ', str(requests_count), ' req(s) every  ', str(request_sending_interval), 's for ' + str(iterations) + ' iterations')
    counter = 0
    for i in range(iterations):
        time1 = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
        #print('Interval #', i, ' for ', requests_count, ' reqs')
        
        
        threads = []
        # send X requests (i,e., requests_count)
        for index in range(requests_count):
            counter +=1
            thread = threading.Thread(target=send_request, args=(counter, url))
            threads.append(thread)

        for t in threads:
            t.start()

        # every X seconds
        time2 = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
        time.sleep(request_sending_interval - (time2 - time1))

    # end time
    end_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    
    # duration
    print('Test duration: ' + str(end_time - start_time))
    
    time.sleep(request_timeout)
    

def send_request(index, url):
    global total_requests_sent
    global total_requests_recv
    global total_requests_failed
    global response_time

    global request_timeout
    global lock
    
    # start time in utc
    thread_start_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    # set data
    url += "/" + str(index)
    try:
        # send
        response = requests.get(url=url, timeout=request_timeout)
        with lock:
            total_requests_sent += 1
        # if success
        if response.ok:
            with lock:
                total_requests_recv += 1
                thread_elapsed_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() - thread_start_time
                response_time.append(thread_elapsed_time)

    # if failed
    except Exception as e:
        with lock:
            total_requests_failed += 1
        print(e)


def old_send_request(index, url):
    global total_requests_sent
    global total_requests_recv
    global total_requests_failed
    global response_time

    global request_timeout
    global lock
    
    # start time in utc
    thread_start_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() # local ts
    # set data
    url += "/" + str(index)
    try:
        # send
        response = requests.post(url=url, timeout=request_timeout)
        with lock:
            total_requests_sent += 1
        # if success
        if response.ok:
            with lock:
                total_requests_recv += 1
                thread_elapsed_time = datetime.datetime.now(datetime.timezone.utc).astimezone().timestamp() - thread_start_time
                response_time.append(thread_elapsed_time)

    # if failed
    except Exception as e:
        with lock:
            total_requests_failed += 1
        print(e)



if __name__ == "__main__":
    start = datetime.datetime.now(datetime.timezone.utc).astimezone() 
    print('Start: ', start)
    
    # run the load generator
    generator()
    
    end = datetime.datetime.now(datetime.timezone.utc).astimezone()
    print('End: ', end)
    
    # print the logs to a file
    log = args.info + '\n'
    log+= 'From ' + str(start) + '    To ' + str(end) + '\n'
    log += 'url: '  + url + '\n'
    log+= 'Benchmark duration: ' + str(benchmark_duration) + '\n'
    log+= 'Requests: ' + str(requests_count) + '\n'
    log+= 'Interval: ' + str(request_sending_interval) + '\n'
    log+= 'Timeout: ' + str(request_timeout) + '\n'

    log += 'total requests sent: ' + str(total_requests_sent) + '\n'
    log+= 'total requests recevied: ' + str(total_requests_recv) + '\n'
    log += 'total requests failed: ' + str(total_requests_failed) + '\n'
    log += 'Success rate: ' + str(total_requests_recv / total_requests_sent) + '\n'
    log+= 'Avg. Response time: ' + str(sum(response_time) / len(response_time)) + '\n'
    log += '\n *************************** \n\n'
    
    #write logs
    print(log)
    
    with open(test_full_name, 'a') as logfile:
        logfile.write(log)
    
    print('Test ' + args.info + ' is done and logs are written to '+ test_full_name)