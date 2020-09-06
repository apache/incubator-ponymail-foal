import asyncio
import typing

import aiohttp
from elasticsearch import AsyncElasticsearch

import plugins.configuration


class Endpoint:
    exec: typing.Callable

    def __init__(self, executor):
        self.exec = executor


class BaseServer:
    """Main server class, base def"""

    config: plugins.configuration.Configuration
    server: aiohttp.web.Server
    data: plugins.configuration.InterData
    handlers: typing.Dict[str, Endpoint]
    database: AsyncElasticsearch
    dbpool: asyncio.Queue
