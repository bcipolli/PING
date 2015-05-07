"""
Build similarity matrices for cortical area (left, right) and asymmetry
"""
import copy
import numpy as np
import scipy
from matplotlib import pyplot as plt

from ping import load_PING_data, which_hemi
from export_measures import get_all_derived_data


def get_all_data(prefix):
    all_data = get_all_derived_data(prefix=prefix)
    ping_data = copy.deepcopy(load_PING_data())

    for key in copy.deepcopy(ping_data.keys()):
        if not np.any([key.startswith(p) for p in prefix]):
            del ping_data[key]
    all_data.update(ping_data)
    return all_data


def get_good_keys(all_data, filter_fn):
    good_keys = []
    for key in all_data.keys():
        if not filter_fn(key):
            continue  # Bad key
        elif np.isnan(all_data[key]).sum() == len(all_data[key]):
            continue  # All data is nan!
        elif all_data[key][np.logical_not(np.isnan(all_data[key]))].std() == 0:
            continue  # Data without variation
        elif '_Vent' in key:
            continue  # Remove ventricles
        good_keys.append(key)
    return sorted(good_keys)


def build_similarity_matrix(all_data, good_keys=None, filter_fn=None, standardize=False):
    """
    """
    # Filter keys
    if not good_keys:
        good_keys = sorted(get_good_keys(all_data, filter_fn))

    # Convert data dictionary into a data matrix
    data_mat = []
    for key in good_keys:
        data_mat.append(all_data[key])
    data_mat = np.asarray(data_mat)

    # Remove subjects with any nan, and standardize values
    bad_idx = np.isnan(data_mat.sum(axis=0))
    good_idx = np.logical_not(bad_idx)
    data_mat = data_mat[:, good_idx]
    if standardize:
        data_mat = scipy.stats.mstats.zscore(data_mat, axis=1)
        assert np.all(np.abs(data_mat.sum(axis=1)) < 1E-4)
    print "Found %d keys; removed %d subjects w/ missing data." % (
        len(data_mat), bad_idx.sum())

    # Compute a correlation matrix
    dist_mat = scipy.spatial.distance.pdist(data_mat, 'correlation')
    corr_mat = 1 - dist_mat
    assert not np.isnan(corr_mat.sum())

    return corr_mat, good_keys


def compare_similarity_matrices(vec1, vec2):

    # Make sure both similarity matrices are in vector form.
    if len(vec1.shape) == 2:
        vec1 = scipy.spatial.distance.squareform(vec1, 'tovector')
    if len(vec2.shape) == 2:
        vec2 = scipy.spatial.distance.squareform(vec2, 'tovector')

    # Now compare.
    return scipy.stats.pearsonr(vec1, vec2)


def compare_all_similarity_matrices(prefix=None):
    prefix = prefix or ['MRI_cort_area', 'MRI_cort_thick',
                        'MRI_subcort_vol', 'DTI_fiber_vol']

    filt_fns = {
        'ai': (lambda key: key.endswith('_AI')),
        'left': (lambda key: which_hemi(key) == 'lh'),
        'right': (lambda key: which_hemi(key) == 'rh')}

    sim_dict = dict()
    key_dict = dict()
    comp_dict = dict()
    for p in prefix:
        sim_dict[p], key_dict[p] = dict(), dict()

        # 1. Compute similarity matrices
        for mat_type, filt_fn in filt_fns.items():
            print "Computing similarity matrix for %s, %s" % (mat_type, p)

            all_data = get_all_data(prefix=p)
            fn = lambda key: filt_fn(key) and key.startswith(p)
            sim_mat, good_keys = build_similarity_matrix(all_data,
                                                         filter_fn=fn,
                                                         standardize=True)
            sim_dict[p][mat_type] = sim_mat
            key_dict[p][mat_type] = good_keys

        # 2. Compare similarity matrices.
        compare_keys = sim_dict[p].keys()
        n_keys = len(compare_keys)
        mat_compare_mat = np.zeros((n_keys * (n_keys - 1) / 2,))
        mat_idx = 0
        for ki, key1 in enumerate(compare_keys):
            for kj in range(ki + 1, n_keys):
                key2 = compare_keys[kj]
                r, pval = compare_similarity_matrices(sim_dict[p][key1],
                                                      sim_dict[p][key2])
                print "%s vs. %s: r**2=%.3f (p=%.3f)" % (
                    key1, key2, r**2, pval)
                mat_compare_mat[mat_idx] = r
                mat_idx += 1

        # Visualize similarity matrices
        fh = plt.figure(figsize=(16, 6))
        for ki, key in enumerate(compare_keys):
            ax = fh.add_subplot(1, n_keys, ki)
            full_mat = scipy.spatial.distance.squareform(sim_dict[p][key])
            full_mat += np.eye(full_mat.shape[0])
            ax.imshow(full_mat, vmin=-1, vmax=1)
            ax.set_title('%s: %s' % (p, key))
        plt.show()
    import pdb; pdb.set_trace()


if __name__ == '__main__':
    compare_all_similarity_matrices()