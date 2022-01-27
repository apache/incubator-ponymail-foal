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
import random
import requests

# Run as: python3 -m pytest [-s] test/itest_integration.py

API_BASE='http://localhost:8080/api'

# Emulate how test auth is used by GUI
def get_cookies(user='user'):
    state=random.randint(
        1000000000000000000,
        2000000000000000000) # roughly equivalent to code in oauth.js
    testauth='testauth'
    res = requests.get(f"{API_BASE}/{testauth}?state={state}&redirect_uri=x&state={state}&key=ignored",allow_redirects=False)
    code = res.headers['Location'][1:]
    res = requests.get(f"{API_BASE}/oauth.lua?key=ignored{code}&oauth_token={API_BASE}/{testauth}&state={state}&user={user}")
    cookies = res.cookies
    print(res.text)
    jzon = requests.get(f"{API_BASE}/preferences", cookies=cookies).json()
    assert 'credentials' in jzon['login']
    return cookies


def test_lists():
    jzon = requests.get(f"{API_BASE}/preferences").json()
    # print(jzon)
    lists = jzon['lists']
    assert 'ponymail.apache.org' in lists
    assert 'users' in lists['ponymail.apache.org']

def test_public_stats():
    jzon = requests.get(
        f"{API_BASE}/stats.lua?list=users&domain=ponymail.apache.org&emailsOnly&d=gte=0d",
    ).json()
    assert jzon['firstYear'] == 2022
    assert jzon['firstMonth'] == 1
    assert jzon['lastYear'] == 2022
    assert jzon['lastMonth'] == 1
    assert jzon['hits'] == 6
    for email in jzon['emails']:
        assert email['list_raw'] == '<users.ponymail.apache.org>'
        assert email['list'] == email['list_raw']
        assert email['id'] == email['mid']
        assert email['private'] == False
    # Check we cannot see the private emails
    jzon = requests.get(
        f"{API_BASE}/stats.lua?list=users&domain=ponymail.apache.org&emailsOnly&d=2019-09"
        ).json()
    assert jzon['hits'] == 0

def test_private_stats():
    cookies = get_cookies('user')
    # only fetch the private mail stats
    jzon = requests.get(
        f"{API_BASE}/stats.lua?list=users&domain=ponymail.apache.org&emailsOnly&d=2019-09",
        cookies=cookies
    ).json()
    # The earlier mails are private
    assert jzon['firstYear'] == 2019
    assert jzon['firstMonth'] == 9
    assert jzon['lastYear'] == 2022
    assert jzon['lastMonth'] == 1
    assert jzon['hits'] == 4
    for email in jzon['emails']:
        assert email['list_raw'] == '<users.ponymail.apache.org>'
        assert email['list'] == email['list_raw']
        assert email['id'] == email['mid']
        assert email['private']
