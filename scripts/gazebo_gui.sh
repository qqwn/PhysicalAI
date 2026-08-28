#!/usr/bin/env bash

set -euo pipefail

CONTAINER_NAME="${ROS2_CONTAINER:-ros2-jazzy}"
VNC_PORT="${GAZEBO_VNC_PORT:-5901}"
VNC_PASSWORD="${GAZEBO_VNC_PASSWORD:-ros2gui}"
DISPLAY_NUMBER="${GAZEBO_DISPLAY_NUMBER:-99}"
SCREEN_GEOMETRY="${GAZEBO_GUI_SCREEN:-1600x900x24}"
COLIMA_SSH_CONFIG="${COLIMA_SSH_CONFIG:-${HOME}/.colima/ssh_config}"
SSH_CONTROL_SOCKET="${TMPDIR:-/tmp}/physical-ai-gazebo-vnc-ssh.sock"

usage() {
  printf '%s\n' \
    "Usage: $0 {start|open|status|stop}" \
    "" \
    "  start   Start the container GUI stack, SSH tunnel, and Screen Sharing" \
    "  open    Open the already-running GUI in macOS Screen Sharing" \
    "  status  Show the container GUI and tunnel status" \
    "  stop    Stop only the GUI stack and tunnel (Gazebo server stays running)"
}

require_host_tools() {
  local command_name

  for command_name in docker ssh open; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
      printf 'Required host command is missing: %s\n' "${command_name}" >&2
      exit 1
    fi
  done

  if [[ ! -f "${COLIMA_SSH_CONFIG}" ]]; then
    printf 'Colima SSH config was not found: %s\n' "${COLIMA_SSH_CONFIG}" >&2
    exit 1
  fi

  if ! docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    printf 'ROS 2 container was not found: %s\n' "${CONTAINER_NAME}" >&2
    exit 1
  fi

  if [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}")" != "true" ]]; then
    printf 'Starting container: %s\n' "${CONTAINER_NAME}"
    docker start "${CONTAINER_NAME}" >/dev/null
  fi
}

validate_settings() {
  if [[ ! "${CONTAINER_NAME}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    printf 'Invalid container name: %s\n' "${CONTAINER_NAME}" >&2
    exit 1
  fi

  if [[ ! "${VNC_PORT}" =~ ^[0-9]+$ ]] || ((VNC_PORT < 1024 || VNC_PORT > 65535)); then
    printf 'Invalid VNC port: %s\n' "${VNC_PORT}" >&2
    exit 1
  fi

  if [[ ! "${VNC_PASSWORD}" =~ ^[A-Za-z0-9._-]{1,8}$ ]]; then
    printf 'VNC password must contain 1-8 letters, numbers, dots, underscores, or hyphens.\n' >&2
    exit 1
  fi

  if [[ ! "${DISPLAY_NUMBER}" =~ ^[0-9]+$ ]]; then
    printf 'Invalid X display number: %s\n' "${DISPLAY_NUMBER}" >&2
    exit 1
  fi

  if [[ ! "${SCREEN_GEOMETRY}" =~ ^[0-9]+x[0-9]+x(16|24|32)$ ]]; then
    printf 'Invalid screen geometry: %s\n' "${SCREEN_GEOMETRY}" >&2
    exit 1
  fi
}

container_ip() {
  docker inspect -f '{{range .NetworkSettings.Networks}}{{println .IPAddress}}{{end}}' \
    "${CONTAINER_NAME}" | awk 'NF {print; exit}'
}

start_container_gui() {
  docker exec -i \
    -e GAZEBO_GUI_DISPLAY_NUMBER="${DISPLAY_NUMBER}" \
    -e GAZEBO_GUI_SCREEN="${SCREEN_GEOMETRY}" \
    -e GAZEBO_GUI_VNC_PORT="${VNC_PORT}" \
    -e GAZEBO_GUI_VNC_PASSWORD="${VNC_PASSWORD}" \
    "${CONTAINER_NAME}" bash -s <<'CONTAINER_SCRIPT'
set -euo pipefail

runtime_dir=/tmp/gazebo-vnc
display=":${GAZEBO_GUI_DISPLAY_NUMBER}"
password_file="${runtime_dir}/vnc.passwd"

if ! command -v Xvfb >/dev/null 2>&1 \
  || ! command -v x11vnc >/dev/null 2>&1 \
  || ! command -v fluxbox >/dev/null 2>&1 \
  || ! command -v glxinfo >/dev/null 2>&1 \
  || ! command -v xdpyinfo >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y --no-install-recommends \
    dbus-x11 fluxbox mesa-utils x11-utils x11vnc xvfb
fi

install -d -m 700 "${runtime_dir}" "${runtime_dir}/runtime"

find_pid() {
  pgrep -o -f "$1" 2>/dev/null || true
}

xvfb_pid="$(find_pid "^Xvfb ${display}( |$)")"
if [[ -z "${xvfb_pid}" ]]; then
  nohup Xvfb "${display}" \
    -screen 0 "${GAZEBO_GUI_SCREEN}" \
    +extension GLX +render -noreset \
    >"${runtime_dir}/xvfb.log" 2>&1 &
  xvfb_pid=$!
fi
printf '%s\n' "${xvfb_pid}" >"${runtime_dir}/xvfb.pid"

for _ in $(seq 1 30); do
  if DISPLAY="${display}" xdpyinfo >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

if ! DISPLAY="${display}" xdpyinfo >/dev/null 2>&1; then
  printf 'Xvfb did not become ready. See %s/xvfb.log\n' "${runtime_dir}" >&2
  exit 1
fi

if ! DISPLAY="${display}" glxinfo -B 2>/dev/null | grep -q 'OpenGL version string'; then
  printf 'The virtual display does not provide a usable OpenGL context.\n' >&2
  exit 1
fi

fluxbox_pid="$(pgrep -o -x fluxbox 2>/dev/null || true)"
if [[ -z "${fluxbox_pid}" ]]; then
  nohup env DISPLAY="${display}" fluxbox \
    >"${runtime_dir}/fluxbox.log" 2>&1 &
  fluxbox_pid=$!
fi
printf '%s\n' "${fluxbox_pid}" >"${runtime_dir}/fluxbox.pid"

vnc_pid="$(find_pid "^x11vnc -display ${display}( |$)")"
if [[ -z "${vnc_pid}" ]]; then
  x11vnc -storepasswd "${GAZEBO_GUI_VNC_PASSWORD}" "${password_file}" \
    >/dev/null
  chmod 600 "${password_file}"
  nohup x11vnc \
    -display "${display}" \
    -forever -shared -rfbauth "${password_file}" \
    -rfbport "${GAZEBO_GUI_VNC_PORT}" \
    -listen 0.0.0.0 \
    >"${runtime_dir}/x11vnc.log" 2>&1 &
  vnc_pid=$!
fi
printf '%s\n' "${vnc_pid}" >"${runtime_dir}/x11vnc.pid"

gazebo_gui_pid="$(find_pid '^gz sim -g( |$)')"
if [[ -z "${gazebo_gui_pid}" ]]; then
  nohup bash -lc "
    source /opt/ros/jazzy/setup.bash
    export DISPLAY='${display}'
    export XDG_RUNTIME_DIR='${runtime_dir}/runtime'
    export QT_X11_NO_MITSHM=1
    export LIBGL_ALWAYS_SOFTWARE=1
    exec gz sim -g -v 3 --force-version 8
  " >"${runtime_dir}/gazebo-gui.log" 2>&1 &
  gazebo_gui_pid=$!
fi
printf '%s\n' "${gazebo_gui_pid}" >"${runtime_dir}/gazebo-gui.pid"

printf 'Container GUI ready: DISPLAY=%s, VNC=%s\n' \
  "${display}" "${GAZEBO_GUI_VNC_PORT}"
CONTAINER_SCRIPT
}

start_tunnel() {
  local target_ip
  target_ip="$(container_ip)"

  if [[ -z "${target_ip}" ]]; then
    printf 'Could not determine the container IP.\n' >&2
    exit 1
  fi

  if [[ -S "${SSH_CONTROL_SOCKET}" ]] \
    && ssh -F "${COLIMA_SSH_CONFIG}" \
      -S "${SSH_CONTROL_SOCKET}" -O check colima >/dev/null 2>&1; then
    return
  fi

  if [[ -e "${SSH_CONTROL_SOCKET}" ]]; then
    unlink "${SSH_CONTROL_SOCKET}"
  fi

  ssh -F "${COLIMA_SSH_CONFIG}" \
    -o ControlMaster=yes \
    -o ControlPath="${SSH_CONTROL_SOCKET}" \
    -o ControlPersist=yes \
    -o ExitOnForwardFailure=yes \
    -fN -L "127.0.0.1:${VNC_PORT}:${target_ip}:${VNC_PORT}" \
    colima
}

open_gui() {
  open "vnc://127.0.0.1:${VNC_PORT}"
}

show_status() {
  local target_ip
  target_ip="$(container_ip)"

  printf 'Container: %s (%s)\n' "${CONTAINER_NAME}" "${target_ip:-no IP}"
  docker exec "${CONTAINER_NAME}" bash -lc '
    printf "%-12s %s\n" "COMPONENT" "PROCESS"
    printf "%-12s %s\n" "Xvfb" "$(pgrep -a -f "^Xvfb :[0-9]+( |$)" || echo stopped)"
    printf "%-12s %s\n" "Fluxbox" "$(pgrep -a -x fluxbox || echo stopped)"
    printf "%-12s %s\n" "VNC" "$(pgrep -a -x x11vnc || echo stopped)"
    printf "%-12s %s\n" "Gazebo GUI" "$(pgrep -a -f "^gz sim -g( |$)" || echo stopped)"
    printf "%-12s %s\n" "Gazebo srv" "$(pgrep -a -f "^gz sim .* -s( |$)" || echo stopped)"
  '

  if [[ -S "${SSH_CONTROL_SOCKET}" ]] \
    && ssh -F "${COLIMA_SSH_CONFIG}" \
      -S "${SSH_CONTROL_SOCKET}" -O check colima >/dev/null 2>&1; then
    printf 'SSH tunnel: running on vnc://127.0.0.1:%s\n' "${VNC_PORT}"
  else
    printf 'SSH tunnel: stopped\n'
  fi
}

stop_container_gui() {
  docker exec -i "${CONTAINER_NAME}" bash -s <<'CONTAINER_SCRIPT'
set -euo pipefail

runtime_dir=/tmp/gazebo-vnc

stop_from_pid_file() {
  local name="$1"
  local pid_file="${runtime_dir}/$2.pid"
  local pid

  if [[ ! -r "${pid_file}" ]]; then
    return
  fi

  pid="$(tr -cd '0-9' <"${pid_file}")"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    kill -TERM "${pid}"
    printf 'Stopped %s (PID %s)\n' "${name}" "${pid}"
  fi
}

stop_from_pid_file 'Gazebo GUI' gazebo-gui
stop_from_pid_file 'VNC server' x11vnc
stop_from_pid_file 'Fluxbox' fluxbox
stop_from_pid_file 'Xvfb' xvfb
CONTAINER_SCRIPT
}

stop_tunnel() {
  if [[ -S "${SSH_CONTROL_SOCKET}" ]]; then
    ssh -F "${COLIMA_SSH_CONFIG}" \
      -S "${SSH_CONTROL_SOCKET}" -O exit colima >/dev/null 2>&1 || true
  fi
}

main() {
  local action="${1:-}"

  validate_settings

  case "${action}" in
    start)
      require_host_tools
      start_container_gui
      start_tunnel
      open_gui
      printf 'VNC password: %s (not the macOS account password)\n' "${VNC_PASSWORD}"
      show_status
      ;;
    open)
      require_host_tools
      start_tunnel
      open_gui
      printf 'VNC password: %s (not the macOS account password)\n' "${VNC_PASSWORD}"
      ;;
    status)
      require_host_tools
      show_status
      ;;
    stop)
      require_host_tools
      stop_tunnel
      stop_container_gui
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
