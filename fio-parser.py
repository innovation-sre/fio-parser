#!/usr/bin/env python2.7

# (C)2014 Red Hat, Inc., Jan Tulak <jtulak@redhat.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# fio-parser
#
# run fio with --minimal 
from __future__ import print_function
import sys
import getopt
import fileinput
import re
from libfioparser.TestSuite import TestSuite
import requests
import os
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

"""
This function prints results.
Change it for whatever you want to see.
"""


def parse(jobs):
    # print the layout
    print("iodepth\t%s\t%s\t%s\t%s\t%s\t%s" % (
        "read", "write", "cpu_user", "iops", "total io", "runtime"
    ))
    build_no = int(os.environ.get('BUILD_NUMBER', 0))
    block_size = os.environ.get('FIOTEST_BS', '4k')
    job_id = os.environ.get('FIOTEST_JOB_ID', 'default-job')
    node = os.environ.get('FIOTEST_NODE', 'default-node')
    io_depth = os.environ.get('FIOTEST_IO_DEPTH', 128)
    push_gw_namespace = os.environ.get('PUSH_GW_NAMESPACE', 'scale-ci-tooling')
    push_gw_endpoint = f'galeo-prometheus-pushgateway.{push_gw_namespace}.svc.cluster.local:9091'
    # with open('/metrics', 'w') as f:
    print('Jobs Count: ', len(jobs))
    for job_name in jobs:
        job = jobs[job_name]
        # parse the name of the job
        name_split = re.split("-", job.name)
        # and print just jobs that starts with "multi-" prefix
        # Write Prometheus Metrics
        metrics = []
        registry = CollectorRegistry()
        posting_error = False
        posting_error_str = ""
        if name_split[1] == "multi":
            block_size = name_split[4]
            print("IO Depth (%s): %s" % (name_split,job.io_depths))
            print("Blocksize:", block_size)
            read_bandwidth = int(job.read_status.bandwidth.avg())
            read_bandwidth_min = int(job.read_status.bandwidth.min())
            read_bandwidth_max = int(job.read_status.bandwidth.max())
            write_bandwidth = int(job.write_status.bandwidth.avg())
            write_bandwidth_min = int(job.write_status.bandwidth.min())
            write_bandwidth_max = int(job.write_status.bandwidth.max())
            user_cpu = job.cpu_usage.user[0]
            iops = int(job.write_status.iops.avg())
            iops_min = int(job.write_status.iops.min())
            iops_max = int(job.write_status.iops.max())
            total_io = int(job.write_status.total_io.avg())
            total_io_min = int(job.write_status.total_io.min())
            total_io_max = int(job.write_status.total_io.max())
            total_runtime = int(job.write_status.runtime.avg())
            total_runtime_min = int(job.write_status.runtime.min())
            total_runtime_max = int(job.write_status.runtime.max())
            print("%s\t%dB/s\t%dB/s\t%s\t%d\t%dKB\t%dms" % (
                io_depth,
                read_bandwidth,
                write_bandwidth,
                user_cpu,
                iops,
                total_io,
                total_runtime
            ))
            bw_gauge = Gauge('scaleci_fiotest_bandwidth', 'Bandwidth Result of an FIO Test',
                             ["build_no", "io_depth", "type", "agg"], registry=registry)
            bw_gauge.labels(build_no=build_no, io_depth=io_depth, type="read", agg="avg").set(
                read_bandwidth)

            bw_gauge.labels(build_no=build_no, io_depth=io_depth, type="read", agg="min").set(
                read_bandwidth_min)

            bw_gauge.labels(build_no=build_no, io_depth=io_depth, type="read", agg="max").set(
                read_bandwidth_max)

            bw_gauge.labels(build_no=build_no, io_depth=io_depth, type="write", agg="avg").set(
                write_bandwidth)

            bw_gauge.labels(build_no=build_no, io_depth=io_depth, type="write", agg="min").set(
                write_bandwidth_min)

            bw_gauge.labels(build_no=build_no, io_depth=io_depth, type="write", agg="max").set(
                write_bandwidth_max)

            cpu_gauge = Gauge('scaleci_fiotest_cpu', 'CPU Utilization for the FIO Test',
                              ["build_no", "io_depth"], registry=registry)
            cpu_gauge.labels(build_no=build_no, io_depth=io_depth).set(user_cpu)

            iops_gauge = Gauge('scaleci_fiotest_iops', 'IO Operations /sec for the FIO Test',
                               ["build_no", "io_depth", "agg"], registry=registry)
            iops_gauge.labels(build_no=build_no, io_depth=io_depth, agg="avg").set(iops)
            iops_gauge.labels(build_no=build_no, io_depth=io_depth, agg="min").set(iops_min)
            iops_gauge.labels(build_no=build_no, io_depth=io_depth, agg="max").set(iops_max)

            total_io_gauge = Gauge('scaleci_fiotest_total_io', 'Total IO count for the FIO Test',
                                   ["build_no", "io_depth", "agg"], registry=registry)
            total_io_gauge.labels(build_no=build_no, io_depth=io_depth, agg="avg").set(total_io)
            total_io_gauge.labels(build_no=build_no, io_depth=io_depth, agg="min").set(total_io_min)
            total_io_gauge.labels(build_no=build_no, io_depth=io_depth, agg="max").set(total_io_max)

            total_runtime_gauge = Gauge('scaleci_fiotest_runtime', 'Total runtime for the FIO Test',
                                        ["build_no", "io_depth", "agg"], registry=registry)
            total_runtime_gauge.labels(build_no=build_no, io_depth=io_depth, agg="avg").set(total_runtime)
            total_runtime_gauge.labels(build_no=build_no, io_depth=io_depth, agg="min").set(total_runtime_min)
            total_runtime_gauge.labels(build_no=build_no, io_depth=io_depth, agg="max").set(total_runtime_max)

            try:
                gid = {}
                gid['instance'] = node
                gid['block_size'] = "%sk" % block_size
                print('Posting the data to pushgateway (%s) - Node: %s | Job Name: %s | Group Key: %s' % (
                                                    push_gw_endpoint, node, job_name, gid))
                push_to_gateway(push_gw_endpoint, job=job_id,
                                grouping_key=gid,
                                registry=registry)
                print('Posted successfully to pushgateway - ', push_gw_endpoint)
            except Exception as e:
                posting_error_str = e
                posting_error = True

        if posting_error:
            print('Exception was raised. Error: %s' % posting_error_str)


def print_help():
    print("%s [-h] [-i|--input FILENAME]" % (sys.argv[0]))


def main(argv):
    instream = None

    try:
        opts, args = getopt.getopt(argv, "hi:", ["input="])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)

    for opt, arg in opts:
        if (opt == '-h'):
            print_help()
            sys.exit()
        elif (opt in ("-i", "--input")):
            instream = open(arg)

    if (instream is None):
        instream = fileinput.input()

    # parse the data
    ts = TestSuite(instream)
    parse(ts.get_all())


if __name__ == "__main__":
    main(sys.argv[1:])
