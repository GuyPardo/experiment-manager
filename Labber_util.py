# -*- coding: utf-8 -*-
"""
Created on Mon Jun 20 15:00:15 2022

@author: owner
"""

import Labber as lb
import os
def log_exists(log_name):
    #create a temporary log:
    lLog = [dict(name='name', vector = False)]
    templog = lb.createLogFile_ForData('temp', lLog)
    path = templog.getFilePath(None)
    folder = os.path.dirname(path)
    log_name = f'{log_name}.hdf5'
    new_file_path = os.path.join(folder, log_name)
    return(os.path.exists(new_file_path))


def get_log_name(log_name):
    i=1
    log_name_temp = log_name
    while log_exists(log_name_temp):
        log_name_temp = f'{log_name}__{i}'
        i=i+1
    return log_name_temp    

def open_log(log_name):
    lLog = [dict(name='name', vector = False)]
    templog = lb.createLogFile_ForData('temp', lLog)
    path = templog.getFilePath(None)
    folder = os.path.dirname(path)
    log_name = f'{log_name}.hdf5'
    new_file_path = os.path.join(folder, log_name)
    return lb.LogFile(new_file_path)

