# caddyless

An alternative to [vercel-labs/portless](https://port1355.dev/) based on [Caddy](https://caddyserver.com/).
Replace port numbers with stable, named .localhost URLs.

```diff
- "dev": "nuxt dev"                  # http://localhost:3000
+ "dev": "caddyless myapp nuxt dev"  # https://myapp.localhost
```

```diff
[tool.pdm.scripts]
- start = "flask run -p 54321"                    # http://localhost:54321
+ start = "caddyless myapp flask run -p '$PORT'"  # https://myapp.localhost
```

## Install

- [Install Caddy](https://caddyserver.com/docs/install) and trust Caddy internal CA:

```sh
# Maybe requires sudo
caddy trust
```

- [Keep Caddy running](https://caddyserver.com/docs/running) (optional)
- Install caddyless:

```sh
curl https://raw.githubusercontent.com/ProgramRipper/caddyless/refs/heads/master/caddyless/__main__.py -o ~/.local/bin/caddyless
chmod +x ~/.local/bin/caddyless

# Or with uv
uv tool install git+https://github.com/ProgramRipper/caddyless.git
```

## Usage

For app that respects `$PORT` environment variable, just run:

```sh
# Explicit name
caddyless myapp nuxt dev
# -> https://myapp.localhost

# Subdomains
caddyless api.myapp nuxt dev
# -> https://api.myapp.localhost

# Any other domains (requires hosts configuration)
caddyless example.com nuxt dev
# -> https://example.com
```

For app thats specify port by argument or flag, use placeholder `'$PORT'` (single quotes are required to prevent shell expansion):

```sh
caddyless myapp python -m http.server '$PORT'

caddyless myapp uvicorn main:app --port '$PORT'
```

For app that doesn't support custom port, set `$PORT` environment variable:

```sh
PORT=8000 caddyless myapp python -m http.server
```
