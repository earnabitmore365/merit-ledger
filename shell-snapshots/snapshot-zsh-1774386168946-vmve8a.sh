# Snapshot file
# Unset all aliases to avoid conflicts with functions
unalias -a 2>/dev/null || true
# Functions
# Shell Options
setopt nohashdirs
setopt login
# Aliases
alias -- abby-time='python3 ~/.openclaw/workspace/skills/abby-watch/scripts/time_cli.py'
alias -- run-help=man
alias -- which-command=whence
# Check for rg availability
if ! (unalias rg 2>/dev/null; command -v rg) >/dev/null 2>&1; then
  function rg {
  if [[ -n $ZSH_VERSION ]]; then
    ARGV0=rg /Users/allenbot/.local/share/claude/versions/2.1.81 "$@"
  elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    ARGV0=rg /Users/allenbot/.local/share/claude/versions/2.1.81 "$@"
  elif [[ $BASHPID != $$ ]]; then
    exec -a rg /Users/allenbot/.local/share/claude/versions/2.1.81 "$@"
  else
    (exec -a rg /Users/allenbot/.local/share/claude/versions/2.1.81 "$@")
  fi
}
fi
export PATH=/Users/allenbot/.local/bin\:/opt/homebrew/bin\:/usr/local/bin\:/System/Cryptexes/App/usr/bin\:/usr/bin\:/bin\:/usr/sbin\:/sbin\:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin\:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin\:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin\:/opt/pmk/env/global/bin\:/opt/homebrew/bin
