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


class OAuthConfig:
    authoritative_domains: list
    google_client_id: str
    github_client_id: str
    github_client_secret: str

    def __init__(self, subyaml: dict):
        self.authoritative_domains = subyaml.get('authoritative_domains', [])
        self.google_client_id = subyaml.get('google_client_id', '')
        self.github_client_id = subyaml.get('github_client_id', '')
        self.github_client_secret = subyaml.get('github_client_secret', '')


class DBConfig:
    hostname: str
    port: int
    secure: bool
    url_prefix: str
    db_prefix: str
    max_hits: int

    def __init__(self, subyaml: dict):
        self.hostname = str(subyaml.get("server", "localhost"))
        self.port = int(subyaml.get("port", 9200))
        self.secure = bool(subyaml.get("secure", False))
        self.url_prefix = subyaml.get("url_prefix", "")
        self.db_prefix = str(subyaml.get("db_prefix", "ponymail"))
        self.max_hits = int(subyaml.get("max_hits", 5000))


class Configuration:
    server: ServerConfig
    database: DBConfig
    tasks: TaskConfig
    oauth: OAuthConfig

    def __init__(self, yml: dict):
        self.server = ServerConfig(yml.get("server", {}))
        self.database = DBConfig(yml.get("database", {}))
        self.tasks = TaskConfig(yml.get("tasks", {}))
        self.oauth = OAuthConfig(yml.get("oauth", {}))


class InterData:
    """
        A mix of various global variables used throughout processes
    """

    lists: dict
    sessions: dict
    activity: dict

    def __init__(self):
        self.lists = {}
        self.sessions = {}
        self.activity = {}
