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

# To be run as: python3 -m pytest test/test_defuzzer.py
# This ensures sys.path is set up correctly

from server.plugins.defuzzer import defuzz

def test_defuzzer_0():
    with pytest.raises(ValueError) as excinfo:
        defuzz({})
    assert 'You must specify a domain' in str(excinfo.value)
    with pytest.raises(ValueError) as excinfo:
        defuzz({'domain': 'invalid'})
    assert 'You must specify a list' in str(excinfo.value)

def test_defuzzer_1():
    with pytest.raises(ValueError) as excinfo:
        defuzz({'list': '@', 'domain': 'invalid'})
    assert 'cannot contain @' in str(excinfo.value)

def test_defuzzer_2():
    df = defuzz({'list': 'dev', 'domain': 'ponymail.apache.org', 'q': ''})
    assert 1 == len(df)
    assert 'must' in df
    dfm = df['must']
    assert 2 == len(dfm)
    assert "{'term': {'list_raw': '<dev.ponymail.apache.org>'}}" == str(dfm[0])
    assert "{'range': {'date': {'gt': 'now-30d', 'lt': 'now+1d'}}}" == str(dfm[1])

def test_defuzzer_3():
    df = defuzz({'list': 'dev', 'domain': 'ponymail.apache.org', 'q': 'a -b --c'})
    assert 2 == len(df)
    assert 'must' in df
    assert 'must_not' in df

    dfm = df['must']
    assert 3 == len(dfm)
    assert "{'term': {'list_raw': '<dev.ponymail.apache.org>'}}" == str(dfm[0])
    assert "{'range': {'date': {'gt': 'now-30d', 'lt': 'now+1d'}}}" == str(dfm[1])

    dfb = dfm[2]

    assert 1 == len(dfb)
    assert 'bool' in dfb
    dfbb = dfb['bool']
    assert 2 == dfbb['minimum_should_match'] # two shoulds

    dfbs = dfbb['should']
    assert 2 == len(dfbs)

    assert "{'bool': {'should': [{'multi_match': {'fields': ['from', 'body', 'subject'], 'query': 'a', 'type': 'phrase'}}]}}" == str(dfbs[0])
    assert "{'bool': {'should': [{'multi_match': {'fields': ['from', 'body', 'subject'], 'query': '-c', 'type': 'phrase'}}]}}" == str(dfbs[1])

    dfn = df['must_not']

    assert "[{'match': {'subject': 'b'}}, {'match': {'from': 'b'}}, {'match': {'body': 'b'}}]" == str(dfn)