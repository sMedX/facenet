"""Validate a face recognizer on the "Labeled Faces in the Wild" dataset (http://vis-www.cs.umass.edu/lfw/).
Embeddings are calculated using the pairs from http://vis-www.cs.umass.edu/lfw/pairs.txt and the ROC curve
is calculated and plotted. Both the model metagraph and the model parameters need to exist
in the same directory, and the metagraph should have the extension '.meta'.
"""
# MIT License
# 
# Copyright (c) 2019 SMedX
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

import sys
import argparse
import numpy as np
import pathlib as plib
from facenet import dataset, utils, ioutils, h5utils


def main(args):

    if args.outdir is None:
        args.outdir = args.dir + '_false_examples'
    ioutils.makedirs(args.outdir)

    if args.h5file is None:
        args.h5file = args.dir + '.h5'

    # Get the paths for the corresponding images
    tf_files = dataset.list_files(args.dir, extension='.tfrecord')
    print('dataset', args.dir)
    print('number of tf records', len(tf_files))

    for i, file in enumerate(tf_files):
        print('\r{}/{}'.format(i, len(tf_files)), end=utils.end(i, len(tf_files)))

        tf = utils.TFRecord(file)

        dist = 2*(1 - tf.embeddings @ tf.embeddings.transpose())

        dist[np.diag_indices(dist.shape[0])] = np.nan
        values = np.nanmean(dist, axis=0)
        mean_face_index = values.argmin()

        while np.nanmax(dist[mean_face_index]) > args.threshold:
            index = np.nanargmax(dist[mean_face_index])

            image = utils.ConcatenateImages(tf.files[mean_face_index], tf.files[index], dist[mean_face_index, index])
            image.save(args.outdir)

            print()
            print(dist[mean_face_index, index])
            print(tf.files[index])

            dist[mean_face_index, index] = np.nan

        if i == 5:
            break



def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    
    parser.add_argument('dir', type=str,
        help='Path to the directory with tf records files.')
    parser.add_argument('--outdir', type=str,
        help='Directory to save examples with false examples.', default=None)
    parser.add_argument('--h5file', type=str,
        help='Path to h5 file to save information about false images.', default=None)
    parser.add_argument('--threshold', type=float,
        help='Threshold to identify outlier faces.', default=1.80)
    return parser.parse_args(argv[1:])


if __name__ == '__main__':
    main(parse_arguments(sys.argv))
