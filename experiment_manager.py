import os
import sys
import typing
from typing import Iterable
from copy import deepcopy
import numpy as np
from beautifultable import BeautifulTable
from dataclasses import dataclass
import Labber
import itertools as iter
from general_utils import enumerated_product

sys.path.append(os.path.abspath(r"G:\My Drive\guy PHD folder\util"))
import Labber_util as lu


@dataclass
class Parameter:  # TODO - I realized this class can be used for output data as well. consider change the name
    """
    a physical parameter with name, value, units.
    """
    name: str
    value: typing.Any
    units: str = 'n.u.'
    is_iterated = None

    def __init__(self, name: str, value, units='n.u.', is_iterated=None):
        """
        creates a Parameter object
        :param name: str -  name of the parameter
        :param value: any type -  value of the parameter
        :param units: str  - physical units of the parameter, by default 'n.u.' = no units, which is not exactly the same thing as a.u. (arbitrary units).
        :param is_iterated: bool. detemines whether the value is constant or iterated. if iterated, then value should be an Iterable.
                                    by default self.is_iterated is defined according to whether value is an Iterable, but thie can be changed if you want, for example, a constant value that is a list.
        """

        self.name = name
        self.value = value
        self.units = units

        if is_iterated == None:
            if isinstance(self.value, Iterable):
                self.is_iterated = True
            else:
                self.is_iterated = False
        else:
            self.is_iterated = is_iterated


class Config:  # TODO - I realized this class can be used for output data as well. consider changing the name
    """
    this is an envelope-class for a list of Parameter objects with some useful methods.
    """

    # TODO easier access to values? right now one has to do config.param_name.value
    def __init__(self, *param_list):
        """
        creates a Config object from a list of Parameter objects
        :param param_list: a list of Parameter objects
        """
        self.param_list = list(param_list)
        for param in self.param_list:
            setattr(self, param.name, param)

    def add_parameter(self, param: Parameter):
        self.param_list.append(param)
        setattr(self, param.name, param)

    def set_parameter(self, **kwargs):

        if "name" in kwargs.keys():
            getattr(self, kwargs["name"]).value = kwargs["value"]
            if "is_iterated" in kwargs.keys():
                getattr(self, kwargs["name"]).is_iterated = kwargs["is_iterated"]
            else:
                getattr(self, kwargs["name"]).is_iterated = isinstance(kwargs["value"], Iterable)

        if "index" in kwargs.keys():
            self.param_list[kwargs["index"]] = kwargs["value"]
            if "is_iterated" in kwargs.keys():
                self.param_list[kwargs["index"]].is_iterated = kwargs["is_iterated"]
            else:
                self.param_list[kwargs["index"]].is_iterated = isinstance(kwargs["value"], Iterable)

    def get_dict(self):
        d = {}
        for param in self.param_list:
            d[param.name] = param
        return d

    #TODO
    def get_dataclass_object_with_values(self):
        pass



    def get_values(self):
        values = []
        for param in self.param_list:
            values.append(param.value)
        return values

    def get_iterables(self):
        iter_list = []
        for param in self.param_list:
            if param.is_iterated:
                iter_list.append(param)
        return iter_list

    def get_constants(self):
        const_list = []
        for param in self.param_list:
            if not param.is_iterated:
                const_list.append(param)
        return const_list

    def get_metadata_table(self):
        table = BeautifulTable()
        table.columns.header = ["name", "value", "units"]
        for param in self.param_list:
            #print(param)
            if param.is_iterated:
                val = "iterated"
            else:
                val = param.value
            table.rows.append([param.name, val, param.units])
            table.set_style(BeautifulTable.STYLE_NONE)
            table.precision=20
        return table

    def is_constant(self):
        pass  # TODO - implement

    def get_labber_step_list(self):
        iterated_config = Config(*self.get_iterables())  # build a new config with just the iterables of self
        steplist = []
        for param in iterated_config.param_list:
            steplist.append(dict(name=param.name, unit=param.units, values=param.value))
        steplist.reverse()
        return steplist

    def get_labber_log_list(self):
        # thinking about the Config object as an output data
        loglist = []
        for param in self.param_list:
            loglist.append(dict(name=param.name, unit=param.units, vector=param.is_iterated))
        return loglist


def get_labber_trace(output_config_list):
    labber_dict = {}

    for param in output_config_list[0].param_list:
        labber_dict[param.name] = []

    for c in output_config_list:
        for param in c.param_list:
            labber_dict[param.name].append(param.value)
    for param in output_config_list[0].param_list:
        if not param.is_iterated:
            labber_dict[param.name] = np.array(labber_dict[param.name])
    return labber_dict


class Experiment:
    """
    a procedure (a computation or physical experiment with some controlled hardware) that you might like to run many
    times with different configurations.
    """

    def __init__(self):
        pass

    def run(self, config: Config):
        # to be implemented in child classes
        raise NotImplemented('run method not implemented')

    def one_dimensional_sweep(self, config: Config, save_to_labber=False):
        """
        execute self.run in a loop on a certain variable parameter
        :param config: a Config object with exactly one iterated Parameters  (and the others are constants)TODO: input verification
        :param save_to_labber:bool: whether to save the data in a new labber log
        :return: a dict with two entries: 'output_config' --> a list of Config objects with the data,
                    'labber_trace'--> a dict that can be inputted to labber's addEntry method
        """

        variable_param = config.get_iterables()[0]
        result = []
        for val in variable_param.value:
            current_param = Parameter(variable_param.name, val, units=variable_param.units)
            current_config = deepcopy(config)
            current_config.set_parameter(name=current_param.name, value=current_param.value)
            result.append(self.run(current_config))

        labber_trace = get_labber_trace(result)
        if save_to_labber:
            log_name = lu.get_log_name('test_exp_new')  # TODO: automatic naming
            logfile = Labber.createLogFile_ForData(log_name, result[0].get_labber_log_list(),
                                                   Config(variable_param).get_labber_step_list())
            logfile.addEntry(get_labber_trace(result))
            logfile.setComment(str(config.get_metadata_table()))
        return dict(output_config=result, labber_trace=labber_trace)

    def sweep(self, config, save_to_labber=True, labber_log_name=None):
        """
        executes self.run(...) in an N-dimneional loop with N equals the number of iterated Parameters ("variables") in
         config.
        :param config: a Config object with some iterated Parameters ("varialbes") and some non-iterated ones ("constants)
        :param save_to_labber: bool.
        :param labber_log_name: str, optional. if not supplied use automatic naming scheme #TODO : describe here the scheme
        :return: none currently. for now I want to use the save_to_labber feature anyway.
        TODO: save the data in python as well. his will be more important for asynchronic experiments
        """

        variable_config = Config(*config.get_iterables())  # a Config with only the variables

        # the last variable is the trace parameter (inner-most loop):
        tracing_parameter = variable_config.param_list[-1]

        # get labber step list:
        step_list = variable_config.get_labber_step_list()


        # create a constant configuration for test run
        curr_config = deepcopy(config)
        for variable in variable_config.param_list:
            curr_config.set_parameter(name=variable.name, value=0)

        # test run
        test_result = self.run(curr_config)

        # get labber log list
        log_list = test_result.get_labber_log_list()


        print("setp list")
        print(step_list)
        print("log list")
        print(log_list)

        # add back the tracing parameter as an iterated Parameter
        curr_config.set_parameter(name=tracing_parameter.name, value=tracing_parameter.value)

        if save_to_labber:

            # automatic naming:
            if labber_log_name:
                log_name = labber_log_name
            else:
                class_name = type(self).__name__
                log_name = f'{class_name}_sweep'

            log_name = lu.get_log_name(log_name) # adds automatic numbering to avoid overwrite

            # create log file
            logfile = Labber.createLogFile_ForData(log_name, log_list, step_list)

            # add comment w. metadata
            logfile.setComment(str(config.get_metadata_table()))

        outer_variables = Config(*variable_config.param_list[:-1])  # "outer" means all but the inner-most loop

        # N-dimensional loop with itertools.product: # (actually N-1 )
        for indices, vals in enumerated_product(*outer_variables.get_values()):
            # update parameters to current values:
            for i, param in enumerate(outer_variables.param_list):
                curr_config.set_parameter(name=param.name, value=vals[i])

            # do 1D sweep on the tracing parameter:
            result = self.one_dimensional_sweep(curr_config, save_to_labber=False)

            # save to labber
            print("trace")
            print(result["labber_trace"])
            if save_to_labber:
                logfile.addEntry(result["labber_trace"])

            # save in python: #TODO

class AsyncExperiment(Experiment):

    def __init__(self):
        self._async_results = []
        self.results = []

    @classmethod
    def wait_result(async_result):
        pass


    def _run(self, args, **kwargs):
        self._async_results.append(self.run(*args, **kwargs))

    def wait_results(self):
        for result in self._async_results:
            self.results.append(self.wait_result(result))






class QiskitExperimentDensityMat(AsyncExperiment):
    """
    a qiskit experiment docstring
    """


    # let's agrQiskitExperimentDensityMatee that we always work with lists of circuits..
    def get_circ(self, config:Config):
        #to be implemented in child class
        raise  NotImplemented('get_circ method not implemented')

    def run(self, config: Config):
        job = config.backend.value.run(self.get_circ(config))
        return job


    def wait_result(self, job):
        # return a list of density matrix objects
        result = []
        for i in range(len(job.result().results)):
            result.append(job.result().data(i)["density_matrix"])
        return result

    def one_dimensional_job(self, config: Config):
        variable_param = config.get_iterables()[0]
        circs = []
        for val in variable_param.value:
            current_param = Parameter(variable_param.name, val, units=variable_param.units)
            current_config = deepcopy(config)
            current_config.set_parameter(name=current_param.name, value=current_param.value)
            # print(current_config.param_list)
            circs.append(self.get_circ(current_config))

        job = config.backend.value.run(circs)
        self._async_results.append(job)
        return job

    def sweep(self, config):
        self.sweep_jobs = []
        self.sweep_configs = []
        variable_config = Config(*config.get_iterables())  # a Config with only the variables

        # the last variable is the trace parameter (inner-most loop):
        tracing_parameter = variable_config.param_list[-1]

        curr_config = deepcopy(config)
        for variable in variable_config.param_list[:-1]:
            curr_config.set_parameter(name=variable.name, value=0)

        outer_variables = Config(*variable_config.param_list[:-1])  # "outer" means all but the inner-most loop
        # N-dimensional loop with itertools.product: # (actually N-1 )


        for indices, vals in enumerated_product(*outer_variables.get_values()):
            # update parameters to current values:
            for i, param in enumerate(outer_variables.param_list):
                curr_config.set_parameter(name=param.name, value=vals[i])

            print("running...")
            # do 1D sweep on the tracing parameter:
            print(curr_config.param_list) #TODO only print sweep parameters
            job = self.one_dimensional_job(curr_config)
            self.sweep_jobs.append(job)
            self.sweep_configs.append(deepcopy(curr_config))

    def get_observables(self,config:Config, density_matrix):
        # to be implemented in child class
        # should return an output Config object
        pass

    def get_observables_1D(self,config, job):
        #returns a dict with output config list, and labber trace

        # input verification
        if not len(config.get_iterables()) == 1:
            raise ValueError("config must have exactly one iterable Parameter")

        variable_param = config.get_iterables()[0]

        density_matrices = self.wait_result(job)
        output_config = []
        config_scalar = deepcopy(config)
        for index, density_mat in enumerate(density_matrices):
            config_scalar.set_parameter(name=variable_param.name, value=variable_param.value[index])
            output_config.append(self.get_observables(config_scalar, density_mat))

        labber_trace = get_labber_trace(output_config)

        return dict(output_config=output_config, labber_trace=labber_trace)


    def labber_read(self,config, labber_log_name=None):
        # create labber log file for nd loop according to config
        # add entries from self.sweep_jobs using self.get_observables and self.wait_reaults
        variable_config = Config(*config.get_iterables())  # a Config with only the variables

        # the last variable is the trace parameter (inner-most loop):
        tracing_parameter = variable_config.param_list[-1]

        # get labber step list:
        step_list = variable_config.get_labber_step_list()

        # get observables from one iteration of first job: #TODO: check that a job exists
        single_run_rho = self.wait_result(self.sweep_jobs[0])[0]
        single_run_config = deepcopy(config)
        for var in variable_config.param_list:
            single_run_config.set_parameter(name=var.name, value=var.value[0])

        single_run_observables = self.get_observables(single_run_config, single_run_rho)

        #get labber log list
        log_list = single_run_observables.get_labber_log_list()

        # build labber logfile
        # automatic naming:
        if labber_log_name:
            log_name = labber_log_name
        else:
            class_name = type(self).__name__
            log_name = f'{class_name}_sweep'

        log_name = lu.get_log_name(log_name)  # adds automatic numbering to avoid overwrite
        # create log file
        logfile = Labber.createLogFile_ForData(log_name, log_list, step_list)
        # add comment w. metadata
        logfile.setComment(str(config.get_metadata_table()))

        # print("labber log")
        # print(log_list)
        # print("labber step")
        # print(step_list)

        for index, job in enumerate(self.sweep_jobs):
            print(self.sweep_configs[index].param_list) #TODO only pring sweep parameters
            result = self.get_observables_1D(self.sweep_configs[index], job)
            labber_trace = result["labber_trace"]
            #
            # print("labber trace")
            # print(labber_trace)
            logfile.addEntry(labber_trace)



















####################################################################

