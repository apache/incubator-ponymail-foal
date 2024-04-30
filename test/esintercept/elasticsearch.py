#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Very simple module to intercept calls to Elasticsearch methods
# Writes call parameters to a file.
#
# Use it by defining PYTHONPATH to include its parent dir, e.g.
# [OUT=/tmp/pmfoal_out.txt] PYTHONPATH=test/esintercept python3 tools/archiver.py <file.eml
# Redefine OUT to change the output file name

import os
import json

# Dummy to satisf code
VERSION = (7, 0, 1)
VERSION_STR = "7.0.1"

import atexit

def exit_handler():
    print("Closing %s" % outfile)
    OUT.close()

atexit.register(exit_handler)

outfile=os.getenv('OUT','/tmp/pmfoal_out.txt')
print("Opening %s" % outfile)
OUT = open(outfile, 'w', encoding='utf-8')


def show(method, *args, **kwargs):
    OUT.write("======= Method: %s =======\n" % method)
    bits = {
        'args': args,
        'kwargs': kwargs,
    }
    json.dump(bits, OUT, indent=2, sort_keys=True)
    OUT.write("\n")

class helpers:
    def bulk(self,*args,**kwargs):
        show('bulk', *args, **kwargs)

class Indices:
    def exists(self, *args, **kwargs):
        show('exists', *args, **kwargs)
        return True # Dummy value

class Elasticsearch:

    indices = Indices()

    def __init__(self, *args, **kwargs):
        show('Elasticsearch', *args,**kwargs)

    def index(self, *args, **kwargs):
        show('index', *args, **kwargs)

    def info(self, *args, **kwargs):
        show('info', *args, **kwargs)
        return {"version": {"number": VERSION_STR}} # sufficient for testing

class ConnectionError:
    pass

class AsyncElasticsearch(Elasticsearch):
    pass
