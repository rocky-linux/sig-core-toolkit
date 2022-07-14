#!/bin/bash
set -ex

{% if extra_iso_mode == "podman" %}
{{ lorax_pkg_cmd }}
mkdir -p {{ compose_work_iso_dir }}/{{ arch }}
cd  {{ compose_work_iso_dir }}/{{ arch }}
test -f {{ isoname }} && { echo "ERROR: ISO ALREDY EXISTS!"; exit 1; }
{% else %}
cd /builddir

if ! TEMPLATE="$($(head -n1 $(which lorax) | cut -c3-) -c 'import pylorax; print(pylorax.find_templates())')"; then
  TEMPLATE="/usr/share/lorax"
fi
{% endif %}


{{ make_image }}

{{ isohybrid }}

{{ implantmd5 }}

{{ make_manifest }}

