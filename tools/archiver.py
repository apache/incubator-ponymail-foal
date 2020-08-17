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

""" Publish notifications about mails to pony mail.

Copy this file to $mailman_plugin_dir/mailman_ponymail/__init__.py
Also copy ponymail.cfg to that dir.
Enable the module by adding the following to your mailman.cfg file::

[archiver.ponymail]
# The class implementing the IArchiver interface.
class: mailman_ponymail_plugin.Archiver
enable: yes

and by adding the following to ponymail.cfg:

[mailman]
plugin: true

OR, to use the STDIN version (non-MM3 mailing list managers),
sub someone to the list(s) and add this to their .forward file:
"|/usr/bin/env python3 /path/to/archiver.py"

"""

import argparse
import base64
import collections
import email.header
import email.utils
import fnmatch
import hashlib
import json
import logging
import os
import re
import sys
import time
import traceback
import typing
import uuid

import certifi
import chardet
import formatflowed
import netaddr
import yaml

import plugins.generators
import plugins.elastic
import elasticsearch

# Fetch config from same dir as archiver.py
config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ponymail.yaml")
config = yaml.safe_load(open(config_path))

# Set some vars before we begin
archiver_generator = config["archiver"].get(
    "generator", "full"
)  # Fall back to full hashing if nothing is set.
logger = None
ES_MAJOR = elasticsearch.VERSION[0]


# If MailMan is enabled, import and set it up
if config.get("mailman") and config["mailman"].get("plugin"):
    from mailman.interfaces.archiver import ArchivePolicy, IArchiver
    from zope.interface import implementer

    logger = logging.getLogger("mailman.archiver")

# Access URL once archived
aURL = config.get("archiver", {}).get("baseurl")


def encode_base64(buff: bytes) -> str:
    """ Convert bytes to base64 as text string (no newlines) """
    return base64.standard_b64encode(buff).decode("ascii", "ignore")


def parse_attachment(
    part: email.message.Message,
) -> typing.Tuple[typing.Optional[dict], typing.Optional[str]]:
    """
    Parses an attachment in an email, turns it into a dict with a content-type, sha256 digest, file size and file name.
    Also returns the attachment contents as base64 encoded string.
    :param part: The message part to parse
    :return: attachment info and contents as b64 string
    """
    cd = part.get("Content-Disposition", None)
    if cd:
        # Use str() in case the name is not in ASCII.
        # In such cases, the get() method returns a Header not a string
        dispositions = str(cd).strip().split(";")
        cdtype = dispositions[0].lower()
        if cdtype == "attachment" or cdtype == "inline":
            fd = part.get_payload(decode=True)
            # Allow for empty string
            if fd is None:
                return None, None
            filename = part.get_filename()
            if filename:
                attachment = {
                    "content_type": part.get_content_type(),
                    "size": len(fd),
                    "filename": filename,
                }
                h = hashlib.sha256(fd).hexdigest()
                b64 = encode_base64(fd)
                attachment["hash"] = h
                return attachment, b64  # Return meta data and contents separately
    return None, None


def normalize_lid(lid: str) -> str:  # N.B. Also used by import-mbox.py
    """ Ensures that a List ID is in standard form, i.e. <a.b.c.d> """
    # If of format "list name" <foo.bar.baz>
    # we crop away the description (#511)
    m = re.match(r'".*"\s+(.+)', lid)
    if m:
        lid = m.group(1)
    # Drop <> and anything before/after, if found
    m = re.search(r"<(.+)>", lid)
    if m:
        lid = m.group(1)
    # Belt-and-braces: remove possible extraneous chars
    lid = "<%s>" % lid.strip(" <>").replace("@", ".")
    if not re.match(r"^<.+\..+>$", lid):
        print("Invalid list-id %s" % lid)
        sys.exit(-1)
    return lid


def message_attachments(msg: email.message.Message) -> typing.Tuple[list, dict]:
    """
    Parses an email and returns all attachments found as a tuple of metadata and contents
    :param msg: The email to parse
    :return: a tuple of attachment metadata and their content
    """
    attachments = []
    contents = {}
    for part in msg.walk():
        part_meta, part_file = parse_attachment(part)
        if part_meta:
            attachments.append(part_meta)
            contents[part_meta["hash"]] = part_file
    return attachments, contents


class Body:
    def __init__(self, part: email.message.Message):
        self.content_type = part.get_content_type()
        self.charsets = set([part.get_charset()])  # Part's charset
        self.charsets.update(part.get_charsets())  # Parent charsets as fallback
        self.character_set = "utf-8"
        self.string = None
        self.flowed = True if "format=flowed" in part.get("content-type", "") else False
        contents = part.get_payload(decode=True)
        if contents is not None:
            for cs in self.charsets:
                if cs:
                    try:
                        self.string = contents.decode(cs)
                        self.character_set = cs
                    except UnicodeDecodeError:
                        pass
            if not self.string:
                self.string = contents.decode("utf-8", errors="replace")

    def __str__(self):
        return self.string or "None"

    def __len__(self):
        return len(self.string or "")

    def encode(self, charset="utf-8", errors="strict"):
        return self.string.encode(charset, errors=errors)

    def unflow(self):
        if self.string:
            if self.flowed:
                return formatflowed.convertToWrapped(
                    self.string.encode(self.character_set, errors="ignore"),
                    wrap_fixed=False,
                    character_set=self.character_set,
                )
        return self.string


class Archiver(object):  # N.B. Also used by import-mbox.py
    """The general archiver class. Compatible with MailMan3 archiver classes."""

    if config.get("mailman") and config["mailman"].get("plugin"):
        implementer(IArchiver)

    # This is a list of headers which are stored in msg_metadata
    keys = [
        "archived-at",
        "delivered-to",
        "from",
        "cc",
        "content-type",
        "to",
        "date",
        "in-reply-to",
        "message-id",
        "subject",
        "references",
        # The following don't appear to be needed currently
        "x-message-id-hash",
        "x-mailman-rule-hits",
        "x-mailman-rule-misses",
    ]

    """ Intercept index calls and fix up consistency argument """

    def index(self, **kwargs):
        if ES_MAJOR in [5, 6, 7]:
            if kwargs.pop("consistency", None):  # drop the key if present
                if self.wait_for_active_shards:  # replace with wait if defined
                    kwargs["wait_for_active_shards"] = self.wait_for_active_shards
        return self.elastic.index(**kwargs)

    def __init__(self, generator=archiver_generator, parse_html=False, dump_dir=None):
        """ Just initialize ES. """
        self.html = parse_html
        self.generator = generator
        self.dump_dir = dump_dir
        self.cropout = config.get("debug", {}).get("cropout")
        if parse_html:
            import html2text

            self.html2text = html2text.html2text

    def message_body(
        self, msg: email.message.Message, verbose=False, ignore_body=None
    ) -> Body:
        """
            Fetches the proper text body from an email as an archiver.Body object
        :param msg: The email or part of it to examine for proper body
        :param verbose: Verbose output while parsing
        :param ignore_body: Optional bodies to ignore while parsing
        :return: archiver.Body object
        """
        body = None
        first_html = None
        for part in msg.walk():
            # can be called from importer
            if verbose:
                print("Content-Type: %s" % part.get_content_type())
            """
                Find the first body part and the first HTML part
                Note: cannot use break here because firstHTML is needed if len(body) <= 1
            """
            try:
                if not body and part.get_content_type() in [
                    "text/plain",
                    "text/enriched",
                ]:
                    body = Body(part)
                elif (
                    self.html
                    and not first_html
                    and part.get_content_type() == "text/html"
                ):
                    first_html = Body(part)
            except Exception as err:
                print(err)

        # this requires a GPL lib, user will have to install it themselves
        if first_html and (
            body is None
            or len(body) <= 1
            or (ignore_body and str(body).find(str(ignore_body)) != -1)
        ):
            content_type = "text/html"
            body = first_html
            body.string = self.html2text(body.string)
        return body

    def format_flowed(self, body, msg_metadata):
        if body and body.flowed:
            return formatflowed.decode(body.encode("utf-8"))
        else:
            return body

    # N.B. this is also called by import-mbox.py
    def compute_updates(
        self,
        args,
        lid: typing.Optional[str],
        private: bool,
        msg: email.message.Message,
        raw_msg: bytes,
    ) -> typing.Tuple[typing.Optional[dict], dict, dict, typing.Optional[str]]:
        """Determine what needs to be sent to the archiver.
        :param args: Command line arguments for the archiver
        :param lid: The list id
        :param private: Whether privately archived email or not (bool)
        :param msg: The message object
        :param raw_msg: The raw message bytes

        :return None if the message could not be parsed, otherwise a four-tuple consisting of:
                the digested email as a dict, its attachments, its metadata fields and any
                in-reply-to data found.
        """

        if not lid:
            lid = normalize_lid(msg.get("list-id"))
        if self.cropout:
            crops = self.cropout.split(" ")
            # Regex replace?
            if len(crops) == 2:
                lid = re.sub(crops[0], crops[1], lid)
            # Standard crop out?
            else:
                lid = lid.replace(self.cropout, "")

        def default_empty_string(value):
            return value and str(value) or ""

        msg_metadata = dict([(k, default_empty_string(msg.get(k))) for k in self.keys])
        mid = (
            hashlib.sha224(
                str("%s-%s" % (lid, msg_metadata["archived-at"])).encode("utf-8")
            ).hexdigest()
            + "@"
            + (lid if lid else "none")
        )
        for key in ["to", "from", "subject", "message-id"]:
            try:
                hval = ""
                if msg_metadata.get(key):
                    for t in email.header.decode_header(msg_metadata[key]):
                        if t[1] is None or t[1].find("8bit") != -1:
                            hval += str(
                                t[0].decode("utf-8") if type(t[0]) is bytes else t[0]
                            )
                        else:
                            hval += t[0].decode(t[1], errors="ignore")
                    msg_metadata[key] = hval
            except Exception as err:
                print("Could not decode headers, ignoring..: %s" % err)
        message_date = None
        try:
            message_date = email.utils.parsedate_tz(str(msg_metadata.get("date")))
        except ValueError:
            pass
        if not message_date and msg_metadata.get("archived-at"):
            message_date = email.utils.parsedate_tz(
                str(msg_metadata.get("archived-at"))
            )

        if not message_date:
            print(
                "Date (%s) seems totally wrong, using current UNIX epoch instead."
                % message_date
            )
            epoch = time.time()
        else:
            epoch = email.utils.mktime_tz(message_date)
        # message_date calculations are all done, prepare the index entry
        date_as_string = time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime(epoch))
        body = self.message_body(msg, verbose=args.verbose, ignore_body=args.ibody)

        attachments, contents = message_attachments(msg)
        irt = ""

        output_json = None

        if body is not None or attachments:
            pmid = mid
            try:
                mid = plugins.generators.generate(
                    self.generator, msg, body, lid, attachments, raw_msg
                )
            except Exception as err:
                if logger:
                    # N.B. use .get just in case there is no message-id
                    logger.warning(
                        "Could not generate MID: %s. MSGID: %s",
                        err,
                        msg_metadata.get("message-id", "?"),
                    )
                mid = pmid

            if "in-reply-to" in msg_metadata:
                try:
                    irt_original = msg_metadata["in-reply-to"]
                    if isinstance(irt_original, list):
                        irt = "".join(irt_original)
                    else:
                        irt = str(irt_original)
                    if irt:
                        irt = irt.strip()
                except ValueError:
                    irt = ""
            output_json = {
                "from_raw": msg_metadata["from"],
                "from": msg_metadata["from"],
                "to": msg_metadata["to"],
                "subject": msg_metadata["subject"],
                "message-id": msg_metadata["message-id"],
                "mid": mid,
                "cc": msg_metadata.get("cc"),
                "epoch": epoch,
                "list": lid,
                "list_raw": lid,
                "date": date_as_string,
                "private": private,
                "references": msg_metadata["references"],
                "in-reply-to": irt,
                "body": body.unflow(),
                "attachments": attachments,
            }

        return output_json, contents, msg_metadata, irt

    def archive_message(self, args, mlist, msg, raw_message):
        """Send the message to the archiver.

        :param args: Command line args (verbose, ibody)
        :param mlist: The IMailingList object.
        :param msg: The message object.
        :param raw_message: Raw message bytes

        :return (lid, mid)
        """

        lid = normalize_lid(mlist.list_id)

        private = False
        if hasattr(mlist, "archive_public") and mlist.archive_public is True:
            private = False
        elif hasattr(mlist, "archive_public") and mlist.archive_public is False:
            private = True
        elif (
            hasattr(mlist, "archive_policy")
            and mlist.archive_policy is not ArchivePolicy.public
        ):
            private = True

        ojson, contents, msg_metadata, irt = self.compute_updates(
            args, lid, private, msg, raw_message
        )
        sha3 = hashlib.sha3_256(raw_message).hexdigest()
        if not ojson:
            _id = msg.get("message-id") or msg.get("Subject") or msg.get("Date")
            raise Exception("Could not parse message %s for %s" % (_id, lid))

        if args.dry:
            print("**** Dry run, not saving message to database *****")
            return lid, ojson["mid"]

        if self.dump_dir:
            try:
                self.elastic = plugins.elastic.Elastic()
            except elasticsearch.exceptions.ElasticsearchException as e:
                print(e)
                print(
                    "ES connection failed, but dumponfail specified, dumping to %s"
                    % self.dump_dir
                )
        else:
            self.elastic = plugins.elastic.Elastic()

        # Always allow this to be set; will be replaced as necessary by wait_for_active_shards
        self.consistency = config["elasticsearch"].get("write", "quorum")
        es_engine_major = self.elastic.engineMajor()
        if es_engine_major == 2:
            pass
        elif es_engine_major in [5, 6, 7]:
            self.wait_for_active_shards = config["elasticsearch"].get("wait", 1)
        else:
            raise Exception("Unexpected elasticsearch version ", es_engine_major)

        try:
            if contents:
                for key in contents:
                    self.index(
                        index=self.elastic.db_attachment,
                        id=key,
                        body={"source": contents[key]},
                    )

            self.index(
                index=self.elastic.db_mbox,
                id=ojson["mid"],
                consistency=self.consistency,
                body=ojson,
            )

            self.index(
                index=self.elastic.db_source,
                id=sha3,
                consistency=self.consistency,
                body={
                    "message-id": msg_metadata["message-id"],
                    "permalink": ojson["mid"],
                    "source": self.mbox_source(raw_message),
                },
            )
        # If we have a dump dir and ES failed, push to dump dir instead as a JSON object
        # We'll leave it to another process to pick up the slack.
        except Exception as err:
            print(err)
            if args.dump:
                print(
                    "Pushing to ES failed, but dumponfail specified, dumping JSON docs"
                )
                uid = uuid.uuid4()
                mbox_path = os.path.join(args.dump, "%s.json" % uid)
                with open(mbox_path, "w") as f:
                    json.dump(
                        {
                            "id": ojson["mid"],
                            "mbox": ojson,
                            "mbox_source": {
                                "id": sha3,
                                "permalink": ojson["mid"],
                                "message-id": msg_metadata["message-id"],
                                "source": self.mbox_source(raw_message),
                            },
                            "attachments": contents,
                        },
                        f,
                        indent=2,
                    )
                    f.close()
                sys.exit(0)  # We're exiting here, the rest can't be done without ES
            # otherwise fail as before
            raise err

        # If MailMan and list info is present, save/update it in ES:
        if (
            hasattr(mlist, "description")
            and hasattr(mlist, "list_name")
            and mlist.description
            and mlist.list_name
        ):
            self.elastic.index(
                index=self.elastic.db_mailinglist,
                id=lid,
                consistency=self.elastic.consistency,
                body={
                    "list": lid,
                    "name": mlist.list_name,
                    "description": mlist.description,
                    "private": private,
                },
            )

        if logger:
            logger.info("Pony Mail archived message %s successfully", ojson["mid"])
        oldrefs = []

        # Is this a direct reply to a pony mail email?
        if irt != "":
            dm = re.search(r"pony-([a-f0-9]+)-([a-f0-9]+)@", irt)
            if dm:
                cid = dm.group(1)
                mid = dm.group(2)
                if self.elastic.exists(index=self.elastic.db_account, id=cid):
                    doc = self.elastic.get(index=self.elastic.db_account, id=cid)
                    if doc:
                        oldrefs.append(cid)
                        # N.B. no index is supplied, so ES will generate one
                        self.index(
                            index=self.elastic.db_notification,
                            consistency=self.elastic.consistency,
                            body={
                                "type": "direct",
                                "recipient": cid,
                                "list": lid,
                                "private": private,
                                "date": ojson["date"],
                                "from": msg_metadata["from"],
                                "to": msg_metadata["to"],
                                "subject": msg_metadata["subject"],
                                "message-id": msg_metadata["message-id"],
                                "in-reply-to": irt,
                                "epoch": ojson["epoch"],
                                "mid": mid,
                                "seen": 0,
                            },
                        )
                        if logger:
                            logger.info("Notification sent to %s for %s", cid, mid)

        # Are there indirect replies to pony emails?
        if msg_metadata.get("references"):
            for im in re.finditer(
                r"pony-([a-f0-9]+)-([a-f0-9]+)@", msg_metadata.get("references")
            ):
                cid = im.group(1)
                mid = im.group(2)
                # TODO: Fix this to work with pibbles
                if self.elastic.exists(index=self.elastic.db_mbox, id=cid):
                    doc = self.elastic.get(index=self.elastic.db_mbox, id=cid)

                    # does the user want to be notified of indirect replies?
                    if (
                        doc
                        and "preferences" in doc["_source"]
                        and doc["_source"]["preferences"].get("notifications")
                        == "indirect"
                        and cid not in oldrefs
                    ):
                        oldrefs.append(cid)
                        # N.B. no index mapping is supplied, so ES will generate one
                        self.elastic.index(
                            index=self.elastic.db_notification,
                            body={
                                "type": "indirect",
                                "recipient": cid,
                                "list": lid,
                                "private": private,
                                "date": ojson["date"],
                                "from": msg_metadata["from"],
                                "to": msg_metadata["to"],
                                "subject": msg_metadata["subject"],
                                "message-id": msg_metadata["message-id"],
                                "in-reply-to": irt,
                                "epoch": ojson["epoch"],
                                "mid": mid,
                                "seen": 0,
                            },
                        )
                        if logger:
                            logger.info("Notification sent to %s for %s", cid, mid)
        return lid, ojson["mid"]

    def mbox_source(self, b: bytes) -> str:
        # Common method shared with import-mbox
        try:
            # Can we store as ASCII?
            return b.decode("ascii", errors="strict")
        except UnicodeError:
            # No, so must use base64 to avoid corruption on re-encoding
            return encode_base64(b)

    def list_url(self, _mlist):
        """ Required by MM3 plugin API
        """
        return None

    def permalink(self, _mlist, _msg):
        """ Required by MM3 plugin API
        """
        return None


def main():
    parser = argparse.ArgumentParser(description="Command line options.")
    parser.add_argument(
        "--lid", dest="lid", type=str, nargs=1, help="Alternate specific list ID"
    )
    parser.add_argument(
        "--altheader",
        dest="altheader",
        type=str,
        nargs=1,
        help="Alternate header for list ID",
    )
    parser.add_argument(
        "--allowfrom",
        dest="allowfrom",
        type=str,
        nargs=1,
        help="(optional) source IP (mail server) to allow posts from, ignore if no match",
    )
    parser.add_argument(
        "--ignore",
        dest="ignorefrom",
        type=str,
        nargs=1,
        help="Sender/list to ignore input from (owner etc)",
    )
    parser.add_argument(
        "--private",
        dest="private",
        action="store_true",
        help="This is a private archive",
    )
    parser.add_argument(
        "--makedate",
        dest="makedate",
        action="store_true",
        help="Use the archive timestamp as the email date instead of the Date header",
    )
    parser.add_argument(
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Do not exit -1 if the email could not be parsed",
    )
    parser.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        help="Output additional log messages",
    )
    parser.add_argument(
        "--html2text",
        dest="html2text",
        action="store_true",
        help="Try to convert HTML to text if no text/plain message is found",
    )
    parser.add_argument(
        "--dry",
        dest="dry",
        action="store_true",
        help="Do not save emails to elasticsearch, only test parsing",
    )
    parser.add_argument(
        "--ignorebody",
        dest="ibody",
        type=str,
        nargs=1,
        help="Optional email bodies to treat as empty (in conjunction with --html2text)",
    )
    parser.add_argument(
        "--dumponfail",
        dest="dump",
        help="If pushing to ElasticSearch fails, dump documents in JSON format to this directory and "
        "fail silently.",
    )
    parser.add_argument("--generator", dest="generator", help="Override the generator.")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    else:
        # elasticsearch logs lots of warnings on retries/connection failure
        # Also eliminates: 'Undecodable raw error response from server:' warning message
        logging.getLogger("elasticsearch").setLevel(logging.ERROR)

    archie = Archiver(
        generator=args.generator or archiver_generator, parse_html=args.html2text
    )
    # use binary input so parser can use appropriate charset
    input_stream = sys.stdin.buffer

    try:
        raw_message = input_stream.read()
        try:
            msg = email.message_from_bytes(raw_message)
        except Exception as err:
            print("STDIN parser exception: %s" % err)
            sys.exit(-1)

        if args.altheader:
            alt_header = args.altheader[0]
            if alt_header in msg:
                try:
                    msg.replace_header("List-ID", msg.get(alt_header))
                except KeyError:
                    msg.add_header("list-id", msg.get(alt_header))
        elif "altheader" in sys.argv:
            alt_header = sys.argv[len(sys.argv) - 1]
            if alt_header in msg:
                try:
                    msg.replace_header("List-ID", msg.get(alt_header))
                except KeyError:
                    msg.add_header("list-id", msg.get(alt_header))

        # Set specific LID?
        if args.lid and len(args.lid[0]) > 3:
            try:
                msg.replace_header("List-ID", args.lid[0])
            except KeyError:
                msg.add_header("list-id", args.lid[0])

        # Ignore based on --ignore flag?
        if args.ignorefrom:
            ignore_from = args.ignorefrom[0]
            if fnmatch.fnmatch(msg.get("from"), ignore_from) or (
                msg.get("list-id") and fnmatch.fnmatch(msg.get("list-id"), ignore_from)
            ):
                print("Ignoring message as instructed by --ignore flag")
                sys.exit(0)

        # Check CIDR if need be
        if args.allowfrom:

            c = netaddr.IPNetwork(args.allowfrom[0])
            good = False
            for line in msg.get_all("received") or []:
                m = re.search(r"from .+\[(.+)]", line)
                if m:
                    try:
                        ip = netaddr.IPAddress(m.group(1))
                        if ip in c:
                            good = True
                            msg.add_header("ip-whitelisted", "yes")
                            break
                    except ValueError:
                        pass
                    except netaddr.AddrFormatError:
                        pass
            if not good:
                print("No whitelisted IP found in message, aborting")
                sys.exit(-1)
        # Replace date header with $now?
        if args.makedate:
            msg.replace_header("date", email.utils.formatdate())
        is_public = True
        if args.private:
            is_public = False
        if "list-id" in msg:
            if not msg.get("archived-at"):
                msg.add_header("archived-at", email.utils.formatdate())
            list_data = collections.namedtuple(
                "importmsg",
                [
                    "list_id",
                    "archive_public",
                    "archive_policy",
                    "list_name",
                    "description",
                ],
            )(
                list_id=msg.get("list-id"),
                archive_public=is_public,
                archive_policy=None,
                list_name=msg.get("list-id"),
                description=msg.get("list-id"),
            )

            try:
                lid, mid = archie.archive_message(args, list_data, msg, raw_message)
                print(
                    "%s: Done archiving to %s as %s!"
                    % (email.utils.formatdate(), lid, mid)
                )
            except Exception as err:
                if args.verbose:
                    traceback.print_exc()
                print("Archiving failed!: %s" % err)
                raise Exception("Archiving to ES failed")
        else:
            print("Nothing to import (no list-id found!)")
    except Exception as err:
        # extract the len number without using variables (which may cause issues?)
        #                           last traceback    1st entry, 2nd field
        line = traceback.extract_tb(sys.exc_info()[2])[0][1]
        if args.quiet:
            print(
                "Could not parse email, but exiting quietly as --quiet is on: %s (@ %s)"
                % (err, line)
            )
        else:
            print("Could not parse email: %s (@ %s)" % (err, line))
            sys.exit(-1)


if __name__ == "__main__":
    main()
