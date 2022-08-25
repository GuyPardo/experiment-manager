import importlib
import qiskit_utils as qu
import experiment_manager
importlib.reload(qu)
importlib.reload(experiment_manager)
from experiment_manager import *


def read_qiskit_result(result, label="density_matrix"):
    """
    read a qiskit result object with either density matrices or counts or both

    :param result:

    :param label:

     :return:
    a dict with keys "density_matrices" and "counts" and values that are lists of density_matrices objects and of
    count dicts respectively
    """
    density_mats = []
    for i in range(len(result.results)):
        try:
            density_mats.append(result.data(i)[label])
        except:
            density_mats.append(None)

    try:
        counts = result.get_counts()
    except:
        counts = None

    return dict(density_matrices=density_mats, counts=counts)

class QiskitExperimentDensityMat(AsyncExperiment):
    """
    an abstract class to be used as a parent for user-defined classes.
    an experiment done on qiskit simulator where each run is the execution of a single circuit, saving the resulting
    density matrix, and then calculating some observable(s) from it.
    """

    def __init__(self):
        super().__init__()
        self.sweep_configs = None
        self.sweep_jobs = None

    def get_circ(self, config: Config):
        # to be implemented in child class. sohuld return a qiskit.QuantmCircuit object
        raise NotImplemented('get_circ method not implemented')

    def run(self, config: Config):
        """
        runs the ciscuit :param config:Config with constant (not iterated) Parameters that are used in self.get_circ(
        ), and a parameter called backend with a qiskit backend

        :return: a qiskit job.
        """
        #TODO add calibration
        if config.skip_simulation.value:
            return
        if 'shots' in config.get_names_list():
            shots = config.shots.value
        else:
            shots = 1024
        print("shots")
        print(shots)
        job = config.backend.value.run(self.get_circ(config),shots=shots)
        return job

    def wait_result(self, job):
        """
            envelope for qiskit job.result()
        """
        return job.result()

    def one_dimensional_job(self, config: Config):
        """
        returns a qiskit job for calculating self.get_circ in a 1d loop. and stores it in self._async_results
        :param config:Config with exactly one iterated parameter
        :return:  a qiskit job
        """


        if config.skip_simulation.value:
            return
        if 'shots' in config.get_names_list():
            shots = config.shots.value
        else:
            shots = 1024


        # verify input:
        if len(config.get_iterables()) != 1:
            raise ValueError("config must have exactly one iterable Parameter")
        variable_param = config.get_iterables()[0] # config.get_iterables() is a list of length 1


        tic()


        circs = []
        for val in variable_param.value:
            current_param = Parameter(variable_param.name, val, units=variable_param.units)
            current_config = deepcopy(config)
            current_config.set_parameter(name=current_param.name, value=current_param.value)
            # print(current_config.param_list)
            circs.append(self.get_circ(current_config))

        # # readout calibration:
        # if config.calib_shots.value>0:
        #     n_qubits = max_qubit_number(circs)
        #     calib_job, state_labels = run_calib(config.backend.value, n_qubits,)

        job = config.backend.value.run(circs,shots=shots)
        self._async_results.append(job)
        print('1D job sent in:')
        toc()
        print('')
        return job

    def sweep(self, config):
        """
        evaluate self.get_circ() in an N dimensional loop.
        and store each inner loop 1d job in self._async_results, and additionally in the list self.sweep_jobs.
        each 1d loop config in the N-d loop is copied and stored in the list self.sweep_config
        :param config:Config with some iterated Parameters (and possibly some constant)
        """
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

        counter = 1

        num_jobs = outer_variables.get_total_iteration_count()

        for indices, vals in enumerated_product(*outer_variables.get_values()): #TODO this should be a function or a method of Config
            # update parameters to current values:
            for i, param in enumerate(outer_variables.param_list):
                curr_config.set_parameter(name=param.name, value=vals[i])

            print(f"running job {counter} out of {num_jobs}...")
            # do 1D sweep on the tracing parameter:
            print('current configuration:')
            for param in outer_variables.param_list:
                print(getattr(curr_config, param.name))

            job = self.one_dimensional_job(curr_config)
            self.sweep_jobs.append(job)
            self.sweep_configs.append(deepcopy(curr_config))
            counter = counter + 1

    def get_observables(self, config: Config, density_matrix, counts):
        raise NotImplementedError()
        # should return an output Config object
        pass

    def get_observables_1D(self, config, job):
        """
        performs self.get_observables in a 1d loop.

        :param config: Config with exacly one iterated Parameter)

        :param job: a qiskit (simulation) job that came from a list of circuits, each one returns a single density matrix

        :return: a dict with two entries: "output_config"-> a list of Config objects, "labbe_trace"--> a dict
        according to Labber' trace requirements
        """
        # returns a dict with output config list, and labber trace

        # input verification
        if not len(config.get_iterables()) == 1:
            raise ValueError("config must have exactly one iterable Parameter")

        variable_param = config.get_iterables()[0]

        result = self.wait_result(job)

        results_dict = read_qiskit_result(result)

        output_config = []
        config_scalar = deepcopy(config)
        for index in range(len(result.results)):
            density_matrix = results_dict["density_matrices"][index]
            counts = results_dict["counts"][index]
            config_scalar.set_parameter(name=variable_param.name, value=variable_param.value[index])
            output_config.append(self.get_observables(config_scalar, density_matrix, counts))

        labber_trace = get_labber_trace(output_config)

        return dict(output_config=output_config, labber_trace=labber_trace)

    def labber_read(self, config, labber_log_name=None):
        """
        creates a labber log file for nd loop according to config
        adds entries from self.sweep_jobs using self.get_observables_1d for each entry (1d trace)
        :param config: Config
        :param labber_log_name:str ,optional, otherwise use automatic naming scheme
        """

        variable_config = Config(*config.get_iterables())  # a Config with only the variables

        # the last variable is the trace parameter (inner-most loop):
        tracing_parameter = variable_config.param_list[-1]

        # get labber step list:
        step_list = variable_config.get_labber_step_list()

        # get observables from one iteration of first job: #TODO: check that a job exists
        single_run_rho = read_qiskit_result(self.wait_result(self.sweep_jobs[0]))["density_matrices"][0]
        single_run_counts = read_qiskit_result(self.wait_result(self.sweep_jobs[0]))["counts"][0]
        single_run_config = deepcopy(config)
        for var in variable_config.param_list:
            single_run_config.set_parameter(name=var.name, value=var.value[0])

        single_run_observables = self.get_observables(single_run_config, single_run_rho, single_run_counts)

        # get labber log list
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
        labber_tags = [type(self).__name__]
        for param in variable_config.param_list:
            labber_tags.append(f'loop on {[param.name]}')

        logfile.setTags(labber_tags)
        for index, job in enumerate(self.sweep_jobs):
            print(f'reading result from job {index + 1} out of {len(self.sweep_jobs)}...')
            tic()
            result = self.get_observables_1D(self.sweep_configs[index], job)
            print('1D observables read in:')
            toc()
            print('')
            logfile.addEntry(result["labber_trace"])

####################################################################
