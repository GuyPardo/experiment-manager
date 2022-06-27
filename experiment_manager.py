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
    this is a package for a list of Parameter objects
    with some useful methods.
    I am assuming that the user is not going to change attributes of this class once an object is created. TODO: fix this.
    """

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

        if "index" in kwargs.keys():
            self.param_list[kwargs["index"]] = kwargs["value"]



    def get_dict(self):
        d = {}
        for param in self.param_list:
            d[param.name] = param
        return d

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
            print(param)
            if param.is_iterated:
                val = "iterated"
            else:
                val = param.value
            table.rows.append([param.name, val, param.units])
            table.set_style(BeautifulTable.STYLE_NONE)
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


def get_labber_trace(output_config_list: list[Config]):
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
        raise NotImplemented('run method not implemented')

    def one_dimensional_sweep(self, config: Config,  save_to_labber=False):
        """
        execute self.run in a loop on a certain variable parameter
        :param config: a Config object with exactly one iterated Parameters  (and the others are constants)TODO: input verification
        :return: a dict with two entries: 'output_config' --> a list of Config objects with the data,
                    'labber_trace'--> a dict that can be inputted to labber's addEntry method
        """

        variable_param = config.get_iterables()[0]
        result = []
        print(variable_param)
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

    def sweep(self, config, save_to_labber=True):
        # TODO this wokrs but there is something wrong with variable order
        # I think i fixed it.  now the convention is that the last varialbe is the inner-most loop
        # and we reverse the labber step list in stead.
        #

        constant_config = Config(*config.get_constants())
        variable_config = Config(*config.get_iterables())

        # the first parameter is the trace parameter
        tracing_parameter = variable_config.param_list[-1]
        trace_list = variable_config.get_labber_step_list()

        curr_config = deepcopy(config)
        for variable in variable_config.param_list:
            curr_config.set_parameter(name=variable.name, value=0)
        #print(curr_config.param_list)
        test_result = self.run(curr_config)
        log_list = test_result.get_labber_log_list()

        curr_config.set_parameter(name = tracing_parameter.name, value  = tracing_parameter.value)

        #print(log_list)
        #print(trace_list)
        if save_to_labber:
            log_name = lu.get_log_name('test_sweep_new')  # TODO automate naming
            logfile = Labber.createLogFile_ForData(log_name, log_list, trace_list)
            logfile.setComment(str(config.get_metadata_table()))
        # variable_config.param_list.reverse()
        outer_variables = Config(*variable_config.param_list[:-1])  # all but the inner most loop
        print(outer_variables.param_list)
        for vals in iter.product(*outer_variables.get_values()):
            for i, param in enumerate(outer_variables.param_list):
                print(vals)
                curr_config.set_parameter(name=param.name, value=vals[i])
                print(curr_config.param_list)
                result = self.one_dimensional_sweep(curr_config,  save_to_labber=False)

                if save_to_labber:
                    logfile.addEntry(result["labber_trace"])


class TestExperiment(Experiment):

    def run(self, config: Config):
        # TODO : verify that config is constant (first need to implement an is_const method for Config)

        product = 1
        for param in config.param_list:
            product = product * param.value

        vector = np.array([config.x.value, config.y.value, config.z.value, config.w.value])

        output_config = Config(Parameter('product', product),
                               Parameter('vector', vector))
        return output_config


########################################################################################################################
config = Config(Parameter('x', 5, 'a.u.'),
                Parameter('y', [4.5, 3.4, 3, 5], 'a.u.'),
                Parameter('z', 1),
                Parameter('w', [1, 2, 3, 4], 'm'))

print(config.get_metadata_table())

e = TestExperiment()

# result = e.one_dimensional_sweep(config, Parameter('v', np.linspace(0, 10, 10)), save_to_labber=False)

e.sweep(config, save_to_labber=True)
