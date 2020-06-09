import os

import tensorflow as tf

from fastmri_recon.config import *
from fastmri_recon.data.datasets.multicoil.fastmri_pyfunc import train_masked_kspace_dataset_from_indexable as multicoil_dataset
from fastmri_recon.data.datasets.fastmri_pyfunc import train_masked_kspace_dataset_from_indexable as singlecoil_dataset
from fastmri_recon.models.subclassed_models.xpdnet import XPDNet
from fastmri_recon.models.subclassed_models.denoisers.proposed_params import build_model_from_specs


def evaluate_xpdnet(
        model,
        run_id,
        multicoil=True,
        n_epochs=200,
        contrast=None,
        af=4,
        n_iter=10,
        res=True,
        n_scales=0,
        n_primal=5,
        refine_smaps=False,
        n_samples=None,
        cuda_visible_devices='0123',
    ):
    if multicoil:
        val_path = f'{FASTMRI_DATA_DIR}multicoil_val/'
    else:
        val_path = f'{FASTMRI_DATA_DIR}singlecoil_val/'

    os.environ["CUDA_VISIBLE_DEVICES"] = ','.join(cuda_visible_devices)
    af = int(af)

    run_params = {
        'n_primal': n_primal,
        'multicoil': multicoil,
        'n_scales': n_scales,
        'n_iter': n_iter,
        'refine_smaps': refine_smaps,
        'res': res,
    }

    if multicoil:
        dataset = multicoil_dataset
        kwargs = {'parallel': False}
    else:
        dataset = singlecoil_dataset
        kwargs = {}
    val_set = dataset(
        val_path,
        AF=af,
        contrast=contrast,
        inner_slices=None,
        rand=False,
        scale_factor=1e6,
        **kwargs,
    )
    if n_samples is not None:
        val_set = val_set.take(n_samples)

    if multicoil:
        kspace_size = [1, 15, 640, 372]
    else:
        kspace_size = [1, 640, 372]
    if isinstance(model, tuple):
        model = build_model_from_specs(*model)
    model = XPDNet(model, **run_params)
    inputs = [
        tf.zeros(kspace_size + [1], dtype=tf.complex64),
        tf.zeros(kspace_size, dtype=tf.complex64),
    ]
    if multicoil:
        inputs.append(tf.zeros(kspace_size, dtype=tf.complex64))
    model(inputs)
    def tf_psnr(y_true, y_pred):
        perm_psnr = [3, 1, 2, 0]
        psnr = tf.image.psnr(
            tf.transpose(y_true, perm_psnr),
            tf.transpose(y_pred, perm_psnr),
            tf.reduce_max(y_true),
        )
        return psnr
    def tf_ssim(y_true, y_pred):
        perm_ssim = [0, 1, 2, 3]
        ssim = tf.image.ssim(
            tf.transpose(y_true, perm_ssim),
            tf.transpose(y_pred, perm_ssim),
            tf.reduce_max(y_true),
        )
        return ssim

    model.compile(loss=tf_psnr, metrics=[tf_ssim])
    model.load_weights(f'{CHECKPOINTS_DIR}checkpoints/{run_id}-{n_epochs:02d}.hdf5')
    eval_res = model.evaluate(val_set, verbose=1, steps=199 if n_samples is None else None)
    return model.metrics_names, eval_res