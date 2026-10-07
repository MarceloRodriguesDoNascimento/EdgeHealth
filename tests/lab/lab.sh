#!/usr/bin/env bash
# EdgeHealth network lab: simulated devices in network namespaces inside WSL2.
# Run as root inside WSL:  wsl -d Ubuntu-24.04 -u root -- bash tests/lab/lab.sh <command>
# Normally called by edgelab.py (Windows); see tests/lab/README.md.
#
# Everything lives inside the WSL VM: no Windows firewall, route or adapter is touched.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE=/var/lib/edgehealth-lab
VENV=$STATE/venv
LOG=$STATE/coletor.log
PIDFILE=$STATE/coletor.pid

# name|ip/prefix|bridge  (ip is the device; the bridge holds .1 of the subnet)
DEVICES=(
  "firewall|10.77.0.2/24|br-lab"
  "servidor|10.77.0.3/24|br-lab"
  "nas|10.77.0.4/24|br-lab"
  "impressora|10.77.0.5/24|br-lab"
  "desktop|10.77.0.6/24|br-lab"
  "sensor|10.77.0.7/24|br-lab"
  "switch2|10.77.2.2/24|br-andar2"
  "ap|10.77.2.3/24|br-andar2"
  "camera|10.77.2.4/24|br-andar2"
  "voip|10.77.2.5/24|br-andar2"
)
declare -A BRIDGE_IP=([br-lab]=10.77.0.1/24 [br-andar2]=10.77.2.1/24)

die() { echo "ERRO: $*" >&2; exit 1; }
field() { local IFS='|'; read -r -a f <<<"$1"; echo "${f[$2]}"; }
find_device() {
  local d
  for d in "${DEVICES[@]}"; do [[ "$(field "$d" 0)" == "$1" ]] && { echo "$d"; return; }; done
  die "dispositivo desconhecido: $1 (use: $(names))"
}
names() { local d out=(); for d in "${DEVICES[@]}"; do out+=("$(field "$d" 0)"); done; echo "${out[*]}"; }
ns() { echo "eh-$1"; }
veth() { echo "vh-$1"; }   # host side, attached to the bridge (max 15 chars)

up() {
  modprobe sch_netem
  local br d name ip bridge
  for br in "${!BRIDGE_IP[@]}"; do
    ip link show "$br" >/dev/null 2>&1 || ip link add "$br" type bridge
    ip addr replace "${BRIDGE_IP[$br]}" dev "$br"
    ip link set "$br" up
  done
  for d in "${DEVICES[@]}"; do
    name=$(field "$d" 0); ip=$(field "$d" 1); bridge=$(field "$d" 2)
    if ! ip netns list | grep -qw "$(ns "$name")"; then
      ip netns add "$(ns "$name")"
      ip link add "$(veth "$name")" type veth peer name eth0 netns "$(ns "$name")"
      ip -n "$(ns "$name")" addr add "$ip" dev eth0
      ip -n "$(ns "$name")" link set lo up
      ip -n "$(ns "$name")" link set eth0 up
      ip -n "$(ns "$name")" route add default via "${BRIDGE_IP[$bridge]%/*}"
      ip link set "$(veth "$name")" master "$bridge"
      ip link set "$(veth "$name")" up
    fi
  done
  status
}

down() {
  coletor_parar || true
  local d name br
  for d in "${DEVICES[@]}"; do
    name=$(field "$d" 0)
    ip netns del "$(ns "$name")" 2>/dev/null || true
    ip link del "$(veth "$name")" 2>/dev/null || true
  done
  for br in "${!BRIDGE_IP[@]}"; do ip link del "$br" 2>/dev/null || true; done
  echo "Lab removido."
}

status() {
  local d name ip bridge state qd fw
  printf '%-11s %-13s %-10s %-6s %-26s %s\n' DISPOSITIVO IP SWITCH PING NETEM BLOQUEIO
  for d in "${DEVICES[@]}"; do
    name=$(field "$d" 0); ip=$(field "$d" 1); bridge=$(field "$d" 2)
    if ! ip netns list | grep -qw "$(ns "$name")"; then
      printf '%-11s %-13s %-10s %s\n' "$name" "${ip%/*}" "$bridge" "(lab não está de pé)"; continue
    fi
    if ping -c1 -W1 -q "${ip%/*}" >/dev/null 2>&1; then state=ok; else state=FALHA; fi
    qd=$(tc qdisc show dev "$(veth "$name")" | sed -n 's/.*netem.* limit [0-9]* //p' | sed 's/ seed [0-9]*//' || true)
    fw=$(ip netns exec "$(ns "$name")" iptables -S INPUT | grep -q DROP && echo ICMP-DROP || true)
    printf '%-11s %-13s %-10s %-6s %-26s %s\n' "$name" "${ip%/*}" "$bridge" "$state" "${qd:--}" "${fw:--}"
  done
  for br in "${!BRIDGE_IP[@]}"; do
    ip link show "$br" 2>/dev/null | grep -q 'state DOWN' && echo "$br: DESLIGADO" || true
  done
  [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null && echo "Coletor: rodando (pid $(cat $PIDFILE))" || echo "Coletor: parado"
}

# --- Fault injection ----------------------------------------------------------------
offline() { local n; n=$(field "$(find_device "$1")" 0); ip netns exec "$(ns "$n")" iptables -C INPUT -p icmp -j DROP 2>/dev/null || ip netns exec "$(ns "$n")" iptables -A INPUT -p icmp -j DROP; echo "$n: ICMP bloqueado (sem resposta)"; }
netem() {  # netem <name> <delay_ms> <loss_pct>
  local n; n=$(field "$(find_device "$1")" 0)
  tc qdisc replace dev "$(veth "$n")" root netem delay "${2}ms" loss "${3}%"
  echo "$n: atraso ${2} ms, perda ${3}%"
}
restaurar() {
  local targets=("$@") n
  [[ ${1:-} == todos ]] && read -r -a targets <<<"$(names)"
  for n in "${targets[@]}"; do
    n=$(field "$(find_device "$n")" 0)
    tc qdisc del dev "$(veth "$n")" root 2>/dev/null || true
    ip netns exec "$(ns "$n")" iptables -F INPUT
  done
  [[ ${1:-} == todos ]] && ip link set br-andar2 up
  echo "Restaurado: ${targets[*]}"
}
switch_andar2() { ip link set br-andar2 "$1"; echo "Switch andar 2 (br-andar2): $1"; }

# --- Collector ------------------------------------------------------------------------
coletor() {  # foreground: the caller's wsl.exe process keeps the WSL VM alive
  local api=${1:?api-url} token=${2:?token-file}
  mkdir -p "$STATE"
  if [[ ! -x $VENV/bin/python ]]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -r "$LAB_DIR/../../collector/requirements.txt"
  fi
  [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null && die "coletor já está rodando (pid $(cat $PIDFILE))"
  # The collector pings with unprivileged ICMP sockets (icmplib privileged=False).
  sysctl -qw net.ipv4.ping_group_range="0 2147483647"
  # A freshly started VM inherits the Windows clock and corrects it a few seconds later.
  sleep 5; hora "$api" >>"$LOG" 2>&1 || true
  echo $$ >"$PIDFILE"
  cd "$STATE"
  # exec keeps the same pid, so coletor-parar stops exactly this process.
  exec "$VENV/bin/python" -u "$LAB_DIR/../../collector/edgehealth_collector.py" \
       --api-url "$api" --token-file "$token" --queue-file "$STATE/fila.jsonl" >>"$LOG" 2>&1
}
coletor_parar() {
  [[ -f $PIDFILE ]] || { echo "Coletor já estava parado."; return 0; }
  kill "$(cat $PIDFILE)" 2>/dev/null && echo "Coletor parado." || echo "Coletor já estava parado."
  rm -f "$PIDFILE"
}
manter() { exec sleep infinity; }   # keeps the VM (and the lab) alive while the collector is stopped
liberar() { pkill -f '^sleep infinity$' || true; echo "Mantenedor encerrado."; }

hora() {
  # The API rejects samples with skewed clocks (COLLECTOR_MAX_CLOCK_SKEW_SECONDS).
  local url=${1:-https://marcelodomingos.pythonanywhere.com} remote local diff
  remote=$(date -u -d "$(curl -sI "$url/api/health" | tr -d '\r' | sed -n 's/^[Dd]ate: //p')" +%s)
  local=$(date -u +%s); diff=$((local-remote))
  echo "Diferença WSL - servidor: ${diff} s"
  if (( diff > 2 || diff < -2 )); then date -u -s "@$remote" >/dev/null; echo "Relógio do WSL ajustado."; fi
}

log() { tail -n "${1:-30}" "$LOG"; }

cmd=${1:-}; shift || true
case "$cmd" in
  up) up ;;
  down) down ;;
  status) status ;;
  offline) offline "${1:?dispositivo}" ;;
  latencia) netem "${1:?dispositivo}" "${2:?ms}" 0 ;;
  perda) netem "${1:?dispositivo}" 0 "${2:?pct}" ;;
  degradar) netem "${1:?dispositivo}" "${2:?ms}" "${3:?pct}" ;;
  restaurar) restaurar "${@:-todos}" ;;
  switch-andar2) switch_andar2 "${1:?up|down}" ;;
  coletor) coletor "$@" ;;
  coletor-parar) coletor_parar ;;
  manter) manter ;;
  liberar) liberar ;;
  hora) hora "$@" ;;
  log) log "$@" ;;
  *) echo "uso: lab.sh up|down|status|offline D|latencia D MS|perda D PCT|degradar D MS PCT|restaurar [D...|todos]|switch-andar2 up|down|coletor API TOKEN|coletor-parar|manter|liberar|hora|log [N]"
     echo "dispositivos: $(names)"; exit 2 ;;
esac
