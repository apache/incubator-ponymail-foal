#!/usr/bin/env python3

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

# utility to check mappings, report differences and create missing mappings

#  ** INITIAL VERSION, liable to change **

import argparse
import sys
import yaml
from plugins.elastic import Elastic

# Needs 3.4 or higher to work
if sys.version_info <= (3, 3):
    print("This script requires Python 3.4 or higher in order to work!")
    sys.exit(-1)

# the desired mappings
mapping_file = yaml.safe_load(open("mappings.yaml", "r"))

elastic = Elastic()
major = elastic.engineMajor()
if major != 7:
    print("This script requires ElasticSearch 7 API in order to work!")
    sys.exit(-1)

parser = argparse.ArgumentParser(description="Command line options.")
parser.add_argument(
    "--create",
    dest="create",
    action="store_true",
    help="Create the missing mapping(s)",
)
parser.add_argument('names', nargs='*')
args = parser.parse_args()

def check_mapping(index):
  # expected mappings
  mappings_expected = mapping_file[index]['properties']

  index_name = elastic.index_name(index)
  # actual mappings
  mappings = elastic.indices.get_mapping(index=index_name)[index_name]['mappings']['properties']

  if mappings == mappings_expected:
    print("Mappings are as expected, hoorah!")
  else:
    print("Mappings differ:")
    unexpected = set(mappings) - set(mappings_expected)
    for name in unexpected:
      data = {name: mappings[name]}
      print("Unexpected: " + str(data))
    expected = set(mappings_expected) - set(mappings)
    for name in expected:
      data = {name: mappings_expected[name]}
      if args.create:
        print("Creating the mapping: " + str(data))
        elastic.indices.put_mapping(body={'properties': data}, index=index_name)
      else:
        print("Missing: " + str(data))

for type in args.names if len(args.names) > 0 else mapping_file.keys():
  print("Checking " + type)
  check_mapping(type)