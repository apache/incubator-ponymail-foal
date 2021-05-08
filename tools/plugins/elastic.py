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
    common elasticsearch database setup
    also adds defaults for most methods
"""

import sys
import logging
import certifi
import os
from . import ponymailconfig

try:
    from elasticsearch import Elasticsearch, helpers
    from elasticsearch import VERSION as ES_VERSION
    from elasticsearch import ConnectionError as ES_ConnectionError
except ImportError as e:
    sys.exit(
        "Sorry, you need to install the elasticsearch module from pip first. (%s)"
        % str(e)
    )


class Elastic:
    db_mbox:            str
    db_source:          str
    db_attachment:      str
    db_account:         str
    db_session:         str
    db_notification:    str
    db_mailinglist:     str

    def __init__(self, dbname=None):
        # Fetch config
        config = ponymailconfig.PonymailConfig()

        # Set default names for all indices we use
        self.dbname = config.get('elasticsearch', 'dbname', fallback='ponymail')
        self.db_mbox = self.dbname + '-mbox'
        self.db_source = self.dbname + '-source'
        self.db_account = self.dbname + '-account'
        self.db_attachment = self.dbname + '-attachment'
        self.db_session = self.dbname + '-session'
        self.db_notification = self.dbname + '-notification'
        self.db_mailinglist = self.dbname + '-mailinglist'
        self.db_auditlog = self.dbname + '-auditlog'
        self.db_version = 0

        dburl = config.get('elasticsearch', 'dburl', fallback=None)
        if not dburl:
            ssl = config.get('elasticsearch', 'ssl', fallback=False)
            uri = config.get('elasticsearch', 'uri', fallback='')
            auth = None
            if config.has_option('elasticsearch', 'user'):
                auth = (
                    config.get('elasticsearch', 'user'),
                    config.get('elasticsearch', 'password')
                )
            dburl = {
                "host": config.get('elasticsearch', 'hostname', fallback='localhost'),
                "port": config.get('elasticsearch', 'port', fallback=9200),
                "use_ssl": ssl,
                "url_prefix": uri,
                "auth": auth,
                "ca_certs": certifi.where(),
            }

        # Always allow this to be set; will be replaced as necessary by wait_for_active_shards
        self.consistency = config.get("elasticsearch", "write", fallback="quorum")

        # elasticsearch logs lots of warnings on retries/connection failure
        logging.getLogger("elasticsearch").setLevel(logging.ERROR)

        #         # add debug
        #         trace = logging.getLogger("elasticsearch.trace")
        #         trace.setLevel(logging.DEBUG)
        #         # create console handler
        #         consoleHandler = logging.StreamHandler()
        #         trace.addHandler(consoleHandler)

        self.es = Elasticsearch(
            [
                dburl
            ],
            max_retries=5,
            retry_on_timeout=True,
        )

        es_engine_major = self.engineMajor()
        if es_engine_major in [7, 8]:
            self.wait_for_active_shards = config.get("elasticsearch", "wait", fallback=1)
        else:
            raise Exception("Unexpected elasticsearch version ", es_engine_major)

        # Mimic ES hierarchy: es.indices.xyz()
        self.indices = _indices_wrap(self)

    def libraryVersion(self):
        return ES_VERSION

    def libraryMajor(self):
        return ES_VERSION[0]

    def engineVersion(self):
        if not self.db_version:
            try:
                self.db_version = self.es.info()["version"]["number"]
            except ES_ConnectionError:
                # default if cannot connect; allows retry
                return "0.0.0"
        return self.db_version

    def engineMajor(self):
        return int(self.engineVersion().split(".")[0])

    def getdbname(self):
        return self.dbname

    def search(self, **kwargs):
        return self.es.search(index=self.dbname, **kwargs)

    def index(self, **kwargs):
        kwargs["wait_for_active_shards"] = self.wait_for_active_shards
        kwargs["doc_type"] = "_doc"
        return self.es.index(**kwargs)

    def update(self, **kwargs):
        return self.es.update(index=self.dbname, **kwargs)

    def scan(self, scroll="3m", size=100, **kwargs):
        return self.es.search(
            index=self.dbname, search_type="scan", size=size, scroll=scroll, **kwargs
        )

    def scan_and_scroll(self, scroll="3m", size=100, **kwargs):
        """ Run a backwards compatible scan/scroll, passing an iterator
            that returns one page of hits per iteration. This
            incorporates es.scroll for continuous iteration, and thus the
            scroll() does NOT need to be called at all by the calling
            process. """
        results = self.es.search(index=self.dbname, size=size, scroll=scroll, **kwargs)
        if results["hits"].get("hits", []):  # Might not be there in 2.x?
            yield results

        # While we have hits waiting, scroll...
        scroll_size = results["hits"]["total"]
        while scroll_size > 0:
            results = self.scroll(scroll_id=results["_scroll_id"], scroll=scroll)
            scroll_size = len(
                results["hits"]["hits"]
            )  # If >0, try another scroll next.
            yield results

    def get(self, **kwargs):
        return self.es.get(index=self.dbname, **kwargs)

    def scroll(self, **kwargs):
        return self.es.scroll(**kwargs)

    def info(self, **kwargs):
        return self.es.info(**kwargs)

    def bulk(self, actions, **kwargs):
        return helpers.bulk(self.es, actions, **kwargs)

    def clear_scroll(self, *args, **kwargs):
        """
            Call this to release the scroll id and its resources

            It looks like the Python library already releases the SID
            if the caller scrolls to the end of the results, so only need to call this
            when terminating scrolling early.
        """
        return self.es.clear_scroll(*args, **kwargs)


class _indices_wrap(object):
    """
        Wrapper for the ES indices methods we use
    """

    def __init__(self, parent):
        self.es = parent.es

    def exists(self, *args, **kwargs):
        return self.es.indices.exists(*args, **kwargs)
