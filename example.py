
class TestExperiment(Experiment):
    def run(self, config: Config):
        # TODO : verify that config is constant (first need to implement an is_const() method for Config)

        product = 1
        for param in config.param_list:
            product = product * param.value

        # vector = np.array([config.x.value, config.y.value, config.z.value, config.w.value])
        vector = np.array(config.get_values())

        output_config = Config(Parameter('product', product),
                               Parameter('vector', vector))
        return output_config


########################################################################################################################
config = Config(Parameter('x', 5, 'a.u.'),
                Parameter('y', [4.5, 3.4, 3, 5], 'a.u.'),
                Parameter('z', 1),
                Parameter('w', 3, 'm'))

print(config.get_metadata_table())

e = TestExperiment()

# result = e.one_dimensional_sweep(config, Parameter('v', np.linspace(0, 10, 10)), save_to_labber=False)

e.sweep(config, save_to_labber=True)