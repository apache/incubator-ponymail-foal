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

class ServerConfig:
    port: int
    ip: str

    def __init__(self, subyaml: dict):
        self.ip = subyaml.get("bind", "0.0.0.0")
        self.port = int(subyaml.get("port", 8080))


class TaskConfig:
    refresh_rate: int

    def __init__(self, subyaml: dict):
        self.refresh_rate = int(subyaml.get("refresh_rate", 150))


class UIConfig:
    wordcloud: bool
    mailhost: str
    sender_domains: str
    traceback: bool
    mgmt_enabled: bool
    focus_domain: str
    fully_delete: bool

    def __init__(self, subyaml: dict):
        self.wordcloud = bool(subyaml.get("wordcloud", False))
        self.mailhost = subyaml.get("mailhost", "")  # Default to nothing (disabled)
        self.sender_domains = subyaml.get(
            "sender_domains", ""
        )  # Default to nothing (disabled)
        # Default to spitting out traceback to web clients
        # Set to false in yaml to redirect to stderr instead.
        self.traceback = subyaml.get("traceback", True)
        self.mgmt_enabled = bool(subyaml.get("mgmtconsole", False))  # Whether to enable online mgmt component or not
        self.fully_delete = bool(subyaml.get("allow_delete", False))  # Whether to enforce full expunging of deleted emails
        # Default to all lists, "*". Use "" for host. Wildcard subdomain globs also supported
        self.focus_domain = subyaml.get("focus_domain", "*")


class OAuthConfig:
    authoritative_domains: list
    admins: list
    google_client_id: str
    github_client_id: str
    github_client_secret: str
    providers: dict # generic providers

    def __init__(self, subyaml: dict):
        self.authoritative_domains = subyaml.get("authoritative_domains", [])
        self.admins = subyaml.get("admins", [])
        self.google_client_id = subyaml.get("google_client_id", "")
        self.github_client_id = subyaml.get("github_client_id", "")
        self.github_client_secret = subyaml.get("github_client_secret", "")
        self.providers = subyaml.get("providers", {})


class TokensConfig:
    """Configuration for long-term API tokens (see plugins/token.py)."""

    enabled: bool
    default_age: int  # seconds; 0 == token never expires
    max_age: int  # seconds; 0 == no upper bound enforced
    max_tokens: int  # per-account cap on the number of live tokens
    cache_ttl: int  # seconds to cache token auth in memory; 0 == disabled
    cache_max: int  # max number of entries in the in-memory token auth cache
    revoke_on_identity_change: bool  # drop a user's tokens when their OAuth identity changes

    def __init__(self, subyaml: dict):
        self.enabled = bool(subyaml.get("enabled", False))
        # Default to a 30-day lifetime when the user does not request one.
        self.default_age = int(subyaml.get("default_lifetime", 86400 * 30))
        self.max_age = int(subyaml.get("max_lifetime", 0))
        self.max_tokens = int(subyaml.get("max_tokens", 25))
        # Optional in-memory cache of token auth to avoid a database lookup on
        # every request. Disabled by default (0) because caching delays the
        # effect of revocation/expiry by up to this many seconds.
        self.cache_ttl = int(subyaml.get("cache_ttl", 0))
        # Upper bound on cache entries; the cache is flushed if it is exceeded,
        # so token auth cannot grow memory without limit.
        self.cache_max = int(subyaml.get("cache_max", 10000))
        # When a user logs in and their OAuth identity/permissions differ from
        # what was stored (e.g. after a credential reset or a group-membership
        # change upstream), automatically revoke all of that user's API tokens
        # so credentials minted under the old identity cannot be reused.
        self.revoke_on_identity_change = bool(subyaml.get("revoke_on_identity_change", True))


class DBConfig:
    dburl: str
    hostname: str
    port: int
    secure: bool
    url_prefix: str
    db_prefix: str
    max_hits: int
    max_lists: int
    pool_size: int

    def __init__(self, subyaml: dict):
        self.dburl = str(subyaml.get("dburl", ""))
        self.hostname = str(subyaml.get("server", "localhost"))
        self.port = int(subyaml.get("port", 9200))
        self.secure = bool(subyaml.get("secure", False))
        self.url_prefix = subyaml.get("url_prefix", "")
        self.db_prefix = str(subyaml.get("db_prefix", "ponymail"))
        self.max_hits = int(subyaml.get("max_hits", 5000))
        self.max_lists = int(subyaml.get("max_lists", 8192))
        self.pool_size = int(subyaml.get("pool_size", 15))


class Configuration:
    server: ServerConfig
    database: DBConfig
    tasks: TaskConfig
    oauth: OAuthConfig
    ui: UIConfig
    tokens: TokensConfig

    def __init__(self, yml: dict):
        self.server = ServerConfig(yml.get("server", {}))
        self.database = DBConfig(yml.get("database", {}))
        self.tasks = TaskConfig(yml.get("tasks", {}))
        self.oauth = OAuthConfig(yml.get("oauth", {}))
        self.ui = UIConfig(yml.get("ui", {}))
        self.tokens = TokensConfig(yml.get("tokens", {}))


class InterData:
    """
        A mix of various global variables used throughout processes
    """

    lists: dict
    sessions: dict
    activity: dict
    token_cache: dict

    def __init__(self):
        self.lists = {}
        self.sessions = {}
        self.activity = {}
        self.token_cache = {}  # token hash -> cached auth (only used if tokens.cache_ttl > 0)
