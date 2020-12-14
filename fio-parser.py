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
    push_gw_namespace = os.environ.get('PUSH_GW_NAMESPACE', 'scale-ci-tooling')
    # with open('/metrics', 'w') as f:
    for job_name in jobs:
        job = jobs[job_name]
        # parse the name of the job
        name_split = re.split("-", job.name)
        # and print just jobs that starts with "multi-" prefix
        # Write Prometheus Metrics
        metrics = []
        registry = CollectorRegistry()
        if name_split[1] == "multi":
            io_depth = name_split[4]
            read_bandwidth = int(job.read_status.bandwidth.med())
            write_bandwidth = int(job.write_status.bandwidth.med())
            user_cpu = job.cpu_usage.user[0]
            iops = int(job.write_status.iops.med())
            total_io = int(job.write_status.total_io.med())
            total_runtime = int(job.write_status.runtime.med())
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
                             ["build_no", "block_size", "type"], registry=registry)
            bw_gauge.labels(build_no=build_no, block_size=block_size, type="read").set(
                read_bandwidth)

            # write_bw_gauge = Gauge('scaleci_fiotest_bandwidth_write', 'Bandwidth Result of an FIO Test',
            #                        ["build_no", "block_size", "io_depth"], registry=registry)
            # write_bw_gauge.set_to_current_time()
            bw_gauge.labels(build_no=build_no, block_size=block_size, type="write").set(
                write_bandwidth)

            cpu_gauge = Gauge('scaleci_fiotest_cpu', 'CPU Utilization for the FIO Test',
                              ["build_no", "block_size"], registry=registry)
            cpu_gauge.labels(build_no=build_no, block_size=block_size).set(user_cpu)

            iops_gauge = Gauge('scaleci_fiotest_iops', 'IO Operations /sec for the FIO Test',
                               ["build_no", "block_size"], registry=registry)
            iops_gauge.labels(build_no=build_no, block_size=block_size).set(iops)

            total_io_gauge = Gauge('scaleci_fiotest_total_io', 'Total IO count for the FIO Test',
                                   ["build_no", "block_size"], registry=registry)
            total_io_gauge.labels(build_no=build_no, block_size=block_size).set(total_io)

            total_runtime_gauge = Gauge('scaleci_fiotest_runtime', 'Total runtime for the FIO Test',
                                        ["build_no", "block_size"], registry=registry)
            total_runtime_gauge.labels(build_no=build_no, block_size=block_size).set(total_runtime)

            #             metrics.append('scaleci_fiotest_bandwidth{build_no="%d",type="read",'
            #                     'block_size="%s",io_depth="%s"} %d' % (build_no, block_size, iodepth, read_bandwidth))
            #             metrics.append('scaleci_fiotest_bandwidth{build_no="%d",type="write",'
            #                     'block_size="%s",io_depth="%s"} %d' % (build_no, block_size, iodepth, write_bandwidth))
            # registry.register(cpu_gauge)
            # registry.register(read_bw_gauge)
            # registry.register(write_bw_gauge)

            #
            #             metrics.append('# HELP scaleci_fiotest_cpu CPU Utilization for the FIO Test')
            #             metrics.append('# TYPE scaleci_fiotest_cpu gauge')
            #             metrics.append('scaleci_fiotest_cpu{build_no="%d",block_size="%s",'
            #                     'io_depth="%s"} %d' % (build_no, block_size, iodepth, user_cpu))
            # registry.register(iops_gauge)

            #
            #             metrics.append('# HELP scaleci_fiotest_iops IO Operations /sec for the FIO Test')
            #             metrics.append('# TYPE scaleci_fiotest_iops gauge')
            #             metrics.append('scaleci_fiotest_iops{build_no="%d",block_size="%s",'
            #                     'io_depth="%s"} %d' % (build_no, block_size, iodepth, iops))
            # registry.register(total_io_gauge)

            #             metrics.append('# HELP scaleci_fiotest_total_io Total IO count for the FIO Test')
            #             metrics.append('# TYPE scaleci_fiotest_total_io gauge')
            #             metrics.append('scaleci_fiotest_total_io{build_no="%d",block_size="%s",'
            #                     'io_depth="%s"} %d' % (build_no, block_size, iodepth, total_io))
            # registry.register(total_io_gauge)

            #
            #             metrics.append('# HELP scaleci_fiotest_runtime Total runtime for the FIO Test')
            #             metrics.append('# TYPE scaleci_fiotest_runtime gauge')
            #             metrics.append('scaleci_fiotest_runtime{build_no="%d",block_size="%s",'
            #                     'io_depth="%s"} %d' % (build_no, block_size, iodepth, total_runtime))

            # f.writelines([s + '\n' for s in metrics])

            metrics_lines = '\n'.join(metrics)
            try:
                print('Posting the data to pushgateway - ', node, job_name)
                #                 res = requests.post(url=f'http://galeo-prometheus-pushgateway.{push_gw_namespace}.svc.cluster.local:9091'
                #                                         f'/metrics/job/fiotest/instance/{build_no}',
                #                                     data=metrics_lines.encode('utf8'))
                gid = {}
                gid['instance'] = node
                gid['io_depth'] = io_depth
                push_to_gateway(f'galeo-prometheus-pushgateway.{push_gw_namespace}.svc.cluster.local:9091', job=job_id,
                                grouping_key=gid,
                                registry=registry)
                print('Posted the data to pushgateway.')
            #                 if res.status_code == 200:
            #                     print('Successful')
            #                 print('Metrics Data Posted: ')
            #                 print(data)
            except Exception as e:
                print('Exception was raised. Error: %s' % e)


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
