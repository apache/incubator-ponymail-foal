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


class OAuthConfig:
    authoritative_domains: list
    admins: list
    google_client_id: str
    github_client_id: str
    github_client_secret: str

    def __init__(self, subyaml: dict):
        self.authoritative_domains = subyaml.get("authoritative_domains", [])
        self.admins = subyaml.get("admins", [])
        self.google_client_id = subyaml.get("google_client_id", "")
        self.github_client_id = subyaml.get("github_client_id", "")
        self.github_client_secret = subyaml.get("github_client_secret", "")


class DBConfig:
    dburl: str
    hostname: str
    port: int
    secure: bool
    url_prefix: str
    db_prefix: str
    max_hits: int

    def __init__(self, subyaml: dict):
        self.dburl = str(subyaml.get("dburl", ""))
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
    ui: UIConfig

    def __init__(self, yml: dict):
        self.server = ServerConfig(yml.get("server", {}))
        self.database = DBConfig(yml.get("database", {}))
        self.tasks = TaskConfig(yml.get("tasks", {}))
        self.oauth = OAuthConfig(yml.get("oauth", {}))
        self.ui = UIConfig(yml.get("ui", {}))


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
