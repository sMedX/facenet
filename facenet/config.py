# coding: utf-8
__author__ = 'Ruslan N. Kosarev'

import yaml
import pathlib

src_dir = pathlib.Path(__file__).parents[1]
file_extension = '.png'


class YAMLConfigReader:
    """Object representing YAML settings as a dict-like object with values as fields
    """

    def __init__(self, custom_config_file=None):
        self.update_from_file(custom_config_file)

    @property
    def _config(self):
        if '_config_dict' not in self.__dict__:
            self.__dict__['_config_dict'] = {}
        return self.__dict__['_config_dict']

    def update(self, dct):
        """Update config from dict

        :param dct: dict
        """
        self._config.update(dct)

    def update_from_file(self, path):
        """Update config from YAML file
        """
        with open(path, "r") as custom_config:
            self.update(yaml.safe_load(custom_config.read()))

    def dump(self):
        """Dump config to YAML string
        """
        return yaml.dump(self._config)

    def get(self, name, default=None):
        return self._config.get(name, default)

    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        raise AttributeError("Cannot set config attribute")

    def __contains__(self, name):
        return name in self._config

    def __repr__(self):
        return "<config object>"


class DefaultConfig:
    def __init__(self):
        self.model = src_dir.joinpath('models', '20190727-080213')
        self.pretrained_checkpoint = src_dir.joinpath('models', '20190727-080213', 'model-20190727-080213.ckpt-275')

        # type of distance metric to use. 0: Euclidian, 1:Cosine similarity distance
        self.distance_metric = 0

        # image size (height, width) in pixels
        self.image_size = 160

        # embedding size
        self.embedding_size = 512

        # image standardisation
        # False: tf.image.per_image_standardization(image)
        # True: (tf.cast(image, tf.float32) - 127.5) / 128.0
        self.image_standardization = True
