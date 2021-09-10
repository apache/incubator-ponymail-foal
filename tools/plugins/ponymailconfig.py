#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
    common config parsing
    reads the file ponymail.yaml from the same directory as this file
    Emulates parts of the API of configparser/RawConfigParser

    How to use:

    from ponymailconfig import PonymailConfig
    config=PonymailConfig()
    if config.has_option("elasticsearch", "user"):
        ...
"""

import os.path
import yaml


class PonymailConfig:

    def __init__(self):
        # Get ../archiver.yaml
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "archiver.yaml")
        self.config = yaml.safe_load(open(config_path))

    def has_section(self, section):
        val = section in self.config
        return val

    def has_option(self, section, option):
        val = section in self.config and self.config[section] and option in self.config[section]
        return val

    def get(self, section, option, fallback=None):
        if self.has_option(section, option):
            val = self.config[section][option] or fallback
        else:
            val = fallback
        return val
