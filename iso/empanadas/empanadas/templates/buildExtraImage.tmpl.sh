#!/bin/bash
set -ex

{% if inside_podman %}
mkdir /builddor
{% endif %}

cd /builddir

if ! TEMPLATE="$($(head -n1 $(which lorax) | cut -c3-) -c 'import pylorax; print(pylorax.find_templates())')"; then
  TEMPLATE="/usr/share/lorax"
fi

{{ make_image }}

{{ isohybrid }}

{{ implantmd5 }}

{{ make_manifest }}

{% if inside_podman %}
mkdir -p {{ compose_work_iso_dir }}/{{ arch }}
cp /builddir/*.iso {{ compose_work_iso_dir }}/{{ arch }}
cp /builddir/*.iso.manifest {{ compose_work_iso_dir }}/{{ arch }}
{% endif %}
