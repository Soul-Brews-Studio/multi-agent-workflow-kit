# shellcheck shell=bash

# Auto-detect repo root from this file's location (works from any worktree)
# Supports both bash (BASH_SOURCE) and zsh (%x)
if [[ -n "$MAW_REPO_ROOT" ]]; then
  repo_root="$MAW_REPO_ROOT"
else
  # Get this script's path - works in both bash and zsh
  __maw_self="${BASH_SOURCE[0]:-${(%):-%x}}"
  if [[ -n "$__maw_self" && -f "$__maw_self" ]]; then
    # This file is at .agents/maw.env.sh, so parent of parent = repo root
    repo_root="$(cd "$(dirname "$__maw_self")/.." && pwd)"
  else
    repo_root="$PWD"
  fi
  unset __maw_self
fi
toolkit_dir="$repo_root/.agents"
legacy_scripts_dir="$toolkit_dir/scripts"

declare -a maw_script_dirs=()

if [[ -d "$legacy_scripts_dir" ]]; then
  maw_script_dirs+=("$legacy_scripts_dir")
fi

if [[ -d "$toolkit_dir" ]]; then
  maw_script_dirs+=("$toolkit_dir")
fi

maw_script_dirs+=("$repo_root")

if [[ ${#maw_script_dirs[@]} -gt 0 ]]; then
  maw_path_dir=""
  for candidate_dir in "${maw_script_dirs[@]}"; do
    if [[ "$candidate_dir" != "$repo_root" ]]; then
      maw_path_dir="$candidate_dir"
      break
    fi
  done

  if [[ -n "$maw_path_dir" ]]; then
    if command -v PATH_add >/dev/null 2>&1; then
      PATH_add "$maw_path_dir"
    elif [[ :$PATH: != *":$maw_path_dir:"* ]]; then
      export PATH="$maw_path_dir:$PATH"
    fi
  fi
fi

__maw_usage() {
  cat <<'USAGE'
Usage: maw <command> [args]

Commands:
  install | setup    Run setup.sh to provision or refresh agent worktrees
  start              Run start-agents.sh to launch the tmux session
  attach             Run attach.sh to connect to an active tmux session
  agents             Run agents.sh to manage worktrees manually
  kill               Run kill-all.sh to terminate tmux sessions by prefix
  send               Run send-commands.sh to broadcast commands to panes
  remove             Run remove.sh to delete agent worktrees
  issue              Run issue.sh to open a GitHub issue via gh CLI
  uninstall          Run uninstall.sh to remove toolkit assets
  warp <target>      Navigate to agent worktree or root (e.g., warp 1, warp root)
  hey <agent> <msg>  Send a message to a specific agent (e.g., hey 1 analyse repo)
  zoom <agent>       Toggle zoom (maximize/restore) for a specific agent pane
  sync               Smart sync all agent worktrees from main (respects boundaries)
  merge <N|all>      Safely merge agent commits INTO main (fetch origin first)
  log <type> <msg>   Write to per-agent log (types: activity, debug, completions, errors)
  peek [agent]       Check what agents are doing (read-only status + focus)
  wait [agents...]   Wait for agents to commit (1s polling, not 30s)
  checkpoint         Save starting points before dispatch (for review gate)
  review             Show diffs since checkpoint, approve/reject changes
  watch [interval]   Poll agents until all done (default: 2s)
  reset <N>          Reject agent N work → reset to checkpoint
  direnv             Run 'direnv allow' in repo root and all agent worktrees
  catlab             Download CLAUDE.md guidelines from catlab gist
  version            Show toolkit version information
USAGE
}

__maw_find_script() {
  local target=$1
  shift || true

  local -a names=("$target")
  if [[ $target != *.sh ]]; then
    names+=("$target.sh")
  fi

  local name dir
  for name in "${names[@]}"; do
    for dir in "${maw_script_dirs[@]}"; do
      [[ -d "$dir" ]] || continue
      if [[ -f "$dir/$name" ]]; then
        printf '%s\n' "$dir/$name"
        return 0
      fi
    done
  done

  return 1
}

__maw_exec() {
  local script_name=$1
  shift || true

  local resolved
  if ! resolved=$(__maw_find_script "$script_name"); then
    echo "Unknown maw command target: $script_name" >&2
    __maw_usage >&2
    return 1
  fi

  command "$resolved" "$@"
}

__maw_warp() {
  local print_mode=0
  local target=""

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --print)
        print_mode=1
        shift
        ;;
      *)
        target="$1"
        shift
        ;;
    esac
  done

  if [[ -z "$target" ]]; then
    echo "Usage: maw warp <target>" >&2
    echo "  target: agent name (e.g., 1-agent, 2-agent) or 'root'" >&2
    return 1
  fi

  local agents_dir="$repo_root/agents"
  local destination=""

  if [[ "$target" == "root" ]]; then
    destination="$repo_root"
  else
    local target_dir="$agents_dir/$target"
    if [[ -d "$target_dir" ]]; then
      destination="$target_dir"
    else
      echo "Error: Agent worktree not found: $target_dir" >&2
      echo "Available agents:" >&2
      if [[ -d "$agents_dir" ]]; then
        ls -1 "$agents_dir" 2>/dev/null | grep -v '^\.' | sed 's/^/  /' >&2
      fi
      return 1
    fi
  fi

  # Either print the path or cd to it
  if [[ $print_mode -eq 1 ]]; then
    echo "$destination"
  else
    cd "$destination" || return 1
    echo "📍 Warped to: $destination" >&2
  fi
}

maw() {
  if [[ $# -eq 0 ]]; then
    __maw_usage
    return 1
  fi

  local subcommand=$1
  shift || true

  case "$subcommand" in
    install|setup)
      __maw_exec setup.sh "$@"
      ;;
    start)
      __maw_exec start-agents.sh "$@"
      ;;
    attach)
      __maw_exec attach.sh "$@"
      ;;
    agents)
      __maw_exec agents.sh "$@"
      ;;
    kill)
      __maw_exec kill-all.sh "$@"
      ;;
    send)
      __maw_exec send-commands.sh "$@"
      ;;
    remove)
      __maw_exec remove.sh "$@"
      ;;
    issue)
      __maw_exec issue.sh "$@"
      ;;
    uninstall)
      __maw_exec uninstall.sh "$@"
      ;;
    warp)
      __maw_warp "$@"
      ;;
    hey)
      __maw_exec hey.sh "$@"
      ;;
    zoom)
      __maw_exec zoom.sh "$@"
      ;;
    sync)
      __maw_exec smart-sync.sh "$@"
      ;;
    merge)
      __maw_exec merge.sh "$@"
      ;;
    log)
      __maw_exec agent-log.sh "$@"
      ;;
    peek)
      __maw_exec peek.sh "$@"
      ;;
    wait)
      __maw_exec wait.sh "$@"
      ;;
    checkpoint)
      __maw_exec checkpoint.sh "$@"
      ;;
    review)
      __maw_exec review.sh "$@"
      ;;
    watch)
      __maw_exec watch.sh "$@"
      ;;
    reset)
      __maw_exec reset.sh "$@"
      ;;
    direnv)
      __maw_exec direnv-allow.sh "$@"
      ;;
    catlab)
      __maw_exec catlab.sh "$@"
      ;;
    version)
      __maw_exec version.sh "$@"
      ;;
    help|-h|--help)
      __maw_usage
      ;;
    *)
      echo "Unknown maw command: $subcommand" >&2
      __maw_usage >&2
      return 1
      ;;
  esac
}

alias maw-start='maw start'
alias maw-attach='maw attach'
alias maw-setup='maw install'
alias maw-agents='maw agents'
alias maw-kill='maw kill'
alias maw-send='maw send'
alias maw-remove='maw remove'
alias maw-uninstall='maw uninstall'
alias maw-hey='maw hey'
alias maw-issue='maw issue'
alias maw-zoom='maw zoom'

# Load shell completion if available
if [[ -n "${ZSH_VERSION:-}" ]]; then
  # Zsh completion - add to fpath and load completion
  if [[ -d "$toolkit_dir" ]] && [[ -f "$toolkit_dir/maw.completion.zsh" ]]; then
    fpath=("$toolkit_dir" $fpath)
    autoload -Uz compinit
    compinit -C
    # Source the completion file directly to register _maw function
    source "$toolkit_dir/maw.completion.zsh"
    compdef _maw maw
  fi
elif [[ -n "${BASH_VERSION:-}" ]]; then
  # Bash completion
  completion_file="$toolkit_dir/maw.completion.bash"
  if [[ -f "$completion_file" ]]; then
    # shellcheck disable=SC1090
    source "$completion_file"
  fi
fi
