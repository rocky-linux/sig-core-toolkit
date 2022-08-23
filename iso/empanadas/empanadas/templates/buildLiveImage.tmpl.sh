#!/bin/bash
set -ex

{% if live_iso_mode == "podman" %}
{{ live_pkg_cmd }}
mkdir -p {{ compose_live_work_dir }}/{{ arch }}
cd  {{ compose_live_work_dir }}/{{ arch }}
test -f {{ isoname }} && { echo "ERROR: ISO ALREDY EXISTS!"; exit 1; }

major=$(grep loop /proc/devices | cut -c3)
for index in 0 1 2 3 4 5; do
  mknod /dev/loop$index $major $index
done
{% else %}
cd /builddir

{% endif %}

{{ git_clone }}
if [ -d "/builddir/ks/live/{{ major }}/peridot" ]; then
  pushd /builddir/ks/live/{{ major }}/{{ arch }}/peridot || { echo "Could not change directory"; exit 1; }
else
  pushd /builddir/ks/live/{{ major }}/{{ arch }}/staging || { echo "Could not change directory"; exit 1; }
fi
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
