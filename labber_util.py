# -*- coding: utf-8 -*-
"""
Created on Mon Jun 20 15:00:15 2022

@author: Guy
"""

import Labber as lb
import os

def get_current_Labber_path():
    """
    Labber has a database structure based on dates and it automatically writes new logfiles into the folder of today/
    however here we want to be absolutely sure that we get the correct folder so we find it by creating a fictitious
    temporary  logfile called temp.  and get its path. not very elegant but it works.

    :return:str: path to the current Labber database folder
    """
    # create a temporary log:
    lLog = [dict(name='name', vector=False)]
    templog = lb.createLogFile_ForData('temp', lLog)
    % get its path
    templog_path = templog.getFilePath(None)

    #return just the folder
    return os.path.dirname(templog_path)

def get_logfile_full_path(log_name):
    """
    returns the full path of a Labber logfile with name log_name in the current Labber database folder. note that the
    logfile might be a nonexisting one and that's ok. the function will just return a full path pf the form f'{Labber
    folder}/{log_name}.hdf5' where labber folder is the current Labber database folder, and that can be used to create
    a new logfile

    :param log_name: str
    :return: str: full path: '{Labber folder}/{log_name}.hdf5'
    """
    log_name = f'{log_name}.hdf5'
    return os.path.join(get_current_Labber_path(), log_name)

def log_exists(log_name):
    """
    checks whether a Labber logfile with name log_name exists in the current Labber database directory.
    :param log_name:str
    :return: bool
    """
    return (os.path.exists(get_logfile_full_path(log_name)))


def get_log_name(log_name):
    """
    if log_name does not exist in the current Labber database directory, returns log_name
    if it does exist, adds a number at the end as needed to avoid overwrite.
    example: if the current Labber folder has the following files:
    my_experiment.hdf5
    my_experiment__1.hdf5
    my_experiment__2.hdf5
    my_experiment__3.hdf5

    then  get_log_name('my_experiment') = 'my_experiment__4'
    :param log_name:str desired name for labber logfile
    :return:str the same name with additional numbers at the end as necessary to avoid overwrite.
    """
    LOG_NAME_FORMAT = '{log_name}__{integer_suffix}'
    counter = 1
    log_name_temp = log_name
    while log_exists(log_name_temp):
        log_name_temp = LOG_NAME_FORMAT.format(log_name=log_name, integer_suffix=counter)
        counter = counter + 1
    return log_name_temp


def open_log(log_name):
    """
    returns a Labber.logfile object corresponding to the data file indicated by log_name from the current Labber
    database folder
    :param log_name: a name of a log file that exists in the current database
    :return:Labber.logfile object
    """
    return lb.LogFile(get_logfile_full_path(log_name))
