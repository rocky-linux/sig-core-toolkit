#!/bin/bash
set -ex

{% if extra_iso_mode == "podman" %}
{{ lorax_pkg_cmd }} | tee -a {{ log_path }}
mkdir -p {{ compose_work_iso_dir }}/{{ arch }}
cd  {{ compose_work_iso_dir  }}/{{ arch }}
{% else %}
cd /builddir
{% endif %}


if ! TEMPLATE="$($(head -n1 $(which lorax) | cut -c3-) -c 'import pylorax; print(pylorax.find_templates())')"; then
  TEMPLATE="/usr/share/lorax"
fi

{{ make_image }} | tee -a {{ log_path }}

{{ isohybrid }} | tee -a {{ log_path }}

{{ implantmd5 }} | tee -a {{ log_path }}

{{ make_manifest }} | tee -a {{ log_path }}

