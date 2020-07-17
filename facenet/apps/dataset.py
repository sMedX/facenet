# coding:utf-8
"""Application to print information about dataset
"""
# MIT License
# 
# Copyright (c) 2020 sMedX
# 
import click
from pathlib import Path
from facenet import dataset


@click.command()
@click.option('--path', type=Path,
              help='Path to data set directory.')
def main(**args):
    config = dataset.Config(args['path'])
    dbase = dataset.DBase(config)
    print(dbase)


if __name__ == '__main__':
    main()
