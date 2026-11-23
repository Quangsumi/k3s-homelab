#!/bin/sh
set -eu

mkdir -p "$REPO_ROOT"
# URLs arrive as environment data, never as executable shell text.
printf '%s\n' "$REPO_URLS" | while IFS= read -r repo_url; do
  [ -n "$repo_url" ] || continue
  repo_name=${repo_url##*/}
  repo_name=${repo_name%.git}
  target="$REPO_ROOT/$repo_name"

  # Preserve every existing path, including manual clones, worktrees and symlinks.
  if [ -e "$target" ] || [ -L "$target" ]; then
    printf 'Keeping existing path: %s (no pull, reset or overwrite)\n' "$target"
    continue
  fi

  # Publish a clone only after success. Failed authentication does not block the IDE.
  clone_dir=$(mktemp -d "$REPO_ROOT/.clone-XXXXXX")
  if GIT_TERMINAL_PROMPT=0 git clone -- "$repo_url" "$clone_dir" </dev/null; then
    mv "$clone_dir" "$target"
  else
    rm -rf -- "$clone_dir"
    printf 'Clone failed for %s. Fix Git access in the terminal, then restart to retry.\n' "$repo_url" >&2
  fi
done

# Only Coder can reach this listener; Coder supplies authentication.
code-server --auth none --bind-addr 127.0.0.1:13337 --disable-telemetry \
  "$REPO_ROOT" >/tmp/code-server.log 2>&1 &
