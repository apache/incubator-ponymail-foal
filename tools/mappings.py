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

# utility to check for and add missing mappings. Only applies to mbox index currently

#  ** INITIAL VERSION, liable to change **

import sys
import yaml
from plugins.elastic import Elastic

# Needs 3.4 or higher to work
if sys.version_info <= (3, 3):
    print("This script requires Python 3.4 or higher in order to work!")
    sys.exit(-1)

# the desired mappings
mapping_file = yaml.safe_load(open("mappings.yaml", "r"))['mbox']['properties']

elastic = Elastic()
major = elastic.engineMajor()
if major != 7:
    print("This script requires ElasticSearch 7 API in order to work!")
    sys.exit(-1)
  
# actual mappings
mappings = elastic.get_mapping(index=elastic.db_mbox)[elastic.db_mbox]['mappings']['properties']

if mappings == mapping_file:
  print("Mappings are as expected, hoorah!")
else:
  unexpected = set(mappings) - set(mapping_file)
  for name in unexpected:
    data = {name: mappings[name]}
    print("Unexpected: " + str(data))
  expected = set(mapping_file) - set(mappings)
  for name in expected:
    data = {name: mapping_file[name]}
    print("Missing: " + str(data))
    elastic.put_mapping(body={'properties': data}, index=elastic.db_mbox)
