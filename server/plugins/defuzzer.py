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

import calendar
import re
import shlex
import typing

"""
This is the query de-fuzzer library for Foal.
It turns a URL search query into an ES query

"""


def defuzz(formdata: dict, nodate: bool = False, list_override: typing.Optional[str] = None) -> dict:
    # Default to 30 day date range
    daterange = {"gt": "now-30d", "lt": "now+1d"}

    # Custom date range?
    # If a month is the only thing, fake start and end
    if "date" in formdata and "e" not in formdata:
        formdata["s"] = formdata["date"]
        formdata["e"] = formdata["date"]
    # classic start and end month params
    if "s" in formdata and "e" in formdata:
        if not re.match(r"\d{4}-\d{1,2}$", formdata["s"]):
            raise ValueError("Keyword 's' must be of type YYYY-MM")
        if not re.match(r"\d{4}-\d{1,2}$", formdata["e"]):
            raise ValueError("Keyword 'e' must be of type YYYY-MM")
        syear, smonth = formdata["s"].split("-", 1)
        eyear, emonth = formdata["e"].split("-", 1)
        _estart, eend = calendar.monthrange(int(eyear), int(emonth))
        daterange = {
            "gt": "%04u/%02u/01 00:00:00" % (int(syear), int(smonth)),
            "lt": "%04u/%02u/%02u 23:59:59" % (int(eyear), int(emonth), eend),
        }
    # days ago to start, and number of days to match
    elif "dfrom" in formdata and "dto" in formdata:
        dfrom = formdata["dfrom"]
        dto = formdata["dto"]
        if re.match(r"\d+$", dfrom) and re.match(r"\d+$", dto):
            ef = int(dfrom)
            et = int(dto)
            if ef > 0 and et > 0:
                if et > ef:
                    et = ef # avoid overruning into the future
                daterange = { 
                    "gte": "now-%dd" % ef,
                    "lte": "now-%dd" % (ef - et),
                }
        else:
            raise ValueError("Keywords 'dfrom' and 'dto' must be numeric")

    # Advanced date formatting
    elif "d" in formdata:
        # The more/less than N days/weeks/months/years ago
        m = re.match(r"^(lte|gte)=([0-9]+[Mwyd])$", formdata["d"])
        if m:
            t = m.group(1)
            r = m.group(2)
            if t == "lte" and r:
                daterange = {"gt": "now-%s" % r}
            elif t == "gte" and r:
                daterange = {"lt": "now-%s" % r}
        else:
            # simple one month listing
            m = re.match(r"^(\d\d\d\d-\d+)$", formdata["d"])
            if m:
                xdate = m.group(1)
                dyear, dmonth = xdate.split("-", 1)
                daterange = {
                    "gte": "%04u-%02u-01||/M" % (int(dyear), int(dmonth)),
                    "lte": "%04u-%02u-01||/M" % (int(dyear), int(dmonth)),
                    "format": "yyyy-MM-dd",
                }
            else:
                # dfr and dto defining a time span
                m = re.match(r"^dfr=(\d\d\d\d-\d+-\d+)\|dto=(\d\d\d\d-\d+-\d+)$", formdata["d"])
                if m:
                    dfr = m.group(1)
                    dto = m.group(2)
                    syear, smonth, sday = dfr.split("-", 2)
                    eyear, emonth, eday = dto.split("-", 2)
                    daterange = {
                        "gt": "%04u/%02u/%02u 00:00:00" % (int(syear), int(smonth), int(sday)),
                        "lt": "%04u/%02u/%02u 23:59:59" % (int(eyear), int(emonth), int(eday)),
                    }

    # List parameter(s)
    if list_override:  # Certain requests use the full list ID as a single variable. Allow for that if so.
        if not list_override.count("@") == 1:
            raise ValueError("list_override must contain exactly one @ character")
        listname, fqdn = list_override.split("@", 1)
    else:
        fqdn = formdata.get("domain", '')  # Must be provided
        listname = formdata.get("list", '')  # Must be provided
    if not fqdn:
        raise ValueError("You must specify a domain part of the mailing list(s) to search, or * for wildcard search.")
    if not listname:
        raise ValueError("You must specify a list part of the mailing list(s) to search, or * for wildcard search.")
    if "@" in listname:
        raise ValueError("The list component of the List ID(s) cannot contain @, please use both list and domain keywords for searching.")
    list_raw = "<%s.%s>" % (listname, fqdn)

    # Default is to look in a specific list
    query_list_hash: typing.Dict = {"term": {"list_raw": list_raw}}

    # *@fqdn match?
    if listname == "*" and fqdn != "*":
        query_list_hash = {"wildcard": {"list_raw": {"value": "*.%s>" % fqdn}}}

    # listname@* match?
    if listname != "*" and fqdn == "*":
        query_list_hash = {"wildcard": {"list_raw": "<%s.*>" % listname}}

    # *@* ??
    if listname == "*" and fqdn == "*":
        query_list_hash = {"wildcard": {"list_raw": "*"}}

    must = [query_list_hash]
    must_not = []

    # Append date range if not excluded
    if not nodate:
        must.append({"range": {"date": daterange}})

    # Query string search:
    # - foo bar baz: find emails with these words
    # - orange -apples: fond email with oranges but not apples
    # - "this sentence": find emails with this exact string
    if "q" in formdata:
        qs = formdata["q"].replace(":", "")
        try:
            bits = shlex.split(qs)
        except ValueError:  # Uneven number of quotes, default to split on whitespace instead
            bits = qs.split()

        query_should_match = []
        query_should_not_match = []

        for bit in bits:
            force_positive = False
            # Translate -- into a positive '-', so you can find "-1" etc
            if bit[0:2] == "--":
                force_positive = True
                bit = bit[1:]
            # Negatives
            if bit[0] == "-" and not force_positive:
                query_should_not_match.append(bit[1:])
            # Positives
            else:
                query_should_match.append(bit)

        if query_should_match:
            query_should_match_expanded = []
            for x in query_should_match:
                query_should_match_expanded.append(
                    {
                        "bool": {
                            "should": [
                                {
                                    "multi_match": {
                                        "fields": ["from", "body", "subject"],
                                        "query": x,
                                        "type": "phrase",
                                    },
                                },
                            ]
                        }
                    }
                )
            xmust = {"bool": {"minimum_should_match": len(query_should_match), "should": query_should_match_expanded}}
            must.append(xmust)

        for x in query_should_not_match:
            must_not.append(
                {
                    "match": {
                        "subject": x,
                    }
                }
            )
            must_not.append(
                {
                    "match": {
                        "from": x,
                    }
                }
            )
            must_not.append(
                {
                    "match": {
                        "body": x,
                    }
                }
            )

    # Header parameters
    for header in ["from", "subject", "body", "to"]:
        hname = "header_%s" % header
        if hname in formdata:
            hvalue = formdata[hname]
            must.append({"match_phrase": {header: hvalue}})

    query_as_bool = {"must": must}

    if must_not:
        query_as_bool["must_not"] = must_not

    return query_as_bool
