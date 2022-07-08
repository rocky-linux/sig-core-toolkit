#!/bin/bash
set -ex

{% if live_iso_mode == "podman" %}
{{ live_pkg_cmd }}
mkdir -p {{ compose_live_work_dir }}/{{ arch }}
cd  {{ compose_live_work_dir }}/{{ arch }}
test -f {{ isoname }} && { echo "ERROR: ISO ALREDY EXISTS!"; exit 1; }
{% else %}
cd /builddir

{% endif %}

{{ make_image }}

