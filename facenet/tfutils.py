# coding:utf-8
__author__ = 'Ruslan N. Kosarev'

from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow.python.tools import strip_unused_lib
from tensorflow.python.tools import optimize_for_inference_lib
from tensorflow.python.framework import dtypes


def tensor_by_name_exist(tensor_name):
    tensor_names = [t.name for op in tf.get_default_graph().get_operations() for t in op.values()]

    return True if tensor_name in tensor_names else False


def get_pb_model_filename(model_dir):
    model_dir = Path(model_dir).expanduser()
    pb_files = list(model_dir.glob('*.pb'))

    if len(pb_files) == 0:
        raise ValueError('No pb file found in the model directory {}.'.format(model_dir))

    if len(pb_files) > 1:
        raise ValueError('There should not be more than one pb file in the model directory {}.'.format(model_dir))

    return pb_files[0]


def get_model_filenames(model_dir):
    model_dir = Path(model_dir).expanduser()
    meta_files = list(model_dir.glob('*.meta'))

    if len(meta_files) == 0:
        raise ValueError('No meta file found in the model directory {}.'.format(model_dir))

    if len(meta_files) > 1:
        raise ValueError('There should not be more than one meta file in the model directory {}.'.format(model_dir))

    meta_file = meta_files[0]
    ckpt = tf.train.get_checkpoint_state(model_dir)
    ckpt_file = Path(ckpt.model_checkpoint_path).name
    return meta_file, ckpt_file


def restore_checkpoint(saver, session, path):
    if path:
        path = Path(path).expanduser()
        print('Restoring pre-trained model: {}'.format(path))
        saver.restore(session, str(path))


def freeze_graph_def(sess, input_graph_def, output_node_names):
    for node in input_graph_def.node:
        if node.op == 'RefSwitch':
            node.op = 'Switch'
            for index in range(len(node.input)):
                if 'moving_' in node.input[index]:
                    node.input[index] = node.input[index] + '/read'
        elif node.op == 'AssignSub':
            node.op = 'Sub'
            if 'use_locking' in node.attr:
                del node.attr['use_locking']
        elif node.op == 'AssignAdd':
            node.op = 'Add'
            if 'use_locking' in node.attr:
                del node.attr['use_locking']

    # Get the list of important nodes
    whitelist_names = []
    prefixes = ('InceptionResnet', )  # 'embeddings', 'image_batch', 'phase_train')

    for node in input_graph_def.node:
        if node.name.startswith(prefixes):
            whitelist_names.append(node.name)

    # Replace all the variables in the graph with constants of the same values
    output_graph_def = tf.compat.v1.graph_util.convert_variables_to_constants(sess,
                                                                              input_graph_def,
                                                                              output_node_names,
                                                                              variable_names_whitelist=whitelist_names)
    return output_graph_def


def save_freeze_graph(model_dir, output_file=None, suffix='', strip=True, optimize=True, as_text=False):

    ext = '.pbtxt' if as_text else '.pb'

    input_node_names = ['input']
    output_node_names = ['embedding']

    input_node_types = [dtypes.float32.as_datatype_enum]

    with tf.Graph().as_default():
        with tf.compat.v1.Session() as sess:
            # Load the model metagraph and checkpoint
            print('Model directory: {}'.format(model_dir))
            meta_file, ckpt_file = get_model_filenames(model_dir)

            if output_file is None:
                output_file = model_dir.joinpath(meta_file.stem + suffix + ext)

            print('Metagraph file: {}'.format(meta_file))
            print('Checkpoint file: {}'.format(ckpt_file))

            saver = tf.compat.v1.train.import_meta_graph(str(model_dir.joinpath(meta_file)), clear_devices=True)
            sess.run(tf.compat.v1.global_variables_initializer())
            sess.run(tf.compat.v1.local_variables_initializer())
            saver.restore(sess, str(model_dir.joinpath(ckpt_file)))

            # Retrieve the protobuf graph definition and fix the batch norm nodes
            input_graph_def = sess.graph.as_graph_def()

            # dest_nodes = ['input', 'embeddings']
            # output_graph_def = tf.compat.v1.graph_util.extract_sub_graph(input_graph_def, dest_nodes)

            graph_def = freeze_graph_def(sess, input_graph_def, output_node_names)

            if strip:
                graph_def = strip_unused_lib.strip_unused(graph_def,
                                                          input_node_names, output_node_names,
                                                          input_node_types)

            if optimize:
                graph_def = optimize_for_inference_lib.optimize_for_inference(graph_def,
                                                                              input_node_names, output_node_names,
                                                                              input_node_types)

            tf.io.write_graph(graph_def, str(output_file.parent), output_file.name, as_text=as_text)

    print('{} ops in the final graph: {}'.format(len(graph_def.node), output_file))

    return output_file


def save_variables_and_metagraph(sess, saver, model_dir, step, model_name=None):

    if model_name is None:
        model_name = model_dir.stem

    # save the model checkpoint
    # start_time = time.time()
    checkpoint_path = model_dir.joinpath('model-{}.ckpt'.format(model_name))
    saver.save(sess, str(checkpoint_path), global_step=step, write_meta_graph=False)
    # save_time_variables = time.time() - start_time
    print('saving checkpoint: {}-{}'.format(checkpoint_path, step))

    metagraph_filename = model_dir.joinpath('model-{}.meta'.format(model_name))

    if not metagraph_filename.exists():
        saver.export_meta_graph(str(metagraph_filename))
        print('saving meta graph:', metagraph_filename)


def load_model(path, input_map=None):
    # Check if the model is a model directory (containing a metagraph and a checkpoint file) or
    # if it is a protobuf file with a frozen graph

    path = Path(path).expanduser()

    if path.is_file():
        print('Model filename: {}'.format(path))
        with tf.io.gfile.GFile(str(path), 'rb') as f:
            graph_def = tf.compat.v1.GraphDef()
            graph_def.ParseFromString(f.read())
            tf.import_graph_def(graph_def, input_map=input_map, name='')
    else:
        pb_files = list(path.glob('*.pb'))

        if len(pb_files) == 1:
            load_model(pb_files[0], input_map=input_map)
        else:
            print('Model directory: {}'.format(path))
            meta_file, ckpt_file = get_model_filenames(path)

            print('Metagraph file : {}'.format(meta_file))
            print('Checkpoint file: {}'.format(ckpt_file))

            saver = tf.compat.v1.train.import_meta_graph(str(path.joinpath(meta_file)), input_map=input_map)
            with tf.compat.v1.Session() as sess:
                saver.restore(sess, str(path.joinpath(ckpt_file)))


def int64_feature(value):
    """Wrapper for insert int64 feature into Example proto."""
    if not isinstance(value, list):
        value = [value]
    return tf.train.Feature(int64_list=tf.train.Int64List(value=value))


def float_feature(value):
    """Wrapper for insert float features into Example proto."""
    if not isinstance(value, list):
        value = [value]
    return tf.train.Feature(float_list=tf.train.FloatList(value=value))


def bytes_feature(value):
    """Wrapper for insert bytes features into Example proto."""
    if not isinstance(value, list):
        value = [value]
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=value))


def dict_to_example(dct):

    for key, item in dct.items():
        if isinstance(item, str):
            dct[key] = bytes_feature(item.encode())
        elif isinstance(item, np.int64):
            dct[key] = int64_feature(item)
        elif isinstance(item, np.ndarray):
            dct[key] = float_feature(item.tolist())
        else:
            raise TypeError('Invalid item type {}'.format(type(item)))

    features = tf.train.Features(feature=dct)

    return tf.train.Example(features=features)