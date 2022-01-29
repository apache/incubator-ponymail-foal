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
TEST_DOMAIN = 'ponymail.apache.org'
TEST_LIST = 'users'

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
    jzon = requests.get(f"{API_BASE}/preferences", cookies=cookies).json()
    assert 'credentials' in jzon['login']
    return cookies

def check_access(email, cookies):
        # check email accessibility
        mid = email['mid']
        private = email['private']
        res = requests.get(
            f"{API_BASE}/email.lua",
            params={"id": mid},
            cookies=cookies
        )
        assert res.status_code == 200
        jzon = res.json()
        assert mid == jzon['mid']
        assert mid in jzon['permalinks']
        # check email access by message-id
        msgid = jzon['message-id']
        listid = jzon['list_raw']
        res = requests.get(
            f"{API_BASE}/email.lua",
            params={"id": msgid, "listid": listid},
            cookies=cookies
        )
        assert res.status_code == 200
        if private:
            # should not be visible without cookies
            res = requests.get(
                f"{API_BASE}/email.lua",
                params={"id": mid}
            )
            assert res.status_code == 404
            res = requests.get(
                f"{API_BASE}/email.lua",
                params={"id": msgid, "listid": listid}
            )
            assert res.status_code == 404
        # check source accessibility
        res = requests.get(
            f"{API_BASE}/source.lua",
            params={"id": mid},
            cookies=cookies
        )
        assert res.status_code == 200, mid
        res = requests.get(
            f"{API_BASE}/source.lua",
            params={"id": msgid, "listid": listid},
            cookies=cookies
        )
        assert res.status_code == 200
        if private:
            # should not be visible without cookies
            res = requests.get(
                f"{API_BASE}/source.lua",
                params={"id": mid}
            )
            assert res.status_code == 404
            res = requests.get(
                f"{API_BASE}/source.lua",
                params={"id": msgid, "listid": listid}
            )
            assert res.status_code == 404

def test_lists():
    jzon = requests.get(f"{API_BASE}/preferences").json()
    # print(jzon)
    lists = jzon['lists']
    assert TEST_DOMAIN in lists
    assert TEST_LIST in lists[TEST_DOMAIN]
    assert len(lists) == 1 # only expecting one domain

def test_public_stats():
    jzon = requests.get(
        f"{API_BASE}/stats.lua",
        params={"list": TEST_LIST, "domain": TEST_DOMAIN, "emailsOnly": True, "d": 'gte=0d'}
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
        check_access(email, None)
    # Check we cannot see the private emails
    jzon = requests.get(
        f"{API_BASE}/stats.lua",
        params={"list": TEST_LIST, "domain": TEST_DOMAIN, "emailsOnly": True, "d": '2019-09'}
        ).json()
    assert jzon['hits'] == 0

def test_private_stats():
    cookies = get_cookies('user')
    # only fetch the private mail stats
    jzon = requests.get(
        f"{API_BASE}/stats.lua",
        params={"list": TEST_LIST, "domain": TEST_DOMAIN, "emailsOnly": True, "d": '2019-09'},
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
        check_access(email, cookies)

def mgmt_get_text(params, cookies, expected=200):
    res = requests.post(f"{API_BASE}/mgmt.lua", params=params, cookies=cookies)
    assert res.status_code == expected, res.text
    return res.text

def mgmt_get_json(params, cookies, expected=200):
    res = requests.post(f"{API_BASE}/mgmt.lua", params=params, cookies=cookies)
    assert res.status_code == expected, res.text
    return res.json()

def test_mgmt_validation():
    admin_cookies = get_cookies('admin')
    user_cookies = get_cookies('user')
    mgmt_get_text({"action": 'log'}, user_cookies, 403)
    mgmt_get_text({"action": 'any'}, admin_cookies, 404)

    text = mgmt_get_text({"action": 'delete'}, admin_cookies)
    assert text == "Removed 0 emails from archives."

    text = mgmt_get_text({"action": 'hide'}, admin_cookies)
    assert text == "Hid 0 emails from archives."

    text = mgmt_get_text({"action": 'unhide'}, admin_cookies)
    assert text == "Unhid 0 emails from archives."

    text = mgmt_get_text({"action": 'delatt'}, admin_cookies)
    assert text == "Removed 0 attachments from archives."

    text = mgmt_get_text({"action": 'edit'}, admin_cookies, 500)
    assert "ValueError: Document ID is missing or invalid" in text

    text = mgmt_get_text({"action": 'edit', "document": '1234'}, admin_cookies, 500)
    assert "ValueError: Author field" in text

    text = mgmt_get_text({"action": 'edit', "document": '1234', "from": 'sender'}, admin_cookies, 500)
    assert "ValueError: Subject field" in text

    text = mgmt_get_text({"action": 'edit', "document": '1234', "from": 'sender', "subject": 'Test Email'}, admin_cookies, 500)
    assert "ValueError: List ID field" in text

    text = mgmt_get_text(
        {"action": 'edit', "document": '1234', "from": 'sender', "subject": 'Test Email', "list": 'abc'},
        admin_cookies, 500)
    assert "ValueError: Email body" in text

    text = mgmt_get_text(
        {"action": 'edit', "document": '1234', "from": 'sender', "subject": 'Test Email', "list": 'abc', "body": 'body'},
        admin_cookies, 404)
    assert "Email not found!" in text

def test_mgmt_log():
    admin_cookies = get_cookies('admin')
    jzon = mgmt_get_json({"action": 'log'}, admin_cookies)
    # for entry in jzon['entries']:
        # print(entry)
    # assert jzon == {"entries": []}

def test_mgmt_hiding():
    admin_cookies = get_cookies('admin')

    # reset in case of earlier failure
    text = mgmt_get_text({"action": 'unhide', "document": "c396ps3p5pb05srb4269dzcg9j7sof42"}, admin_cookies)
    assert text == "Unhid 1 emails from archives."

    jzon = requests.get(
        f"{API_BASE}/stats.lua",
        params={"list": TEST_LIST, "domain": TEST_DOMAIN, "emailsOnly": True, "d": 'gte=0d'}
    ).json()

    assert jzon['hits'] == 6

    check_access({"mid": 'c396ps3p5pb05srb4269dzcg9j7sof42', "private": False}, None)

    text = mgmt_get_text({"action": 'hide', "document": "c396ps3p5pb05srb4269dzcg9j7sof42"}, admin_cookies)
    assert text == "Hid 1 emails from archives."

    jzon = requests.get(
        f"{API_BASE}/stats.lua",
        params={"list": TEST_LIST, "domain": TEST_DOMAIN, "emailsOnly": True, "d": 'gte=0d'}
    ).json()
    assert jzon['hits'] == 5



    text = mgmt_get_text({"action": 'unhide', "document": "c396ps3p5pb05srb4269dzcg9j7sof42"}, admin_cookies)
    assert text == "Unhid 1 emails from archives."

    jzon = requests.get(
        f"{API_BASE}/stats.lua",
        params={"list": TEST_LIST, "domain": TEST_DOMAIN, "emailsOnly": True, "d": 'gte=0d'}
    ).json()
    assert jzon['hits'] == 6

    check_access({"mid": 'c396ps3p5pb05srb4269dzcg9j7sof42', "private": False}, None)

def xtest_mgmt_get():
    """This test causes the source for an entry to be hidden"""
    admin_cookies = get_cookies('admin')

    jzon = requests.get(
        f"{API_BASE}/stats.lua",
        params={"list": TEST_LIST, "domain": TEST_DOMAIN, "emailsOnly": True, "d": 'gte=0d'}
    ).json()

    assert jzon['hits'] == 6

    text = mgmt_get_text(
        {
            "action": 'edit', "document": "c396ps3p5pb05srb4269dzcg9j7sof42",
            "from": '', "subject": '', "list": 'users.ponymail.apache.org', "body": 'body', "private": False,
        },
        admin_cookies
        )
    assert text == "Email successfully saved"

