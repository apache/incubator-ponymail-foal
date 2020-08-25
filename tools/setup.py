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

import argparse
import importlib.util
import logging
import os.path
import shutil
import sys

if sys.version_info <= (3, 7):
    print("This script requires Python 3.8 or higher")
    sys.exit(-1)

# Check for all required python packages
wanted_pkgs = [
    "elasticsearch",  # used by setup.py, archiver.py and elastic.py
    "formatflowed",  # used by archiver.py
    "netaddr",  # used by archiver.py
    "certifi",  # used by archiver.py and elastic.py
]

missing_pkgs = list(wanted_pkgs)  # copy to avoid corruption
for pkg in wanted_pkgs:
    if importlib.util.find_spec(pkg):
        missing_pkgs.remove(pkg)

if missing_pkgs:
    print("It looks like you need to install some python modules first")
    print("The following packages are required: ")
    for pkg in missing_pkgs:
        print(" - %s" % pkg)
    print("You may use your package manager, or run the following command:")
    print("pip3 install %s" % " ".join(missing_pkgs))
    sys.exit(-1)


# at this point we can assume elasticsearch is present
from elasticsearch import VERSION as ES_VERSION
from elasticsearch import ConnectionError as ES_ConnectionError
from elasticsearch import Elasticsearch, ElasticsearchException

ES_MAJOR = ES_VERSION[0]

# CLI arg parsing
parser = argparse.ArgumentParser(description="Command line options.")

parser.add_argument(
    "--defaults", dest="defaults", action="store_true", help="Use default settings"
)
parser.add_argument("--dbprefix", dest="dbprefix")
parser.add_argument(
    "--clobber",
    dest="clobber",
    action="store_true",
    help="Allow overwrite of ponymail.yaml & ../site/api/lib/config.lua (default: create *.tmp if either exists)",
)
parser.add_argument("--dbhost", dest="dbhost", type=str, help="ES backend hostname")
parser.add_argument("--dbport", dest="dbport", type=str, help="DB port")
parser.add_argument("--dbname", dest="dbname", type=str, help="ES DB prefix")
parser.add_argument("--dbshards", dest="dbshards", type=int, help="DB Shard Count")
parser.add_argument(
    "--dbreplicas", dest="dbreplicas", type=int, help="DB Replica Count"
)
parser.add_argument(
    "--mailserver",
    dest="mailserver",
    type=str,
    help="Host name of outgoing mail server",
)
parser.add_argument(
    "--mldom", dest="mldom", type=str, help="Domains to accept mail for via UI"
)
parser.add_argument(
    "--wordcloud", dest="wc", action="store_true", help="Enable word cloud"
)
parser.add_argument(
    "--skiponexist",
    dest="soe",
    action="store_true",
    help="Skip setup if ES index exists",
)
parser.add_argument(
    "--noindex",
    dest="noi",
    action="store_true",
    help="Don't create ElasticSearch indices, assume they exist",
)
parser.add_argument(
    "--nocloud", dest="nwc", action="store_true", help="Do not enable word cloud"
)
parser.add_argument(
    "--generator",
    dest="generator",
    type=str,
    help="Document ID Generator to use (legacy, medium, cluster, full)",
)
args = parser.parse_args()

print("Welcome to the Pony Mail setup script!")
print("Let's start by determining some settings...")
print("")


hostname = ""
port = 0
dbname = ""
mlserver = ""
mldom = ""
wc = ""
genname = ""
wce = False
shards = 0
replicas = -1
urlPrefix = None
nonce = None

# If called with --defaults (like from Docker), use default values
if args.defaults:
    hostname = "localhost"
    port = 9200
    dbname = "ponymail"
    mlserver = "localhost"
    mldom = "example.org"
    wc = "Y"
    wce = True
    shards = 1
    replicas = 0
    genname = "cluster"
    urlPrefix = ""
    nonce = None

# Accept CLI args, copy them
if args.dbprefix:
    urlPrefix = args.dbprefix
if args.dbhost:
    hostname = args.dbhost
if args.dbport:
    port = int(args.dbport)
if args.dbname:
    dbname = args.dbname
if args.mailserver:
    mlserver = args.mailserver
if args.mldom:
    mldom = args.mldom
if args.wc:
    wc = args.wc
if args.nwc:
    wc = False
if args.dbshards:
    shards = args.dbshards
if args.dbreplicas:
    replicas = args.dbreplicas
if args.generator:
    genname = args.generator

while hostname == "":
    hostname = input(
        "What is the hostname of the ElasticSearch server? (e.g. localhost): "
    )

while urlPrefix == None:
    urlPrefix = input("Database URL prefix if any (hit enter if none): ")

while port < 1:
    try:
        port = int(input("What port is ElasticSearch listening on? (normally 9200): "))
    except ValueError:
        pass

while dbname == "":
    dbname = input("What would you like to call the mail index (e.g. ponymail): ")

while mlserver == "":
    mlserver = input(
        "What is the hostname of the outgoing mailserver? (e.g. mail.foo.org): "
    )

while mldom == "":
    mldom = input(
        "Which domains would you accept mail to from web-replies? (e.g. foo.org or *): "
    )

while wc == "":
    wc = input("Would you like to enable the word cloud feature? (Y/N): ")
    if wc.lower() == "y":
        wce = True

while genname == "":
    gens = ["dkim", "full"]
    print("Please select a document ID generator:")
    print(
        "1  [RECOMMENDED] DKIM/RFC-6376: Short SHA3 hash useful for cluster setups with permalink usage"
    )
    print(
        "2  FULL: Full message digest with MTA trail. Not recommended for clustered setups."
    )
    try:
        gno = int(input("Please select a generator [1-2]: "))
        if gno <= len(gens) and gens[gno - 1]:
            genname = gens[gno - 1]
    except ValueError:
        pass

if genname == "dkim":
    print(
        "DKIM hasher chosen. It is recommended you set a cryptographic nonce for this generator, though not required."
    )
    print(
        "If you set a nonce, you will need this same nonce for future installations if you intend to preserve "
    )
    print("permalinks from imported messages.")
    nonce = (
        input("Enter your nonce or hit [enter] to continue without a nonce: ") or None
    )

while shards < 1:
    try:
        shards = int(input("How many shards for the ElasticSearch index? "))
    except ValueError:
        pass

while replicas < 0:
    try:
        replicas = int(input("How many replicas for each shard? "))
    except ValueError:
        pass

print("Okay, I got all I need, setting up Pony Mail...")


def createIndex():
    # Check if index already exists
    if es.indices.exists(dbname + "-mbox"):
        if args.soe:
            print(
                "ElasticSearch indices with prefix '%s' already exists and SOE set, exiting quietly"
                % dbname
            )
            sys.exit(0)
        else:
            print("Error: Existing ElasticSearch indices with prefix '%s' already exist!" % dbname)
            sys.exit(-1)

    print(f"Creating indices {dbname}-*...")

    settings = {"number_of_shards": shards, "number_of_replicas": replicas}

    mappings = {
        "mbox": {
            "properties": {
                "@import_timestamp": {
                    "type": "date",
                    "format": "yyyy/MM/dd HH:mm:ss||yyyy/MM/dd",
                },
                "attachments": {
                    "properties": {
                        "content_type": {"type": "keyword",},
                        "filename": {"type": "keyword",},
                        "hash": {"type": "keyword",},
                        "size": {"type": "long"},
                    }
                },
                "body": {"type": "text"},
                "cc": {"type": "text"},
                "date": {
                    "type": "date",
                    "store": True,
                    "format": "yyyy/MM/dd HH:mm:ss",
                },
                "epoch": {"type": "long",},  # number of seconds since the epoch
                "from": {"type": "text"},
                "from_raw": {"type": "keyword",},
                "in-reply-to": {"type": "keyword",},
                "list": {"type": "text"},
                "list_raw": {"type": "keyword",},
                "message-id": {"type": "keyword",},
                "mid": {"type": "keyword"},
                "private": {"type": "boolean"},
                "permalink": {"type": "keyword"},
                "references": {"type": "text"},
                "subject": {"type": "text", "fielddata": True},
                "to": {"type": "text"},
            }
        },
        "attachment": {"properties": {"source": {"type": "binary"}}},
        "source": {
            "properties": {
                "source": {"type": "binary"},
                "message-id": {"type": "keyword",},
                "permalink": {"type": "keyword"},
                "mid": {"type": "keyword"},
            }
        },
        "mailinglist": {
            "properties": {
                "description": {"type": "keyword",},
                "list": {"type": "keyword",},
                "name": {"type": "keyword",},
            }
        },
        "account": {
            "properties": {
                "cid": {"type": "keyword",},
                "credentials": {
                    "properties": {
                        "altemail": {"type": "object"},
                        "email": {"type": "keyword",},
                        "fullname": {"type": "keyword",},
                        "uid": {"type": "keyword",},
                    }
                },
                "internal": {
                    "properties": {
                        "cookie": {"type": "keyword",},
                        "ip": {"type": "keyword",},
                        "oauth_used": {"type": "keyword",},
                    }
                },
                "request_id": {"type": "keyword",},
            }
        },
        "notification": {
            "properties": {
                "date": {
                    "type": "date",
                    "store": True,
                    "format": "yyyy/MM/dd HH:mm:ss",
                },
                "epoch": {"type": "long"},
                "from": {"type": "text",},
                "in-reply-to": {"type": "keyword",},
                "list": {"type": "text",},
                "message-id": {"type": "keyword",},
                "mid": {"type": "text",},
                "private": {"type": "boolean"},
                "recipient": {"type": "keyword",},
                "seen": {"type": "long"},
                "subject": {"type": "keyword",},
                "to": {"type": "text",},
                "type": {"type": "keyword",},
            }
        },
    }

    for index, mappings in mappings.items():
        res = es.indices.create(
            index=f"{dbname}-{index}", body={"mappings": mappings, "settings": settings}
        )

        print(f"Index {dbname}-{index} created! %s " % res)


# we need to connect to database to determine the engine version
es = Elasticsearch(
    [{"host": hostname, "port": port, "use_ssl": False, "url_prefix": urlPrefix}],
    max_retries=5,
    retry_on_timeout=True,
)

# elasticsearch logs lots of warnings on retries/connection failure
logging.getLogger("elasticsearch").setLevel(logging.ERROR)

try:
    DB_VERSION = es.info()["version"]["number"]
except ES_ConnectionError:
    print("WARNING: Connection error: could not determine the engine version.")
    DB_VERSION = "0.0.0"

DB_MAJOR = int(DB_VERSION.split(".")[0])
print(
    "Versions: library %d (%s), engine %d (%s)"
    % (ES_MAJOR, ".".join(map(str, ES_VERSION)), DB_MAJOR, DB_VERSION)
)
if DB_MAJOR < 7:
    print("This version of Pony Mail requires ElasticSearch 7.x or higher")

if not DB_MAJOR == ES_MAJOR:
    print("WARNING: library version does not agree with engine version!")

if DB_MAJOR == 0:  # not known
    if args.noi:
        # allow setup to be used without engine running
        print(
            "Could not determine the engine version. Assume it is the same as the library version."
        )
        DB_MAJOR = ES_MAJOR
    else:
        # if we cannot connect to get the version, we cannot create the index later
        print("Could not connect to the engine. Fatal.")
        sys.exit(1)

if not args.noi:
    try:
        createIndex()
    except ElasticsearchException as e:
        print("Index creation failed: %s" % e)
        sys.exit(1)

ponymail_cfg = "ponymail.yaml"
if not args.clobber and os.path.exists(ponymail_cfg):
    print("%s exists and clobber is not set" % ponymail_cfg)
    ponymail_cfg = "ponymail.yaml.tmp"

print("Writing importer config (%s)" % ponymail_cfg)

with open(ponymail_cfg, "w") as f:
    f.write(
        """
---
###############################################################
# A ponymail.yaml is needed to run this project. This sample config file was
# originally generated by tools/setup.py.
# 
# Run the tools/setup.py script and a ponymail.yaml which looks a lot like this 
# one will be generated. If, for whatever reason, that script is not working 
# for you, you may use this ponymail.cfg as a starting point.
# 
# Contributors should strive to keep this sample updated. One way to do this 
# would be to run the tools/setup.py, rename the generated config to
# ponymail.cfg.sample, and then pasting this message or a modified form of 
# this message at the top.
###############################################################

###############################################################
# Pony Mail Configuration file


# Main ES configuration
elasticsearch:
    hostname:               %s
    dbname:                 %s
    port:                   %u
    ssl:                    false
    #uri:                   url_prefix
    #user:                  username
    #password:              password
    #wait:                  active shard count
    #backup:                database name

archiver:
    #generator:             dkim|full (dkim recommended)
    generator:              %s
    nonce:                  %s

debug:
    #cropout:               string to crop from list-id

            """
        % (hostname, dbname, port, genname, nonce or "~")
    )

print("Copying sample JS config to config.js (if needed)...")
if not os.path.exists("../site/js/config.js") and os.path.exists(
    "../site/js/config.js.sample"
):
    shutil.copy("../site/js/config.js.sample", "../site/js/config.js")


print("All done, Pony Mail should...work now :)")
print(
    "If you are using an external mail inbound server, \nmake sure to copy the contents of this tools directory to it"
)
