_base_ = [
    '../../../../_base_/default_runtime.py',
    '../../../../_base_/datasets/ap10k.py'
]
evaluation = dict(interval=10, metric='mAP', save_best='AP')

# optimizer = dict(type='AdamW', lr=1e-3, betas=(0.9, 0.999), weight_decay=0.1,
#                  constructor='LayerDecayOptimizerConstructor',
#                  paramwise_cfg=dict(
#                                     num_layers=12,
#                                     layer_decay_rate=0.8,
#                                     custom_keys={
#                                             'bias': dict(decay_multi=0.),
#                                             'pos_embed': dict(decay_mult=0.),
#                                             'relative_position_bias_table': dict(decay_mult=0.),
#                                             'norm': dict(decay_mult=0.)
#                                             }
#                                     )
#                 )
# optimizer_config = dict(grad_clip=dict(max_norm=1., norm_type=2))
optimizer = dict(
    type='Adam',
    lr=5e-4,
)
optimizer_config = dict(grad_clip=None)

# learning policy
lr_config = dict(
    policy='step',
    warmup='linear',
    warmup_iters=500,
    warmup_ratio=0.001,
    step=[170, 200])
total_epochs = 210

target_type = 'GaussianHeatmap'

log_config = dict(
    interval=1,
    hooks=[
        dict(type='TextLoggerHook'),
        # dict(type='TensorboardLoggerHook')
    ])

channel_cfg = dict(
    num_output_channels=17,
    dataset_joints=17,
    dataset_channel=[
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
    ],
    inference_channel=[
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
    ])

# model settings
model = dict(
    type='TopDown',
    pretrained='data/small_pretrained.pth',
    backbone=dict(
        type='ViT',
        img_size=(256, 192),
        patch_size=16,
        embed_dim=384,
        depth=12,
        num_heads=12,
        ratio=1,
        use_checkpoint=False,
        mlp_ratio=4,
        qkv_bias=True,
        drop_path_rate=0.3, #this is what I used up to now
    ),
    keypoint_head=dict(
        type='TopdownHeatmapSimpleHead',
        in_channels=384,
        num_deconv_layers=2,
        num_deconv_filters=(256, 256),
        num_deconv_kernels=(4, 4),
        extra=dict(final_conv_kernel=1, ),
        out_channels=channel_cfg['num_output_channels'],
        loss_keypoint=dict(type='JointsMSELoss', use_target_weight=True)),
    train_cfg=dict(),
    test_cfg=dict(
        flip_test=True,
        post_process='default',
        shift_heatmap=True,
        modulate_kernel=11))

data_cfg = dict(
    image_size=[192, 256],
    heatmap_size=[48, 64],
    num_output_channels=channel_cfg['num_output_channels'],
    num_joints=channel_cfg['dataset_joints'],
    dataset_channel=channel_cfg['dataset_channel'],
    inference_channel=channel_cfg['inference_channel'],
    soft_nms=False,
    # use_nms=False,
    nms_thr=1.0,
    oks_thr=0.9,
    vis_thr=0.2,
    use_gt_bbox=True,
    det_bbox_thr=0.0,
    bbox_file='',
    # max_num_joints=133, # dunno
)

train_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='TopDownRandomFlip', flip_prob=0.5),
    dict(
        type='TopDownHalfBodyTransform',
        num_joints_half_body=8,
        prob_half_body=0.3),
    dict(
        type='TopDownGetRandomScaleRotation', rot_factor=40, scale_factor=0.5),
    dict(type='TopDownAffine'),
    dict(type='ToTensor'),
    dict(
        type='NormalizeTensor',
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]),
    dict(type='TopDownGenerateTarget', sigma=2),
    dict(
        type='Collect',
        keys=['img', 'target', 'target_weight'],
        meta_keys=[
            'image_file', 'joints_3d', 'joints_3d_visible', 'center', 'scale',
            'rotation', 'bbox_score', 'flip_pairs'
        ]),
]

val_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='TopDownAffine'),
    dict(type='ToTensor'),
    dict(
        type='NormalizeTensor',
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]),
    dict(
        type='Collect',
        keys=['img'],
        meta_keys=[
            'image_file', 'center', 'scale', 'rotation', 'bbox_score',
            'flip_pairs'
        ]),
]

test_pipeline = val_pipeline

data_root = 'data/ap-10k'
data = dict(
    samples_per_gpu=64,
    workers_per_gpu=8,
    val_dataloader=dict(samples_per_gpu=64),
    test_dataloader=dict(samples_per_gpu=64),
    train=dict(
        type='AnimalAP10KDataset',
        ann_file=f'{data_root}/annotations/ap10k-train-split1.json',
        img_prefix=f'{data_root}/data/',
        data_cfg=data_cfg,
        pipeline=train_pipeline,
        dataset_info={{_base_.dataset_info}}),
    val=dict(
        type='AnimalAP10KDataset',
        ann_file=f'{data_root}/annotations/ap10k-val-split1.json',
        img_prefix=f'{data_root}/data/',
        data_cfg=data_cfg,
        pipeline=val_pipeline,
        dataset_info={{_base_.dataset_info}}),
    test=dict(
        type='AnimalAP10KDataset',
        ann_file=f'{data_root}/annotations/ap10k-val-split1.json',
        img_prefix=f'{data_root}/data/',
        data_cfg=data_cfg,
        pipeline=val_pipeline,
        dataset_info={{_base_.dataset_info}}),
)


# bash tools/dist_train.sh configs/animal/2d_kpt_sview_rgb_img/topdown_heatmap/apt36k/orig_zebras_def.py 1 --seed 0 --autoscale-lr --work-dir orig_zebras_def && bash tools/dist_train.sh configs/animal/2d_kpt_sview_rgb_img/topdown_heatmap/apt36k/orig_zebras_old.py 1 --seed 0 --autoscale-lr --work-dir orig_zebras_old && bash tools/dist_train.sh configs/animal/2d_kpt_sview_rgb_img/topdown_heatmap/apt36k/orig_zebras_old_adam.py 1 --seed 0 --autoscale-lr --work-dir orig_zebras_old_adam
# bash tools/dist_train.sh configs/animal/2d_kpt_sview_rgb_img/topdown_heatmap/apt36k/small_zebras_def.py 1 --seed 0 --autoscale-lr --work-dir small_zebras_def && bash tools/dist_train.sh configs/animal/2d_kpt_sview_rgb_img/topdown_heatmap/apt36k/small_zebras_old.py 1 --seed 0 --autoscale-lr --work-dir small_zebras_old && bash tools/dist_train.sh configs/animal/2d_kpt_sview_rgb_img/topdown_heatmap/apt36k/small_zebras_old_adam.py 1 --seed 0 --autoscale-lr --work-dir small_zebras_old_adam
