# coding:utf-8
"""Training a face recognizer with TensorFlow using softmax cross entropy loss
"""
# MIT License
# 
# Copyright (c) 2020 sMedX
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# https://www.tensorflow.org/tutorials/customization/custom_training

import click
import time
from tqdm import tqdm
from pathlib import Path
import itertools

import tensorflow as tf

from facenet.models.inception_resnet_v1_tf2 import InceptionResnetV1 as FaceNet
from facenet import ioutils, statistics, config, dataset, facenet
from facenet import config_tf2 as config
from facenet import facenet_tf2 as facenet


@click.command()
@click.option('--config', default=None, type=Path,
              help='Path to yaml config file with used options of the application.')
def main(**options):
    app_file_name = '/home/korus/workspace/faces/FaceNet/facenet/apps/train_softmax.py'
    cfg = config.train_softmax(app_file_name, options)

    # gpus = tf.config.experimental.list_physical_devices('GPU')
    #
    # if gpus == 0:
    #     print('\nnot GPU hardware devices available\n')
    # else:
    #     print(f'\nGPU hardware devices available: {len(gpus)}')
    #     for idx, device in enumerate(gpus):
    #         print(f'{idx}/{len(gpus)} - ', device)
    #     print()
    #
    #     tf.config.experimental.set_visible_devices(gpus[0], 'GPU')
    #     logical_gpus = tf.config.experimental.list_logical_devices('GPU')
    #     print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")

    # ------------------------------------------------------------------------------------------------------------------
    train_dbase = dataset.DBase(cfg.dataset)
    ioutils.write_text_log(cfg.logfile, train_dbase)
    print('train dbase:', train_dbase)

    test_dbase = dataset.DBase(cfg.validate.dataset)
    ioutils.write_text_log(cfg.logfile, test_dbase)
    print('test dbase', test_dbase)

    loader = facenet.ImageLoader(config=cfg.image)
    dset = {
        'train': facenet.make_train_dataset(train_dbase, loader, cfg),
        'test': facenet.make_test_dataset(test_dbase, loader, cfg),
    }

    # import network
    facenet_model = FaceNet(image_processing=facenet.ImageProcessing(cfg.image))
    facenet_model(facenet.inputs(cfg.image))

    facenet_model.conv2d.summary()
    for idx,  layer in enumerate(facenet_model.conv2d.layers):
        print(idx, layer.name)

    for idx, var in enumerate(facenet_model.conv2d.trainable_variables):
        print(idx, var.name, var.shape)

    print('number of trainable variables', len(facenet_model.conv2d.trainable_variables))
    facenet_model.summary()

    model = tf.keras.Sequential([
        facenet_model,
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dense(train_dbase.nrof_classes, name='logits')
    ])

    model(facenet.inputs(cfg.image))

    print('number of trainable variables', len(model.trainable_variables))

    learning_rate = facenet.learning_rate_schedule(cfg.train)
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

    # ema = tf.train.ExponentialMovingAverage(options.train.moving_average_decay)

    # ckpt = tf.train.Checkpoint(step=tf.Variable(0), optimizer=optimizer, net=model)
    # manager = tf.train.CheckpointManager(ckpt, cfg.model.path, max_to_keep=3)

    # Training and test loop
    for epoch in range(cfg.train.epoch.nrof_epochs):
        info = f'(model {cfg.model.path.stem}, ' \
               f'epoch [{epoch+1}/{cfg.train.epoch.nrof_epochs}], ' \
               f'learning rate {learning_rate(epoch*cfg.train.epoch.size).numpy()})'
        print('Running training', info)

        # Reset the metrics at the start of the next epoch
        # loss_value.reset_states()

        with tqdm(total=cfg.train.epoch.size) as bar:
            for step, (images, labels) in enumerate(dset['train']):
                if step == cfg.train.epoch.size:
                    break

                with tf.GradientTape() as tape:
                    logits = model(images, training=True)
                    loss = facenet.softmax_cross_entropy_with_logits(logits, labels)

                    gradients = tape.gradient(loss, model.trainable_variables)
                    optimizer.apply_gradients(zip(gradients, model.trainable_variables))

                bar.set_postfix_str(f'loss {loss:.5f}')
                bar.update()

        # perform validation
        epoch1 = epoch + 1
        if epoch1 % cfg.validate.every_n_epochs == 0 or epoch1 == cfg.train.epoch.nrof_epochs:
            embeddings, labels = facenet.evaluate_embeddings(facenet_model, dset['test'])
            validation = statistics.FaceToFaceValidation(embeddings, labels, cfg.validate.validate, info=info)
            ioutils.write_text_log(cfg.logfile, validation)
            print(validation)

        # save checkpoints
        # ckpt.step.assign_add(1)
        # save_path = manager.save()
        # print(f'Saved checkpoint for step {int(ckpt.step)}: {save_path}')

    # model.save(cfg.model.path.joinpath('model'))

    print('Model and logs have been saved to the directory: {}'.format(cfg.model.path))


if __name__ == '__main__':
    main()