# -*- coding: utf-8 -*-
"""
Created on Sat Aug  1 04:44:55 2018

@author: Amr Hendy
"""


import pandas as pd

#reading datafile
df = pd.read_csv('..\WiFi-SLAM\E-house\wifiscanlog - 2016-02-09.csv', sep=',')
df.head()

#filtering
df = df[df.groupby('scanId').scanId.transform(len) > 4]
number_of_APs = df.ssid.value_counts().size;
number_of_scans = df.scanId.value_counts().size;
print('number of scans = ' + str(number_of_scans))
print('number of APs = ' + str(number_of_APs))

#first 3*number_of scans represent scan position x,y,z
#then 3*number_of APs represent APs x,y,z
initial_guess = []

#initial values x,y,z for scans positions
scan_dic = {}
unique_scans_df = df.drop_duplicates('scanId')
scanIds = list(unique_scans_df['scanId'])
X_scans = list(unique_scans_df['gpslatitude'])
Y_scans = list(unique_scans_df['gpslongitude'])
Z_scans = list(unique_scans_df['slamFloor'])
for i in range(len(scanIds)):
    scan_dic[scanIds[i]] = len(initial_guess)
    initial_guess.append(X_scans[i])
    initial_guess.append(Y_scans[i])
    initial_guess.append(Z_scans[i])


#initial values x,y,z for APs positions
APs_dic = {}
unique_APs_df = df.drop_duplicates('ssid')
ssid = list(unique_APs_df['ssid'])
X_APs = list(unique_APs_df['gpslatitude'])
Y_APs = list(unique_APs_df['gpslongitude'])
Z_APs = list(unique_APs_df['slamFloor'])
X_APs_true = list(unique_APs_df['wifilatitude/bluetoothlatitude'])
Y_APs_true = list(unique_APs_df['wifilongitude/bluetoothlongitude'])
Z_APs_true = Z_APs
for i in range(len(ssid)):
    APs_dic[ssid[i]] = len(initial_guess)
    initial_guess.append(X_APs[i])
    initial_guess.append(Y_APs[i])
    initial_guess.append(Z_APs[i])


import math

#paramters
ci = -37
yi = 2.5
cfloor = -15
xij = 0

def getFpow(x):
    Fpow = 0
    for scan in scanIds:
        ssid_of_scan = list(df[df['scanId'] == scan]['ssid'])
        rss_of_scan = list(df[df['scanId'] == scan]['rssi'])
        for ssid_name,rss in zip(ssid_of_scan,rss_of_scan):
            dij = math.pow(x[scan_dic[scan]] - x[APs_dic[ssid_name]] , 2) + math.pow(x[scan_dic[scan] + 1] - x[APs_dic[ssid_name] + 1] , 2) + math.pow(x[scan_dic[scan] + 2] - x[APs_dic[ssid_name] + 2] , 2)
            nij = abs(x[scan_dic[scan] + 2] - x[APs_dic[ssid_name] + 2])
            #add epsilon if dij = 0 to resolve log(0) error
            if dij == 0:
                dij = math.pow(2, -30)
            pij = ci - 10 * yi * 0.5 * math.log10(dij) + nij * cfloor + xij          
            pij_ = rss
            Fpow += math.pow(pij - pij_, 2)   
    return Fpow


def getFGPS(x):
    Fgps = 0
    for scan in scanIds:
        gbsValid = list(df[df['scanId'] == scan]['gpsvalid'])[0]
        gbsAccuracy = list(df[df['scanId'] == scan]['gpsaccuracy'])[0]
        gbsX = list(df[df['scanId'] == scan]['gpslatitude'])[0]
        gbsY = list(df[df['scanId'] == scan]['gpslongitude'])[0]
        if(gbsValid == 1):
            dij = math.pow(gbsX - x[scan_dic[scan]] , 2) + math.pow(gbsY - x[scan_dic[scan] + 1] , 2)
            Fgps += (1.0 / (1.0 * gbsAccuracy)) * dij
    return Fgps
        

def getFacc(x):
    Facc = 0
    temp_df = df[['scanId','scantime','scannerId']].copy()
    unique_scannerId = list((temp_df.drop_duplicates('scannerId'))['scannerId'])
    for scannerId in unique_scannerId:
        temp_df = df[df['scannerId'] == scannerId].copy()
        temp_df = temp_df.sort_values('scantime')
        sorted_scans = list(temp_df['scanId'])
        for i in range(0, len(sorted_scans) - 2):
            dx = x[scan_dic[sorted_scans[i]]] - 2*x[scan_dic[sorted_scans[i+1]]] + x[scan_dic[sorted_scans[i+2]]]
            dy = x[scan_dic[sorted_scans[i]] + 1] - 2*x[scan_dic[sorted_scans[i+1]] + 1] + x[scan_dic[sorted_scans[i+2]] + 1]
            dz = x[scan_dic[sorted_scans[i]] + 2] - 2*x[scan_dic[sorted_scans[i+1]] + 2] + x[scan_dic[sorted_scans[i+2]] + 2]
            Facc += dx*dx + dy*dy + dz*dz
    return Facc


def getFDelta(x):
    Fdelta = 0
    temp_df = df[['scanId','scantime','scannerId']].copy()
    unique_scannerId = list((temp_df.drop_duplicates('scannerId'))['scannerId'])
    for scannerId in unique_scannerId:
        temp_df = df[df['scannerId'] == scannerId].copy()
        temp_df = temp_df.sort_values('scantime')
        sorted_scans = list(temp_df['scanId'])
        for i in range(0, len(sorted_scans) - 1):
            z1 = x[scan_dic[sorted_scans[i]] + 2]
            z2 = x[scan_dic[sorted_scans[i+1]] + 2] 
            #floor change
            if z1 != z2:    
                dx = x[scan_dic[sorted_scans[i]]] - x[scan_dic[sorted_scans[i+1]]]
                dy = x[scan_dic[sorted_scans[i]] + 1] - x[scan_dic[sorted_scans[i+1]] + 1]
                Fdelta += dx*dx + dy*dy
    return Fdelta

    
#for Testing and comparing with scan positions
def calcScanError(x):
    error = 0
    for i in range(len(scanIds)):
        dx = X_scans[i] - x[3*i]
        dy = Y_scans[i] - x[3*i+1]
        dz = Z_scans[i] - x[3*i+2]
        error += dx*dx + dy*dy + dz*dz
    print('error in scans positions = ' + str(error))

#for Testing and comparing with APs positions
def calcAPsError(x):
    error = 0
    for i in range(len(ssid)):
        dx = X_APs_true[i] - x[(len(scanIds)+i)*3]
        dy = Y_APs_true[i] - x[(len(scanIds)+i)*3 + 1]
        dz = Z_APs_true[i] - x[(len(scanIds)+i)*3 + 2]
        error += dx*dx + dy*dy + dz*dz
    print('error in APs positions = ' + str(error))


h = [1, 1, 1]   #weight of target functions   
def objectiveFunction(x):
    total = getFpow(x) + h[0]*getFGPS(x) + h[1]*getFacc(x) + h[2]*getFDelta(x)
    print("Still Minimizing " + str(total))
    calcAPsError(x)
    calcScanError(x)
    return total


from scipy.optimize import minimize

#to simulate integer constraints for z = floot values
con1 = {'type':'eq','fun': lambda x : max([x[scan_dic[scanIds[i]] + 2] - int(x[scan_dic[scanIds[i]] + 2]) for i in range(len(scanIds))])}
con2 = {'type':'eq','fun': lambda x : max([x[APs_dic[ssid[i]] + 2] - int(x[APs_dic[ssid[i]] + 2]) for i in range(len(ssid))])}
cons = ([con1, con2])
solution = minimize(objectiveFunction, initial_guess, method='SLSQP', constraints=cons)
x = solution.x

# show final objective
print('Final Objective Value: ' + str(objectiveFunction(x)))

# show final solutions
for i in range(len(scanIds)):
    print('scan#' + str(i+1) + ' : ' + 'x=' + str(x[3*i]) + ' , ' + 'y=' + str(x[3*i+1]) + ' , ' + 'z=' + str(x[3*i+2]))

for i in range(len(ssid)):
    print('ssid#' + str(i+1) + ' : ' + 'x=' + str(x[(len(scanIds)+i)*3]) + ' , ' + 'y=' + str(x[(len(scanIds)+i)*3+1]) + ' , ' + 'z=' + str(x[(len(scanIds)+i)*3+2]))

