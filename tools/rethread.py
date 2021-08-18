#!/usr/bin/env python3

from elasticsearch.helpers import scan

import archiver
from plugins.elastic import Elastic


def first_pass(elastic: Elastic) -> None:
    hits = scan(
        client=elastic.es,
        index=elastic.db_mbox,
        # Thanks to elasticsearch_dsl.Q
        # (~Q(...)) | (~Q(...))
        query={
            "query": {
                "bool": {
                    "should": [
                        {
                            "bool": {
                                "must_not": [{"exists": {"field": "forum"}}]
                            }
                        },
                        {
                            "bool": {
                                "must_not": [{"exists": {"field": "size"}}]
                            }
                        },
                    ]
                }
            }
        },
    )
    for hit in hits:
        pid = hit["_id"]
        ojson = hit["_source"]
        ojson["forum"] = ojson.get("list", "").strip("<>").replace(".", "@", 1)
        source = elastic.es.get(
            elastic.db_source, ojson["dbid"], _source="source"
        )["_source"]["source"]
        ojson["size"] = len(source)
        elastic.index(index=elastic.db_mbox, id=pid, body=ojson)


def second_pass(elastic: Elastic) -> None:
    hits = scan(
        client=elastic.es,
        index=elastic.db_mbox,
        query={"sort": {"epoch": "asc"}},
    )
    for hit in hits:
        pid = hit["_id"]
        ojson = hit["_source"]
        parent_info = archiver.get_parent_info(elastic, ojson)
        ojson["top"] = parent_info is None
        ojson["previous"] = ""
        ojson["thread"] = pid if (parent_info is None) else ""
        elastic.index(index=elastic.db_mbox, id=pid, body=ojson)


def third_pass(elastic: Elastic) -> None:
    hits = scan(client=elastic.es, index=elastic.db_mbox, query={})
    for hit in hits:
        pid = hit["_id"]
        ojson = hit["_source"]
        if ojson["thread"] != "":
            continue
        if ojson["top"] is True:
            ojson["previous"] = archiver.get_previous_mid(elastic, ojson)
            ojson["thread"] = pid
            elastic.index(index=elastic.db_mbox, id=pid, body=ojson)
        else:
            tree = []
            while ojson["thread"] == "":
                tree.append(ojson)
                ojson_parent = archiver.get_parent_info(elastic, ojson)
                if ojson_parent is None:
                    ojson["previous"] = None
                    print("Error:", ojson["mid"], "has no parent")
                    break
                ojson["previous"] = ojson_parent["mid"]
                ojson = ojson_parent
            for info in tree:
                info["thread"] = ojson["thread"]
                elastic.index(index=elastic.db_mbox, id=info["mid"], body=info)


def main() -> None:
    elastic: Elastic = Elastic()
    first_pass(elastic)
    second_pass(elastic)
    third_pass(elastic)


if __name__ == "__main__":
    main()
