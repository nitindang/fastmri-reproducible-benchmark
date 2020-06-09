import tensorflow as tf
from tqdm import tqdm

from fastmri_recon.models.functional_models.unet import unet
from fastmri_recon.models.subclassed_models.denoisers.dncnn import DnCNN
from fastmri_recon.models.subclassed_models.denoisers.focnet import FocNet, DEFAULT_COMMUNICATION_BETWEEN_SCALES
from fastmri_recon.models.subclassed_models.denoisers.focnet import DEFAULT_N_CONVS_PER_SCALE as default_n_convs_focnet
from fastmri_recon.models.subclassed_models.denoisers.mwcnn import MWCNN, DEFAULT_N_FILTERS_PER_SCALE
from fastmri_recon.models.subclassed_models.denoisers.mwcnn import DEFAULT_N_CONVS_PER_SCALE as default_n_convs_mwcnn


params_per_model = {
    model_name: {} for model_name in 'DnCNN, U-net, MWCNN, FocNet'.split()
}

params_per_model['DnCNN']['big'] = dict(
    n_convs=20,
    n_filters=64,
)
params_per_model['DnCNN']['medium'] = dict(
    n_convs=10,
    n_filters=32,
)
params_per_model['DnCNN']['small'] = dict(
    n_convs=5,
    n_filters=16,
)
params_per_model['DnCNN']['specs'] = dict(
    model=DnCNN,
    output_kwarg='n_outputs',
    res=True,
    n_scales=0,
    extra_kwargs=dict(res=False)
)

params_per_model['U-net']['big'] = dict(
    n_layers=4,
    layers_n_channels=[32, 64, 128, 256],
    layers_n_non_lins=2,
)
params_per_model['U-net']['medium'] = dict(
    n_layers=4,
    layers_n_channels=[16, 32, 64, 128],
    layers_n_non_lins=2,
)
params_per_model['U-net']['small'] = dict(
    n_layers=3,
    layers_n_channels=[16, 32, 64],
    layers_n_non_lins=1,
)
params_per_model['U-net']['specs'] = dict(
    model=unet,
    output_kwarg='n_output_channels',
    res=True,
    n_scales='n_layers',
    extra_kwargs=dict(
        compile=False,
    ),
)

params_per_model['MWCNN']['big'] = dict(
    n_scales=3,
    n_filters_per_scale=DEFAULT_N_FILTERS_PER_SCALE,
    n_convs_per_scale=default_n_convs_mwcnn,
    n_first_convs=3,
    first_conv_n_filters=64,
)
params_per_model['MWCNN']['medium'] = dict(
    n_scales=3,
    n_filters_per_scale=[64, 128, 256],
    n_convs_per_scale=default_n_convs_mwcnn,
    n_first_convs=2,
    first_conv_n_filters=32,
)
params_per_model['MWCNN']['small'] = dict(
    n_scales=2,
    n_filters_per_scale=[32, 64],
    n_convs_per_scale=[2, 2],
    n_first_convs=2,
    first_conv_n_filters=32,
)
params_per_model['MWCNN']['specs'] = dict(
    model=MWCNN,
    output_kwarg='n_outputs',
    res=True,
    n_scales='n_scales',
    extra_kwargs=dict(res=False),
)

params_per_model['FocNet']['big'] = dict(
    n_scales=4,
    n_filters=128,
    n_convs_per_scale=default_n_convs_focnet,
    communications_between_scales=DEFAULT_COMMUNICATION_BETWEEN_SCALES,
)
params_per_model['FocNet']['medium'] = dict(
    n_scales=4,
    n_filters=64,
    n_convs_per_scale=default_n_convs_focnet,
    communications_between_scales=DEFAULT_COMMUNICATION_BETWEEN_SCALES,
)
params_per_model['FocNet']['small'] = dict(
    n_scales=3,
    n_filters=32,
    n_convs_per_scale=default_n_convs_focnet[:-1],
    communications_between_scales=DEFAULT_COMMUNICATION_BETWEEN_SCALES[:-1],
)
params_per_model['FocNet']['specs'] = dict(
    model=FocNet,
    output_kwarg='n_outputs',
    res=False,
    n_scales='n_scales',
)


def get_models(n_primal):
    for model_name, params in tqdm(params_per_model.items(), 'Models'):
        model_specs = params['specs']
        model_fun = model_specs['model']
        n_scales_kwarg = model_specs['n_scales']
        res = model_specs['res']
        extra_kwargs = model_specs['extra_kwargs']
        extra_kwargs.update({model_specs['output_kwarg']: 2*n_primal})
        if model_name == 'U-net':
            extra_kwargs.update({'input_size': (None, None, 2*(n_primal + 1))})
        for model_size, param_values in tqdm(params.items(), model_name):
            if model_size == 'specs':
                continue
            print(model_name, model_size)
            kwargs = param_values
            kwargs.update(extra_kwargs)
            if n_scales_kwarg == 0:
                n_scales = 0
            else:
                n_scales = kwargs[n_scales_kwarg]
            model = model_fun(**kwargs)
            model(tf.zeros([1, 32, 32, 2*(n_primal + 1)]))
            yield model_name, model_size, model, n_scales, res
