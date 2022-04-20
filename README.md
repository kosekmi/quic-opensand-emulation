# Opensand Measurement Testbed

These scripts can be used to automate measurements of different protocols on the
[OpenSAND](https://opensand.org/content/home.php) satellite emulation platform.
Each emulation (one execution of the `opensand.sh` script) consist of multiple
scenarios that are tested, each of which has a different configuration (such as
the orbit of the emulated satellite). Within a single scenario multiple measurements
are executed to measure the performance of different protocols. Each measurement is
executed multiple times with each execution being called a run. This will generate
more statistically stable results.

[![Namespace Overview](res/network-namespace-opensand.png)](res/network-namespace-opensand.pdf)

This is an overview of the environment that is created by the scripts using network namespaces.

### Measured performance values

While the complete output of each component taking part in a measurement is captured,
the runs aim to measure the following set of performance values:

* Goodput Evolution
* Congestion Window Evolution
* Connection Establishment Time
* Time to First Byte
* Web Performance Metrics (e.g., Response Start, First Contentful Paint, Page Load Time) for HTTP/1.1 and HTTP/3

For evaluation of the results you can use these scripts: [quic-opensand-evaluation](https://github.com/kosekmi/quic-opensand-evaluation)

### Script structure

The main executable script is `opensand.sh` which will source all other scripts before
starting the measurements. Some scripts (such as `setup.sh` and `teardown.sh`) can
also be executed individually for, e.g., manual measurements.

* `opensand.sh` - Main executable
* `env.sh` - Environment configuration
* `setup*.sh` - Environment creation and setup
* `teardown*.sh` - Environment disassembly
* `run*.sh` - Execution of the individual measurement runs
* `stats.sh` - System statistics collection during the emulation

# Installation

1. Ensure the requirements below are met
2. Copy all files (including subdirectories) to the machine that will run the emulation
3. Update configuration in `env.sh`, especially the file and directory paths

### Requirements

These programs need to be cloned and built

* [qperf](https://github.com/kosekmi/qperf)
* [pepsal](https://github.com/danielinux/pepsal)

The following utilities need to be installed on the system:

* [opensand](https://opensand.org/content/get.php) (which installs `opensand-core`, `opensand-network` and `opensand-daemon`)  
  Not required are `opensand-collector` and `opensand-manager`. We advise to use `OpenSAND Version 5.2.0`, which has been verified for the Opensand Measurement Testbed
* iperf3
* tmux
* curl
* nginx (deamon can be disabled, it is used standalone)
* iproute2
* xmlstarlet

In addition, the following utilities are required for the Web Performance Measurements: 
* chromium
* selenium
* h2o Web Server

# Usage

Executing the main script `opensand.sh` will start the automated emulation. As this
will take some time, it is recommended to start the script in a tmux session.
```bash
tmux new-session
./opensand.sh
```
This allows to detach from the process and re-attach at any later time. For a rough estimation of emulation execution time, the following values can be considered for a typical GEO orbit with 250ms one-way delay:
* ~2 Minutes for 1 iteration of timing measurements for QUIC and TCP, both PEP and Non-PEP
* ~5 Minutes for 1 iteration of goodput measurements for QUIC and TCP, both PEP and Non-PEP
* ~4 Minutes for 1 iteration of http measurements for QUIC and TCP, both PEP and Non-PEP

The results of an emulation can be found in a subdirectory of the configured
`RESULTS_DIR` (set in `env.sh`), along with the emulation log file. To simplify
downloading the results, the symlink `latest` in `RESULTS_DIR` is updated to the
latest emulation output directory. When downloading the results, it is
recommended to use `rsync` over `scp` since the output consists of many small
files.

The script can be interrupted at any point, which will stop the current emulation
and cleanup the environment.

## Parameters

### General parameters 

| Name | Argument | Description |
| ---- | -------- | --- |
| `-f` | `<file>` | Read the scenario configuration from the file instead of using command line arguments |
| `-h` |          | Print a help message and exit |
| `-s` |          | Show the system statistics also in the log printed to stdout |
| `-t` | `<tag>`  | A tag to append to the output directory name, used for easier identification |
| `-v` |          | Print version and exit |

### Scenario configuration

These parameters configure the scenarios that are executed. All combinations of
all configured values are executed. Consider using the format described in
`Scenario file format` and `Example file` for a finer grained control over
the individual scenarios and example configurations.

| Name | Argument   | Description | Default | Type |
| ---- | ---------- | --- | --- | --- |
| `-A` | `<#,>`     | Comma separated list of attenuation values to measure | `0` | E |
| `-B` | `<GT,>*`   | `QUIC-specific:` Comma separated list of two qperf transfer buffer sizes for gateway and terminal. Repeat the parameter for multiple configurations | `1M,1M` | T |
| `-C` | `<SGTC,>`  | Comma separated list of four congestion control algorithms for server, gateway, terminal and client. (c = cubic, r = reno) | `rrrr` | T |
| `-D` | `#`        | dump the first # packets of a measurement | | M |
| `-E` | `<GT,>`    | csl of two delay values in ms, one value each per direction. Alternatively, a file can be stated which contains multiple second:delay pairs in the form of `second value`, i.e., `0 15` per line to emulate changing delays over time | `125` | M |
| `-F` | `<#,>*`    | `QUIC-specific:` csl of three values: max. ACK Delay, packet no. after which first ack frequency packet is sent, fraction of CWND to be used in ACK frequency frame | `25, 1000, 8` | T |
| `-I` | `<#,>*`    | csl of four initial window sizes for SGTC | `10` | T |
| `-l` | `<#,>`     | `QUIC-specific:` csl of two file paths for the qlog file output: client, server | `server.qlog und client.qlog in output directory` | T |
| `-L` | `<#,>`     | packet loss percentages | `0` | M |
| `-T` | `#`        | Number of runs per timing measurement in a scenario | `4` | M |
| `-N` | `#`        | Number of runs per goodput and HTTP measurement in a scenario | `1` | M |
| `-O` | `<#,>`     | Comma separated list of orbits to measure (GEO,MEO,LEO) | `GEO` | E |
| `-P` | `#`        | Number of seconds to prime a new environment with ICMP ping packets | `5` | M |
| `-Q` | `<SGTC,>*` | `QUIC-specific:` Comma separated list of four qperf quicly buffer sizes at server, gateway, terminal and client. Repeat parameter for multiple configurations | `1M,1M,1M,1M` | T |
| `-U` | `<SGTC,>*` | `QUIC-specific:` Comma separated list of four qperf UDP buffer sizes at server, gateway, terminal and client. Repeat parameter for multiple configurations | `1M,1M,1M,1M` | T |
| `-H` |            | Disable HTTP measurements | | M |
| `-V` |            | Disable plain (non PEP) measurements | | M |
| `-W` |            | Disable PEP measurements | | M |
| `-X` |            | Disable ICMP ping measurements | | M |
| `-Y` |            | Disable QUIC measurements | | M |
| `-Z` |            | Disable TCP measurements | | M |

The abbreviation `csl` stands for `comma-separated list`.
The command line arguments are used to generate a temporary scenario configuration
file in the emulations temporary directory (`/tmp/opensand.*/`).

## Scenario file format

The scenario file allows a much finer grained control over the individual
scenarios that are executed.

Each line in the file describes a single scenario. Blank lines and lines starting
with `#` are ignored. For each scenario the exact same arguments and syntax are
used as for the scenario configuration command line arguments with the exception
that only a single scenario must be described. Repeatable arguments must only be
given once. Arguments that define different configuration values via comma separated
lists must only have a single value.

### Example file

```
# Example scenario configuration

-N 100 -T 10 -P 5 -A 0 -B 4M,4M -Q 4M,4M,4M,4M -U 4M,4M,4M,4M -l client.qlog,server.qlog -O GEO -E 125,125 -W -C cccc -L 0 -I 10,10,10,10

-N 100 -T 10 -P 5 -A 0 -B 4M,4M -Q 4M,4M,4M,4M -U 4M,4M,4M,4M -l client.qlog,server.qlog -O LEO -E 8,8 -C -V crrc -L 0.1 -I 10,100,100,10
```

This file describes two different scenarios. Both scenarios perform 100 iterations of goodput and http measurements (```-N 100```), and 10 iterations of timing measurements (```-T 10```). The environments are primed for 5 seconds (```-P 5```), and the attenuation is configured with 0db (```-A 0```). All Buffers are identically sized in both scenarios with 4MB, and are also identical for the different buffer types (```-B 4M,4M -Q 4M,4M,4M,4M -U 4M,4M,4M,4M```). The client and server qlogs are output to the files client.qlog and server.qlog (```-l client.qlog,server.qlog```).

The first scenario uses a GEO satellite orbit (```-O GEO```) with a one-way delay of 250ms (```-E 125,125```), disables PEP measurements (```-W```), and uses cubic as congestion control on server, gateway, terminal, and client (```-C cccc```). Moreover, the loss is configured to 0% (```-L 0```), and the initial window set to 10 on server, gateway, terminal, and client (```-I 10,10,10,10```).

The second scenario uses a LEO satellite orbit (```-O LEO```) with a one-way delay of 16ms (```-E 8,8```), disables Non-PEP measurements (```-V```), and uses cubic as congestion control on server and client, as well as reno on gateway and terminal (```-C crrc```). Moreover, the loss is configured to 0.1% (```-L 0.1```), and the initial window set to 10 on server and client, as well as 100 on gateway and terminal (```-I 10,100,100,10```).
