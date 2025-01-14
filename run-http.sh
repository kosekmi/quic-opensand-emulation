#!/bin/bash

# osnd_start_http_server(output_dir)
# Start HTTP Server
function _osnd_http_server_start() {
	local output_dir=$1
	log I "Starting h2o server"

	sudo ip netns exec osnd-sv killall h2o -q
	tmux -L ${TMUX_SOCKET} new-session -s http-server -d "sudo ip netns exec osnd-sv bash"
	sleep $TMUX_INIT_WAIT
	tmux -L ${TMUX_SOCKET} send-keys -t http-server \
		"${H2O_BIN} -c ${H2O_CONFIG}" \
		Enter
}

function _osnd_http_server_stop() {
	log I "Stopping http server"

	tmux -L ${TMUX_SOCKET} send-keys -t http-server C-c
	sleep $CMD_SHUTDOWN_WAIT
	tmux -L ${TMUX_SOCKET} send-keys -t http-server C-d
	sleep $CMD_SHUTDOWN_WAIT
	sudo ip netns exec osnd-sv killall $(basename $H2O_BIN) -q
	tmux -L ${TMUX_SOCKET} kill-session -t http-server >/dev/null 2>&1
}

# osnd_start_http_server(output_dir, server_ip, timeout)
# Start HTTP Client (Chromium)
function osnd_http_client_start() {
	local output_dir=$1
	local server_ip=$2
	local timeout=$3
	local quic=$4
	local scenario_config_name=$5
	local pep=$6
	local run=$7

	local -n scenario_config_ref=$scenario_config_name

	local protocol="http"
	
	if [[ "$quic" == true ]]; then
		local protocol="quic"
	fi

	log I "Running chromium script"
	# sleep 1000
	sudo timeout --foreground $timeout ip netns exec osnd-cl ${PYTHON_BIN} ${PYTHON_HTTP_SCRIPT} ${protocol} ${server_ip} ${CHROME_DRIVER_BIN} ${output_dir} "${pep};${run}"

}

# osnd_http_client_stop()
# Stop HTTP Client (Chromium)
function osnd_http_client_stop() {
	log I "Stopping chromium script"

	sudo pkill -f chromedriver
	sudo pkill -f chromium-browser

	sleep $CMD_SHUTDOWN_WAIT
}

# osnd_measure_tcp_timing(scenario_config_name, output_dir, pep=false, run_cnt=12)
# Run HTTP timing measurements on the emulation environment
function osnd_measure_http() {
	local scenario_config_name=$1
	local output_dir=$2
	local pep=$3
	local run_cnt=$4
	local quic=${5:-false}

	local -n scenario_config_ref=$scenario_config_name
	local server_ip="${SV_LAN_SERVER_IP%%/*}:18080"
	local base_run_id="http"
	local name_ext=""
	local measure_secs=$MEASURE_TIME
	local timeout=$(echo "${MEASURE_TIME} * 1.1" | bc -l)

	if [[ "$pep" == true ]]; then
		base_run_id="${base_run_id}_pep"
		name_ext="${name_ext} (PEP)"
		if  [[ "$quic" == true ]]; then
			server_ip="${CL_LAN_ROUTER_IP%%/*}:18080"
		fi
	fi

	for i in $(seq $run_cnt); do
		log I "HTTP${name_ext} run $i/$run_cnt"
		local run_id="${base_run_id}_$i"

		# Environment
		osnd_setup $scenario_config_name "$output_dir" "$run_id" "$pep"
		sleep $MEASURE_WAIT

		_osnd_http_server_start output_dir
		sleep $MEASURE_WAIT
		
		if [[ "$pep" == true ]]; then
			if [[ "$quic" == false ]]; then
				_osnd_pepsal_proxies_start "$output_dir" "$run_id"
			else
				_osnd_quic_proxies_start "$output_dir" "$run_id" "${scenario_config_ref['cc_gw']:-reno}" "${scenario_config_ref['cc_st']:-reno}" "${scenario_config_ref['tbs_gw']:-1M}" "${scenario_config_ref['tbs_st']:-1M}" "${scenario_config_ref['qbs_gw']:-1M}" "${scenario_config_ref['qbs_st']:-1M}" "${scenario_config_ref['ubs_gw']:-1M}" "${scenario_config_ref['ubs_st']:-1M}" "${scenario_config_ref['iw_gw']:-10}" "${scenario_config_ref['iw_st']:-10}" "${scenario_config_ref['max_ack_delay']:-25}" "${scenario_config_ref['first_ack_freq_packet_number']:-1000}" "${scenario_config_ref['ack_freq_cwnd_fraction']:-8}" true true
			fi
			sleep $MEASURE_WAIT
		fi

		# Client
		osnd_http_client_start $output_dir $server_ip $timeout $quic $scenario_config_name $pep $run_id
		sleep $MEASURE_GRACE

		# Cleanup
		if [[ "$pep" == true ]]; then
			if [[ "$quic" == false ]]; then
				_osnd_pepsal_proxies_stop
			else 
				_osnd_quic_proxies_stop
			fi
		fi
		_osnd_http_server_stop
		osnd_http_client_stop
		osnd_teardown


		sleep $RUN_WAIT
	done
}

# If script is executed directly
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	declare -F log >/dev/null || function log() {
		local level="$1"
		local msg="$2"

		echo "[$level] $msg"
	}

	export SCRIPT_VERSION="manual"
	export SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
	set -a
	source "${SCRIPT_DIR}/env.sh"
	set +a
	source "${SCRIPT_DIR}/teardown-opensand.sh"
	source "${SCRIPT_DIR}/teardown-namespaces.sh"
	source "${SCRIPT_DIR}/run-quic.sh"

	if [[ "$@" ]]; then
		osnd_measure_http scenario_config "$@"
	fi
fi
