# Author: Arthur Mensch
# License: BSD
# Adapted from nilearn example
import itertools
import os
import time
from os.path import expanduser, join

from nilearn.datasets import fetch_atlas_smith_2009
from nilearn.image import index_img
from nilearn.plotting import plot_stat_map
from sklearn.externals.joblib import Parallel, delayed

from modl.datasets.hcp import get_hcp_data
from modl.spca_fmri import SpcaFmri

trace_folder = expanduser('~/output/modl/hcp')

def main():
    # Apply our decomposition estimator with reduction
    n_components = 70
    n_jobs = 1
    raw = True
    init = True

    mask, func_filenames = get_hcp_data(raw=raw)

    reduction_list = [1, 2, 4, 8, 12]
    alpha_list = [1e-2, 1e-3, 1e-4]

    Parallel(n_jobs=n_jobs, verbose=10)(delayed(run)(idx, reduction, alpha,
                                                     mask, raw, n_components,
                                                     init, func_filenames) for
                                        idx, (reduction, alpha)
                                        in enumerate(
        itertools.product(reduction_list, alpha_list)))


def run(idx, reduction, alpha, mask, raw, n_components, init, func_filenames):
    output_dir = join(trace_folder, 'experiment_%i' % idx)
    try:
        os.makedirs(output_dir)
    except OSError:
        pass
    dict_fact = SpcaFmri(mask=mask,
                         smoothing_fwhm=3,
                         batch_size=40,
                         shelve=not raw,
                         n_components=n_components,
                         dict_init=fetch_atlas_smith_2009().rsn70 if
                         init else None,
                         reduction=reduction,
                         alpha=alpha,
                         random_state=0,
                         n_epochs=2,
                         l1_ratio=0.5,
                         backend='c',
                         memory=expanduser("~/nilearn_cache"), memory_level=2,
                         verbose=5,
                         n_jobs=1,
                         trace_folder=output_dir
                         )

    print('[Example] Learning maps')
    t0 = time.time()
    dict_fact.fit(func_filenames, raw=raw)
    t1 = time.time() - t0
    print('[Example] Dumping results')
    # Decomposition estimator embeds their own masker
    masker = dict_fact.masker_
    components_img = masker.inverse_transform(dict_fact.components_)
    components_img.to_filename(join(output_dir, 'components_final.nii.gz'))
    print('[Example] Run in %.2f s' % t1)
    # Show components from both methods using 4D plotting tools
    import matplotlib.pyplot as plt
    from nilearn.plotting import plot_prob_atlas, show

    print('[Example] Displaying')
    fig, axes = plt.subplots(2, 1)
    plot_prob_atlas(components_img, view_type="filled_contours",
                    axes=axes[0])
    plot_stat_map(index_img(components_img, 0),
                  axes=axes[1],
                  colorbar=False,
                  threshold=0)
    plt.savefig(join(output_dir, 'components.pdf'))
    show()


if __name__ == '__main__':
    main()
