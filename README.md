# Pulpito Branch Board

This is a small standalone web app that:

- reads branch names from a file whose path is provided by an environment variable
- builds a URL for each branch from a template
- shows one proxied result row per branch on a single page

## Files

- `app.py`: HTTP server and proxy
- `.env.example`: sample environment variables

## Environment variables

- `PULP_BRANCH_FILE`: required; absolute path to the file containing branch names, one per line
- `PULP_URL_TEMPLATE`: optional; URL template containing `{branch}`
- `PULP_HOST`: optional; default `127.0.0.1`
- `PULP_PORT`: optional; default `8000`
- `PULP_ROW_HEIGHT`: optional; iframe height in pixels, default `720`
- `PULP_REFRESH_SECONDS`: optional; page refresh interval, default `0`
- `PULP_REQUEST_TIMEOUT`: optional; remote fetch timeout in seconds, default `20`

Blank lines and lines starting with `#` are ignored in the branch file.

## Example branch file

```text
wip-rf-asokassert-crimson
main
reef
```

## Run

```bash
cd /home/rfriedma/ntry/pulp
export PULP_BRANCH_FILE=/absolute/path/to/branches.txt
export PULP_URL_TEMPLATE='https://pulpito-ng.ceph.com/runs?branch={branch}'
python3 app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Notes

- The page fetches the remote content through the local server to avoid frame restrictions from the target site.
- Relative assets in the fetched page are handled by injecting a `<base>` tag.
