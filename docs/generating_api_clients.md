<!---
 Licensed to the Apache Software Foundation (ASF) under one or more
 contributor license agreements.  See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 The ASF licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License.  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
-->

# Generating API Client Libraries

**You do not have to hand-write a client for the Foal API.** The server ships a
machine-readable [OpenAPI 3.0](https://spec.openapis.org/oas/v3.0.0) description
of its endpoints at [`server/openapi.yaml`](../server/openapi.yaml), and a wide
range of off-the-shelf generators turn that single file into a ready-to-use,
typed client library in almost any language.

## Why generate instead of replicate

Several tools benefit from long-term API tokens and from talking to the API in
general — the [Pony Mail MCP](https://github.com/apache/comdev/tree/main/mcp/ponymail-mcp),
internal scripts, dashboards, bots, and so on. Re-implementing the request
plumbing, auth handling, and response types by hand in each of them multiplies
the maintenance burden: a bug fixed in one copy has to be chased down in all the
others.

The OpenAPI spec avoids that. It is the **single shared contract**: the server
maintains it alongside the code, and every consumer *derives* its client from
it rather than duplicating it. When an endpoint changes, you regenerate — you do
not hand-patch N separate clients. The shared, maintained artifact is the spec,
not copy-pasted client code.

> The spec is the source of truth. If you find the spec is missing an endpoint
> or a field you need, fix `server/openapi.yaml` (and regenerate) rather than
> working around it in a client — that keeps the benefit for every other
> consumer.

## Prerequisites

- The spec file: [`server/openapi.yaml`](../server/openapi.yaml). You can point a
  generator at a local checkout, or at a copy hosted by your instance.
- A generator. The two most common:
  - **[OpenAPI Generator](https://openapi-generator.tech/)** — the most widely
    used, ~50 target languages/frameworks. Examples below use this.
  - **[swagger-codegen](https://github.com/swagger-api/swagger-codegen)** — the
    older sibling; comparable usage.

Install OpenAPI Generator whichever way suits you:

```bash
# Homebrew (macOS)
brew install openapi-generator

# npm (cross-platform)
npm install -g @openapitools/openapi-generator-cli

# Or with no install at all, via the official Docker image (used below)
docker pull openapitools/openapi-generator-cli
```

It is worth validating the spec first — this also confirms your toolchain works:

```bash
openapi-generator validate -i server/openapi.yaml
```

## Authentication in generated clients

The spec declares two security schemes, so generated clients expose both:

| Scheme | How the client sends it | Use |
|--------|-------------------------|-----|
| `bearerAuth` | `Authorization: Bearer <token>` | **Long-term API tokens** (`pmt_…`) — recommended for scripts/automation |
| `cookieAuth` | `Cookie: ponymail=<session>` | Interactive browser sessions |

For programmatic use you almost always want `bearerAuth`. Create a token from
the web UI (user menu → **API Tokens**) or via
[`token.json`](API.md#tokenjson), then hand the `pmt_…` secret to the generated
client as shown per language below. (Token *management* — create/list/revoke —
is deliberately cookie-only and cannot be driven with a bearer token; see
[API.md](API.md#tokenjson).)

## Examples

Each example generates a client into `./out` from a local checkout. Swap the
Docker invocation for a direct `openapi-generator-cli` call if you installed it
natively (the arguments are identical); with Docker, mount the working directory
so the tool can read the spec and write the output:

```bash
DOCKER="docker run --rm -v ${PWD}:/local -w /local openapitools/openapi-generator-cli"
```

### Python

```bash
$DOCKER generate \
  -i server/openapi.yaml \
  -g python \
  -o out/python-client \
  --additional-properties=packageName=ponymail_client
```

```python
import ponymail_client
from ponymail_client.rest import ApiException

config = ponymail_client.Configuration(
    host="https://lists.apache.org/api",
    access_token="pmt_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",  # bearerAuth
)

with ponymail_client.ApiClient(config) as client:
    api = ponymail_client.DefaultApi(client)
    try:
        result = api.api_stats_json_post(...)  # method names follow the spec's operationIds
        print(result)
    except ApiException as e:
        print("API error:", e)
```

### TypeScript / JavaScript

```bash
$DOCKER generate \
  -i server/openapi.yaml \
  -g typescript-fetch \
  -o out/ts-client
```

```ts
import { Configuration, DefaultApi } from "./out/ts-client";

const api = new DefaultApi(
  new Configuration({
    basePath: "https://lists.apache.org/api",
    accessToken: "pmt_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX", // bearerAuth
  }),
);

const stats = await api.apiStatsJsonPost({ /* … */ });
console.log(stats);
```

### Go

```bash
$DOCKER generate \
  -i server/openapi.yaml \
  -g go \
  -o out/go-client \
  --additional-properties=packageName=ponymail
```

```go
ctx := context.WithValue(context.Background(), ponymail.ContextAccessToken,
    "pmt_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX") // bearerAuth

cfg := ponymail.NewConfiguration()
cfg.Servers = ponymail.ServerConfigurations{{URL: "https://lists.apache.org/api"}}
client := ponymail.NewAPIClient(cfg)

stats, _, err := client.DefaultApi.ApiStatsJsonPost(ctx).Execute()
```

### Java

```bash
$DOCKER generate \
  -i server/openapi.yaml \
  -g java \
  -o out/java-client \
  --additional-properties=library=native,invokerPackage=org.apache.ponymail.client
```

```java
ApiClient client = Configuration.getDefaultApiClient();
client.setBasePath("https://lists.apache.org/api");
client.setBearerToken("pmt_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"); // bearerAuth

DefaultApi api = new DefaultApi(client);
```

Other targets (`csharp`, `rust`, `php`, `ruby`, `kotlin`, …) work the same way:
change `-g` and the auth-configuration idiom is analogous.

## Keeping generated code healthy

- **Treat generated clients as build artifacts.** Prefer regenerating them in
  CI from a pinned spec version over committing large generated trees — the same
  reasoning the server uses for its own built files. If you do commit a client,
  commit the generator command/version next to it so it is reproducible.
- **Pin the generator version** (e.g. a specific `openapi-generator-cli` image
  tag) so output is stable across machines and over time.
- **Regenerate when the spec changes.** Watch `server/openapi.yaml`; a diff
  there is your signal to regenerate and re-test the client.
- **Coverage caveats.** The spec covers the JSON API endpoints documented in
  [API.md](API.md). A few operations — notably the admin `mgmt.json` actions —
  are intentionally not in the spec; call those directly if you need them.
  Public read endpoints require no credentials, so a generated client can be
  used anonymously for public lists and only needs a token for private lists or
  writes.

## Related

- [API.md](API.md) — Full endpoint reference, authentication, and scopes
- [API Client Guide](api_client_guide.md) — Hand-rolled `curl`/HTTP examples
- [`server/openapi.yaml`](../server/openapi.yaml) — The spec these clients are generated from
- [OpenAPI Generator documentation](https://openapi-generator.tech/docs/generators/) — Full list of target languages and options
