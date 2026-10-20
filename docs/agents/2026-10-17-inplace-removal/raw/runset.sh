#!/bin/bash
# Runs the removal-relevant suites from root $1 with the native memory source set; writes $2.
cd "$1"
export PYTHONPATH=$1:/home/outsider/.cache/lifeos-release-0.7.3-20261016/archive-integration-wgrx453d/package/hermes
export LIFEOS_MEMORY_SOURCE=/tmp/inplace-removal/lifeos-src/install
PY=/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python
out="$2"; : > "$out"
for n in test_memory_return.py test_memory_transition.py test_memory_transition_probe.py test_memory_removal_workflow.py test_profile_services.py test_removal_bootstrap.py test_removal_configuration.py test_removal_consumers.py test_removal_coordinator.py test_removal_data_barrier.py test_removal_execution_source.py test_removal_generation.py test_removal_inventory.py test_removal_ownership.py test_removal_preparation.py test_removal_publication.py test_removal_recovery.py test_removal_runtime.py test_removal_services.py test_removal_state.py test_inplace_removal.py test_inplace_preparation.py test_inplace_services.py test_host_record.py test_host_compatibility.py test_dependency_plan.py test_consumer_scan.py test_memory_workflow.py test_memory_export.py; do
  [ -f tests/$n ] || continue
  r=$(timeout 1200 $PY -B -m unittest discover -s tests -p "$n" 2>&1 | tail -3 | tr '\n' ' ')
  echo "$n :: $r" >> "$out"
done
touch "$out.done"
