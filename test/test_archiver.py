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

import pytest

# To be run as: python3 -m pytest test/test_archiver.py
# This ensures sys.path is set up correctly

import sys
import email.errors
import email.header
import email.utils
from tools import archiver

def show(dict):
    for key in dict.keys():
        print("%s: %s" % (key, dict[key]))

def test_archiver_1():
    print("---------",file=sys.stderr)
    archie = archiver.Archiver(
        
    )
    list_override = 'a.b.c.d'
    private = False
    file = open("test/resources/rfc2822-A5.eml","rb")
    message_raw = file.read()
    message = email.message_from_bytes(message_raw, policy=email.policy.SMTPUTF8)
    json, contents, _msgdata, _irt, skipit = archie.compute_updates(
        list_override, private, message, message_raw
    )
    print("--json--")
    show(json)
    print("--contents--")
    print(contents)
    print("--_msgdata--")
    show(_msgdata)
    print("--_irt--")
    print(_irt)
    print("--skipit--")
    print(skipit)
    # assert False, json

test_archiver_1()