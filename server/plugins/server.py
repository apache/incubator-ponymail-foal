import asyncio
import typing

import aiohttp
from elasticsearch import AsyncElasticsearch

import plugins.configuration
import plugins.offloader


class Endpoint:
    exec: typing.Callable

    def __init__(self, executor):
        self.exec = executor


class BaseServer:
    """Main server class, base def"""

    config: plugins.configuration.Configuration
    server: typing.Optional[aiohttp.web.Server]
    data: plugins.configuration.InterData
    handlers: typing.Dict[str, Endpoint]
    database: AsyncElasticsearch
    dbpool: asyncio.Queue
    runners: plugins.offloader.ExecutorPool
