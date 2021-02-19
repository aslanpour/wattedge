import csv
import argparse
import numpy as np

# Parse arguments
parser = argparse.ArgumentParser(description="CLI for merging Monitor & USB Meter")
parser.add_argument("--monitor", dest="monitor", type=str,
                    help="Monitor file name", default="", required=False)
parser.add_argument("--usbmeter", dest="usbmeter", type=str,
                    help="USB Meter file name",default="", required=False)

parser.add_argument("--sample", dest="sample",help="Sample Size in second",
                    type=int, default=900, required=False)


args = parser.parse_args()

monitor_file =''
usbmeter_file=''
sample = 900

if args.monitor!="" or args.usbmeter!="":
    monitor_file = args.monitor
    usbmeter_file = args.usbmeter
else:
    monitor_file = '/home/pi/Desktop/logs/cpu/epoch1level1.csv'
    usbmeter_file = '/home/pi/Desktop/logs/cpu/p_epoch1level1.csv'

if args.sample!=900:
    sample=args.sample
    
merged = []
monitor=[]
usbmeter=[]

with open(monitor_file, 'r') as f_monitor, open(usbmeter_file, 'r') as f_usbmeter:
  
    for row in csv.reader(f_monitor):
        monitor.append(row)
    for row in csv.reader(f_usbmeter):
        usbmeter.append(row)


#get monitor from index 5
# get usbmeter from index ?
index = 0
for i in range(len(usbmeter)):
    
    if i==0: continue # first line contains labels
    
    if monitor[5][1].split('.')[0]== usbmeter[i][1].split('.')[0]:
        #print(i)        
        index = i
        
if index==0:
    print("ERROR -------------------")
else:
    print('matching index:', index)

if (sample + index) >= len(usbmeter):
    print('Short USB meter sample')
else:    

    for i in range(sample):
           
        newrow = monitor[5+i]
    
        newrow.append(usbmeter[index+i][0])
        newrow.append(usbmeter[index+i][1])
        newrow.append(usbmeter[index+i][2])
        newrow.append(usbmeter[index+i][3])
        newrow.append(usbmeter[index+i][4])
        newrow.append(usbmeter[index+i][5])
        newrow.append(usbmeter[index+i][6])
        newrow.append(usbmeter[index+i][7])
        newrow.append(usbmeter[index+i][8])
        newrow.append(usbmeter[index+i][9])
        newrow.append(usbmeter[index+i][10])
        newrow.append(usbmeter[index+i][11])
        newrow.append(usbmeter[index+i][12])
        
        merged.append(newrow)

    out = monitor_file.split('/')[0:-1]
    out = '/'.join(out) + '/m' + monitor_file.split('/')[-1]
    print("Write file to "+ out)
    np.savetxt(out, merged, delimiter=",", fmt="%s")
    



