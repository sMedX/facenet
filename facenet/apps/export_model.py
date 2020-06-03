"""Imports a model metagraph and checkpoint file, converts the variables to constants
and exports the model as a graphdef protobuf
"""
# MIT License
# Copyright (c) 2020 sMedX

import click
import pathlib
from facenet import tfutils, config


@click.command()
@click.option('--model_dir', default=config.default_model, type=pathlib.Path,
              help='Directory with the meta graph and checkpoint files containing model parameters.')
@click.option('--as_text', default=0, type=int,
              help='Writes the graph as an ASCII proto.')
@click.option('--strip', default=1, type=int,
              help='Removes unused nodes from a graph file.')
def main(**args):
    pb_file = tfutils.save_freeze_graph(args['model_dir'], strip=args['strip'], as_text=args['as_text'])


if __name__ == '__main__':
    main()
