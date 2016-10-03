"""Does not work with NamedConfig for unknown reason"""

from copy import copy

from decompose_fmri import decompose_ex, decompose_run
from data import data_ing, init_ing
from sacred import Experiment
from sacred.observers import MongoObserver
from sklearn.externals.joblib import Parallel, delayed

compare_ex = Experiment('compare_hcp', ingredients=[decompose_ex])
observer = MongoObserver.create()
compare_ex.observers.append(observer)


@data_ing.config
def config():
    dataset = 'hcp'
    raw = True
    n_subjects = 2000
    test_size = 4


@init_ing.config
def config():
    source = None
    n_components = 70


@decompose_ex.config
def config():
    reduction = 1
    n_epochs = 10
    batch_size = 50
    learning_rate = 0.9
    offset = 0
    AB_agg = 'full'
    G_agg = 'full'
    Dx_agg = 'full'
    alpha = 1e-4
    l1_ratio = 0.9
    n_epochs = 10
    verbose = 200
    n_jobs = 1
    smoothing_fwhm = 3


@compare_ex.config
def config():
    config_updates_list = []
    # Reference
    config_updates_list.append({'G_agg': 'full',
                           'Dx_agg': 'full', 'AB_agg': 'full',
                           'reduction': 1})

# Cannot capture in joblib
def single_run(our_config_updates=None):
    @decompose_ex.capture
    def pre_run_hook(_run):
        _run.info['parent_id'] = compare_ex.observers[0].run_entry['_id']
        _run.info['updated_params'] = our_config_updates

    single_observer = MongoObserver.create()
    decompose_ex.pre_run_hooks = [pre_run_hook]
    decompose_ex.observers = [single_observer]

    config_updates = compare_ex.current_run.config['decompose_fmri'].copy()
    config_updates['seed'] = compare_ex.current_run.config['seed']
    for key, value in our_config_updates.items():
        config_updates[key] = value
    for ingredient in decompose_ex.ingredients:
        path = ingredient.path
        config_updates[path] = {}
        ingredient_config_update = compare_ex.current_run.config[path]
        config_updates[path]['seed'] = compare_ex.current_run.config['seed']
        for key, value in ingredient_config_update.items():
            config_updates[path][key] = value

    decompose_ex.run(config_updates=config_updates)


@compare_ex.automain
def compare_run(config_updates_list, n_jobs):
    Parallel(n_jobs=n_jobs,
             backend='multiprocessing')(
        delayed(single_run)(our_config_updates=our_config_updates)
        for our_config_updates in config_updates_list)