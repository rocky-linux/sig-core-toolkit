#!/bin/bash
set -ex

{% if live_iso_mode == "podman" %}
{{ live_pkg_cmd }}
mkdir -p {{ compose_live_work_dir }}/{{ arch }}
cd  {{ compose_live_work_dir }}/{{ arch }}
test -f {{ isoname }} && { echo "ERROR: ISO ALREDY EXISTS!"; exit 1; }

major=$(grep loop /proc/devices | cut -c3)
for index in 0 1 2 3 4 5; do
  mknod /dev/loop$index b $major $index
done
{% else %}
# This section is typically for mock. It is possible to run mock within a
# container, but we generally don't like this. Even though we can do this,
# it does not mean that livemedia-creator is going to work. There are ways
# around this, such as making sure the container is privileged to have loop
# devices, and the loop devices should exist on the host. After, the loop
# devices have to be cleaned up.
#
# The lorax devs have a way of doing this, but it requires privleges and
# the containers cannot be root, as far as I understand it. Having root
# containers is bad practice IMO.
# 
# Even so, we don't support it. These checks are to prevent (you) from
# getting needless headaches.
[[ -f /run/.containerenv ]]; container_ec=$?
grep -q "0::/$" /proc/1/cgroup; pid_ec=$?
grep -q "0::/$" /proc/self/cgroup; self_ec=$?

if [[ "$pid_ec" == "0" ]] || [[ "$container_ec" == 0 ]] || [[ "$self_ec" == 0 ]]; then
  exit 23
fi

cd /builddir

{% endif %}

{{ git_clone }}
pushd /builddir/ks/live/{{ major }}/{{ arch }}/{{ kloc }} || { echo "Could not change directory"; exit 1; }
ksflatten -c {{ ks_file }} -o /builddir/ks.cfg
if [ $? -ne 0 ]; then
  echo "Error flattening kickstart"
  exit 1
fi
popd || { echo "Could not leave directory"; exit 1; }

{{ make_image }}

{% if live_iso_mode == "podman" %}
cp /builddir/lmc/{{ isoname }} {{ compose_live_work_dir }}/{{ arch }}/{{ isoname }}
{% endif %}
